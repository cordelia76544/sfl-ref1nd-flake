import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('update_honk', Path(__file__).resolve().parents[1] / 'scripts/update-honk.py')
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)


class UpdateHonkTests(unittest.TestCase):
    def release(self, tag='v0.1.0-beta.6'):
        names = [f'honk-core-{tag}-{arch}-unknown-linux-musl-full.tar.gz'
                 for arch in ('x86_64', 'aarch64')]
        return {'tag_name': tag, 'draft': False, 'prerelease': True,
                'assets': [{'name': name, 'digest': 'sha256:' + '12' * 32,
                            'browser_download_url': f'https://github.com/daeuniverse/honk/releases/download/{tag}/{name}'}
                           for name in names]}

    def test_version_selection_excludes_debug_and_drafts(self):
        releases = [self.release(t) for t in ('debug', 'debug-diag.issue-415.3',
                    'v0.1.0-beta.9', 'v0.1.0-beta.10', 'v0.1.0-rc.1', 'v0.1.0')]
        releases.append(dict(self.release('v9.0.0'), draft=True))
        with patch.object(updater, 'request_json', return_value=releases):
            self.assertEqual(updater.latest_release()['tag_name'], 'v0.1.0')
        self.assertGreater(updater.version_key('v0.1.0-beta.10'), updater.version_key('v0.1.0-beta.9'))

    def test_both_architectures_and_paired_doona(self):
        info = updater.release_metadata(self.release(), 'DOONA_VERSION=0.1.0-rc.6\n')
        self.assertEqual(info['doonaVersion'], '0.1.0-rc.6')
        self.assertEqual(set(info['sources']), {'x86_64-linux', 'aarch64-linux'})

    def test_missing_asset_or_digest_fails_closed(self):
        for broken in ('asset', 'digest'):
            release = self.release()
            if broken == 'asset':
                release['assets'].pop()
            else:
                release['assets'][0]['digest'] = None
            with self.subTest(broken=broken), self.assertRaises(ValueError):
                updater.release_metadata(release, 'DOONA_VERSION=0.1.0-rc.6\n')

    def test_missing_pairing_fails(self):
        with self.assertRaises(ValueError):
            updater.release_metadata(self.release(), 'DOONA_SHA256=abc\n')


if __name__ == '__main__':
    unittest.main()
