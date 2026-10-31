#!/usr/bin/env python3
"""Pin the latest stable release; require GitHub's SHA256 asset digests."""
import base64
import json
import os
from pathlib import Path
import urllib.request

req = urllib.request.Request(
    'https://api.github.com/repos/reF1nd/sing-box-releases/releases/latest',
    headers={'Accept': 'application/vnd.github+json',
             **({'Authorization': 'Bearer ' + os.environ['GH_TOKEN']} if os.getenv('GH_TOKEN') else {})})
with urllib.request.urlopen(req, timeout=60) as response:
    release = json.load(response)
assert not release['prerelease'] and not release['draft']
version = release['tag_name'].removeprefix('v')
sources = {}
for system, arch in [('x86_64-linux', 'amd64'), ('aarch64-linux', 'arm64')]:
    name = f'SFL-{version}-{arch}.deb'
    asset, = [a for a in release['assets'] if a['name'] == name]
    digest = asset.get('digest', '')
    assert digest.startswith('sha256:') and len(digest) == 71, f'Missing SHA256: {name}'
    sources[system] = {'url': asset['browser_download_url'],
                       'hash': 'sha256-' + base64.b64encode(bytes.fromhex(digest[7:])).decode()}
path = Path(__file__).resolve().parents[1] / 'sources.json'
path.write_text(json.dumps({'version': version, 'sources': sources}, indent=2) + '\n')
print(version)
