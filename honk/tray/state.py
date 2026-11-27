"""Pure service-state presentation shared by the tray and tests."""
from urllib.parse import urlsplit


def validate_url(value):
    parsed = urlsplit(value)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        raise ValueError('UI URL must be an http(s) URL')
    return value


def presentation(output, returncode=0):
    props = dict(line.split('=', 1) for line in output.splitlines() if '=' in line)
    if props.get('LoadState') == 'not-found':
        return ('未安装 honk 服务', 'stopped', False, False)
    if returncode or props.get('LoadState') != 'loaded':
        return ('无法读取服务状态', 'failed', False, False)
    state = props.get('ActiveState', 'unknown')
    labels = {'active': '服务运行中', 'inactive': '服务已停止', 'failed': '服务启动失败',
              'activating': '服务启动中…', 'deactivating': '服务停止中…', 'reloading': '服务重载中…'}
    icon = 'running' if state == 'active' else 'failed' if state == 'failed' else 'stopped'
    return (labels.get(state, '服务状态：' + state), icon,
            state in ('inactive', 'failed'), state in ('active', 'activating', 'reloading'))
