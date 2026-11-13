#!/usr/bin/env python3
"""Pin the newest versioned honk release, including alpha/beta/rc, and its paired UI."""
import base64
import json
import os
from pathlib import Path
import re
import urllib.request

REPO = 'https://api.github.com/repos/daeuniverse/honk'
TAG = re.compile(r'v(\d+)\.(\d+)\.(\d+)(?:-(alpha|beta|rc)\.(\d+))?')


def version_key(tag):
    match = TAG.fullmatch(tag)
    if not match:
        return None
    major, minor, patch, stage, number = match.groups()
    return (int(major), int(minor), int(patch),
            {'alpha': 0, 'beta': 1, 'rc': 2, None: 3}[stage], int(number or 0))


def request_json(url):
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'honk-flake-updater'}
    if os.getenv('GH_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as response:
        return json.load(response)


def latest_release():
    releases = []
    page = 1
    while True:
        batch = request_json(f'{REPO}/releases?per_page=100&page={page}')
        releases.extend(r for r in batch if not r['draft'] and version_key(r['tag_name']) is not None)
        if len(batch) < 100:
            break
        page += 1
    if not releases:
        raise ValueError('No versioned honk releases found')
    return max(releases, key=lambda r: version_key(r['tag_name']))


def release_metadata(release, pins):
    tag = release['tag_name']
    if release['draft'] or version_key(tag) is None:
        raise ValueError(f'Not a versioned release: {tag}')
    match = re.search(r'^DOONA_VERSION=([0-9A-Za-z.+-]+)$', pins, re.MULTILINE)
    if not match:
        raise ValueError('Missing DOONA_VERSION in honk release pins')
    sources = {}
    for system, arch in [('x86_64-linux', 'x86_64'), ('aarch64-linux', 'aarch64')]:
        name = f'honk-core-{tag}-{arch}-unknown-linux-musl-full.tar.gz'
        matches = [a for a in release['assets'] if a['name'] == name]
        if len(matches) != 1:
            raise ValueError(f'Expected exactly one release asset: {name}')
        asset = matches[0]
        digest = asset.get('digest') or ''
        if not re.fullmatch(r'sha256:[0-9a-fA-F]{64}', digest):
            raise ValueError(f'Missing SHA256 digest: {name}')
        url = f'https://github.com/daeuniverse/honk/releases/download/{tag}/{name}'
        if asset['browser_download_url'] != url:
            raise ValueError(f'Unexpected download URL: {name}')
        sources[system] = {
            'url': url,
            'hash': 'sha256-' + base64.b64encode(bytes.fromhex(digest[7:])).decode(),
        }
    return {'version': tag.removeprefix('v'), 'doonaVersion': match[1], 'sources': sources}


def main():
    release = latest_release()
    # Read metadata as data; never execute the upstream shell file.
    content = request_json(f"{REPO}/contents/.github/ci/pins.env?ref={release['tag_name']}")
    pins = base64.b64decode(content['content']).decode()
    metadata = release_metadata(release, pins)
    path = Path(__file__).resolve().parents[1] / 'honk' / 'sources.json'
    if path.exists():
        old = json.loads(path.read_text())
        if version_key('v' + old['version']) > version_key('v' + metadata['version']):
            raise ValueError('Refusing to downgrade honk')
    path.write_text(json.dumps(metadata, indent=2) + '\n')
    print(f"honk {metadata['version']} / embedded doona {metadata['doonaVersion']}")


if __name__ == '__main__':
    main()
