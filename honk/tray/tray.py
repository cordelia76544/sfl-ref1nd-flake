#!/usr/bin/env python3
import argparse
import signal
import sys

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AyatanaAppIndicator3', '0.1')
from gi.repository import Gtk, Gio, GLib, AyatanaAppIndicator3 as Indicator
from state import presentation, validate_url

UNIT = 'honk-core.service'
SYSTEMCTL = '@systemctl@'
JOURNALCTL = '@journalctl@'
ICONS = '@icons@'


def run_async(argv, callback, timeout=15):
    """Never block GTK, including while Polkit waits for authentication."""
    try:
        process = Gio.Subprocess.new(argv, Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE)
    except GLib.Error as error:
        callback(1, '', str(error))
        return
    timed_out = False

    def expire():
        nonlocal timed_out
        timed_out = True
        process.force_exit()
        return GLib.SOURCE_REMOVE

    timer = GLib.timeout_add_seconds(timeout, expire)

    def finished(proc, result):
        if not timed_out:
            GLib.source_remove(timer)
        try:
            _, output, error = proc.communicate_utf8_finish(result)
            code = proc.get_exit_status() if proc.get_if_exited() else 1
            callback(code, output or '', '操作超时，请检查服务日志。' if timed_out else (error or ''))
        except GLib.Error as error:
            callback(1, '', str(error))

    process.communicate_utf8_async(None, None, finished)


class HonkTray(Gtk.Application):
    def __init__(self, url, runner=run_async):
        super().__init__(application_id='io.github.cordelia76544.HonkTray')
        self.url, self.runner = url, runner
        self.indicator = None
        self.busy = self.polling = False
        self.log_window = None
        self.connect('activate', self.activate_tray)

    def item(self, text, callback=None):
        item = Gtk.MenuItem(label=text)
        if callback:
            item.connect('activate', callback)
        self.menu.append(item)
        return item

    def activate_tray(self, *_):
        if self.indicator is not None:
            return
        self.hold()
        self.menu = Gtk.Menu()
        self.status = self.item('正在读取服务状态…')
        self.status.set_sensitive(False)
        self.menu.append(Gtk.SeparatorMenuItem())
        self.start = self.item('启动 honk', lambda *_: self.action('start'))
        self.stop = self.item('停止 honk', lambda *_: self.action('stop'))
        self.restart = self.item('重启 honk', lambda *_: self.action('restart'))
        for item in (self.start, self.stop, self.restart):
            item.set_sensitive(False)
        self.menu.append(Gtk.SeparatorMenuItem())
        self.item('打开 doona', self.open_ui)
        self.item('查看服务日志', self.show_logs)
        self.item('刷新状态', lambda *_: self.refresh())
        self.menu.append(Gtk.SeparatorMenuItem())
        self.item('退出托盘（不停止服务）', lambda *_: self.quit())
        self.menu.show_all()
        self.indicator = Indicator.Indicator.new_with_path(
            'honk-tray', 'honk-stopped', Indicator.IndicatorCategory.APPLICATION_STATUS, ICONS)
        self.indicator.set_title('honk')
        self.indicator.set_menu(self.menu)
        self.indicator.set_status(Indicator.IndicatorStatus.ACTIVE)
        self.refresh()
        GLib.timeout_add_seconds(3, self.refresh)

    def refresh(self):
        if self.polling or self.busy:
            return GLib.SOURCE_CONTINUE
        self.polling = True
        self.runner([SYSTEMCTL, '--system', 'show', UNIT,
                     '--property=LoadState,ActiveState,SubState'], self.received_state)
        return GLib.SOURCE_CONTINUE

    def received_state(self, code, output, error):
        self.polling = False
        if self.busy:
            return
        label, icon, can_start, can_stop = presentation(output, code)
        self.status.set_label(label)
        self.indicator.set_icon_full('honk-' + icon, label)
        self.start.set_sensitive(can_start)
        self.stop.set_sensitive(can_stop)
        self.restart.set_sensitive(can_stop)

    def action(self, verb):
        if self.busy or verb not in ('start', 'stop', 'restart'):
            return
        self.busy = True
        for item in (self.start, self.stop, self.restart):
            item.set_sensitive(False)
        self.status.set_label('正在执行操作，必要时请完成权限认证…')
        self.runner([SYSTEMCTL, '--system', verb, UNIT], self.action_finished, timeout=180)

    def action_finished(self, code, output, error):
        self.busy = False
        if code:
            self.error('服务操作未完成', error or output or '请查看服务日志。')
        self.refresh()

    def error(self, title, detail):
        dialog = Gtk.MessageDialog(message_type=Gtk.MessageType.ERROR,
                                   buttons=Gtk.ButtonsType.CLOSE, text=title)
        dialog.format_secondary_text(detail.strip()[:4000])
        self.add_window(dialog)
        dialog.connect('response', lambda widget, *_: widget.destroy())
        dialog.show_all()

    def open_ui(self, *_):
        try:
            Gio.AppInfo.launch_default_for_uri(self.url, None)
        except GLib.Error as error:
            self.error('无法打开浏览器', str(error))

    def show_logs(self, *_):
        if self.log_window:
            self.log_window.present()
            return
        window = Gtk.ApplicationWindow(application=self, title='honk 服务日志')
        self.log_window = window
        window.set_default_size(850, 480)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin=12)
        box.pack_start(Gtk.Label(label='最近 200 条日志；日志权限由系统决定。', xalign=0), False, False, 0)
        scroll = Gtk.ScrolledWindow()
        text = Gtk.TextView(editable=False, monospace=True, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        scroll.add(text)
        box.pack_start(scroll, True, True, 0)
        button = Gtk.Button(label='刷新日志')
        box.pack_start(button, False, False, 0)
        window.add(box)
        alive = True

        def closed(*_):
            nonlocal alive
            alive = False
            self.log_window = None

        def refresh(*_):
            button.set_sensitive(False)

            def done(code, output, error):
                if alive:
                    text.get_buffer().set_text(output + ('\n' + error if error else ''))
                    button.set_sensitive(True)
            self.runner([JOURNALCTL, '--system', '--unit=' + UNIT, '--lines=200',
                         '--no-pager', '--output=short-iso'], done)

        window.connect('destroy', closed)
        button.connect('clicked', refresh)
        window.show_all()
        refresh()


def self_test():
    # Exercise GTK, GI/indicator packaging and callbacks without a real system bus.
    calls, failures = [], []
    def fake(argv, callback, **_):
        calls.append(argv)
        GLib.idle_add(callback, 0, 'LoadState=loaded\nActiveState=inactive\n', '')
    app = HonkTray('http://127.0.0.1:9527/ui/', runner=fake)
    def test(*_):
        def check():
            try:
                assert app.start.get_sensitive() and not app.stop.get_sensitive()
                app.action('start')
                app.show_logs()
                assert any('start' in command for command in calls)
                assert any('--lines=200' in command for command in calls)
                app.log_window.destroy()
                print('honk-tray: indicator, state, service action and log window passed', flush=True)
            except Exception as error:
                failures.append(error)
                print(repr(error), file=sys.stderr)
            finally:
                app.quit()
            return False
        GLib.timeout_add(300, check)
    app.connect('activate', test)
    code = app.run([])
    return 1 if failures else code


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='honk system service tray')
    parser.add_argument('--ui-url', default='http://127.0.0.1:9527/ui/', type=validate_url)
    parser.add_argument('--self-test', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.self_test:
        sys.exit(self_test())
    app = HonkTray(args.ui_url)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, lambda: (app.quit(), False)[1])
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, lambda: (app.quit(), False)[1])
    sys.exit(app.run([]))
