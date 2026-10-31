"""Check the repository contract Home Assistant uses to discover/build the add-on."""
from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / 'transition_cues'


class PackagingTests(unittest.TestCase):
    def test_repository_discovery_and_addon_metadata(self):
        repo = yaml.safe_load((ROOT / 'repository.yaml').read_text())
        config = yaml.safe_load((ADDON / 'config.yaml').read_text())
        self.assertEqual(repo['url'], 'https://github.com/Benjamin-Leo-Code/transition-cues-app')
        self.assertEqual(config['slug'], ADDON.name)
        self.assertIsInstance(config['version'], str)
        self.assertEqual(set(config['arch']), {'amd64', 'aarch64'})
        self.assertNotIn('image', config)  # Supervisor builds the source on install/update.
        self.assertNotIn('map', config)  # No shared/config folder access.
        self.assertEqual(config['backup'], 'cold')
        self.assertEqual(config['ports']['8099/tcp'], 8099)
        self.assertIn('/api/state', config['watchdog'])
        self.assertIn(f"## {config['version']}", (ADDON / 'CHANGELOG.md').read_text())

    def test_complete_self_contained_build_context(self):
        for name in ['Dockerfile', 'server.py', 'README.md', 'DOCS.md', 'CHANGELOG.md',
                     'transition-cues-web/index.html', 'transition-cues-web/app.js', 'transition-cues-web/style.css']:
            self.assertTrue((ADDON / name).is_file(), name)
        self.assertFalse((ROOT / 'compose.yaml').exists())
        self.assertFalse((ROOT / 'config.yaml').exists())
        source = (ADDON / 'server.py').read_text()
        self.assertIn("Path('/data/transition-cues-data')", source)
        self.assertNotIn("os.environ.get('DATA_DIR'", source)


if __name__ == '__main__':
    unittest.main()
