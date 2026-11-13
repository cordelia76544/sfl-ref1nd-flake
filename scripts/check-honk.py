#!/usr/bin/env python3
"""Exercise both embedded UIs in unprivileged mock mode, without changing routing."""
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request


def check(binary, edition):
    with tempfile.TemporaryDirectory(prefix='honk-check-') as directory:
        root = Path(directory)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        config = root / 'config.dae'
        config.write_text(f"""
global {{
    data_dir: '{root}'
    nfqueue_enable: false
    preconnect_node_count: 0
    udp_warm_node_count: 0
    auto_config_kernel_parameter: false
}}
routing {{ fallback: direct }}
experimental {{
    native_api {{
        enabled: true
        listen: '127.0.0.1:{port}'
        password_auth: true
        config_write: true
        ui: '{edition}'
    }}
}}
""")
        base = f'http://127.0.0.1:{port}/ui/'
        # Bypass any CI proxy environment for this loopback-only request.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with (root / 'log').open('w+') as log:
            process = subprocess.Popen([binary, '--config', str(config), '--data-dir', str(root),
                                        '--mock-ebpf'], stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 30
                while True:
                    if process.poll() is not None:
                        raise RuntimeError('honk exited before serving the UI')
                    try:
                        with opener.open(base, timeout=2) as response:
                            html = response.read().decode()
                        break
                    except (urllib.error.URLError, TimeoutError):
                        if time.monotonic() >= deadline:
                            raise RuntimeError('Timed out waiting for embedded UI')
                        time.sleep(0.2)
                if '<html' not in html.lower():
                    raise RuntimeError('UI response is not HTML')
                assets = re.findall(r'(?:src|href)=["\']([^"\']+\.js(?:\?[^"\']*)?)["\']', html)
                if not assets:
                    raise RuntimeError('Embedded UI has no JavaScript bundle')
                asset_url = urllib.parse.urljoin(base, assets[0])
                if urllib.parse.urlsplit(asset_url).netloc != urllib.parse.urlsplit(base).netloc:
                    raise RuntimeError('Expected a local embedded JavaScript bundle')
                with opener.open(asset_url, timeout=5) as response:
                    if 'javascript' not in response.headers.get('Content-Type', '') or not response.read():
                        raise RuntimeError('Embedded JavaScript bundle is missing')
                print(f'{edition}: HTML and JavaScript served successfully')
            except Exception:
                log.flush()
                log.seek(0)
                print(log.read(), file=sys.stderr)
                raise
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()


if __name__ == '__main__':
    binary = str(Path(sys.argv[1]).resolve())
    subprocess.run([binary, '--version'], check=True)
    for edition in ('embedded', 'embedded-lite'):
        check(binary, edition)
