import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('tray_state', Path(__file__).resolve().parents[1] / 'honk/tray/state.py')
state = importlib.util.module_from_spec(spec)
spec.loader.exec_module(state)


class TrayStateTests(unittest.TestCase):
    def test_running_is_service_status(self):
        label, icon, start, stop = state.presentation('LoadState=loaded\nActiveState=active\n')
        self.assertEqual(label, '服务运行中')
        self.assertEqual((icon, start, stop), ('running', False, True))

    def test_failure_can_be_started_again(self):
        self.assertEqual(state.presentation('LoadState=loaded\nActiveState=failed\n')[1:],
                         ('failed', True, False))

    def test_missing_and_unreadable_units_disable_actions(self):
        for output, code in [('LoadState=not-found\n', 0), ('', 1)]:
            self.assertEqual(state.presentation(output, code)[2:], (False, False))

    def test_starting_can_be_stopped_but_not_started_again(self):
        self.assertEqual(state.presentation('LoadState=loaded\nActiveState=activating\n')[2:],
                         (False, True))

    def test_browser_url_rejects_non_web_schemes(self):
        self.assertEqual(state.validate_url('http://127.0.0.1:9527/ui/'), 'http://127.0.0.1:9527/ui/')
        for url in ('file:///etc/passwd', 'javascript:alert(1)', 'https://'):
            with self.assertRaises(ValueError):
                state.validate_url(url)
