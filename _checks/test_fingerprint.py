import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('fingerprint', Path(__file__).resolve().parents[1] / '_scripts/fingerprint.py')
fp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fp)


class FingerprintTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.write('fonts/a.woff2', b'font')
        self.write('css/a.css', b'@font-face{src:url(../fonts/a.woff2)}')
        self.write('js/a.js', b'console.log(42)')
        self.write('index.html', b'''<link rel=preload href='/fonts/a.woff2'>
<link rel=stylesheet href=/css/a.css><script src="/js/a.js"></script>''')

    def write(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def assets(self):
        return {p.name: p.read_bytes() for p in (self.root / 'assets').iterdir()}

    def run_build(self):
        fp.Fingerprinter(self.root).run()

    def test_final_css_references_same_fingerprinted_font_as_preload(self):
        self.run_build()
        assets = self.assets()
        self.assertEqual(3, len(assets))
        for name, data in assets.items():
            self.assertEqual(hashlib.sha256(data).hexdigest(), name.split('-')[0])
        font = next(name for name in assets if name.endswith('.woff2'))
        css = next(data for name, data in assets.items() if name.endswith('.css'))
        self.assertIn(('/assets/' + font).encode(), css)
        self.assertIn('/assets/' + font, (self.root / 'index.html').read_text())

    def test_idempotent_and_unrelated_content_does_not_change_assets(self):
        self.run_build()
        before = self.assets()
        page = (self.root / 'index.html').read_bytes()
        self.run_build()
        self.assertEqual(page, (self.root / 'index.html').read_bytes())
        self.write('other.html', b'<p>Changed post</p>')
        self.run_build()
        self.assertEqual(before, self.assets())

    def test_font_change_invalidates_dependent_css_only(self):
        first = fp.Fingerprinter(self.root)
        first.run()
        self.write('fonts/a.woff2', b'new font')
        second = fp.Fingerprinter(self.root)
        old_font = first.asset(self.root / 'fonts/a.woff2')
        new_font = second.asset(self.root / 'fonts/a.woff2')
        self.assertNotEqual(old_font, new_font)
        self.assertNotEqual(first.asset(self.root / 'css/a.css'), second.asset(self.root / 'css/a.css'))
        self.assertEqual(first.asset(self.root / 'js/a.js'), second.asset(self.root / 'js/a.js'))

    def test_only_url_attributes_change_not_code_or_other_attributes(self):
        text = '''<p title="src='/missing.js'">/js/a.js</p>
<script>const example = '<script src="/missing.js">';</script>
<code>&lt;script src="/missing.js"&gt;</code>
<script src='/js/a.js?x=1&amp;y=2#part'></script>
<script src='https://example.org/a.js'></script>'''
        self.write('nested/post.html', text.encode())
        self.run_build()
        result = (self.root / 'nested/post.html').read_text()
        self.assertIn('title="src=\'/missing.js\'"', result)
        self.assertIn("const example = '<script src=\"/missing.js\">';", result)
        self.assertIn('&lt;script src="/missing.js"&gt;', result)
        self.assertIn('?x=1&amp;y=2#part', result)
        self.assertIn("src='https://example.org/a.js'", result)

    def test_missing_asset_and_path_traversal_stop_build(self):
        self.write('index.html', b'<script src=/missing.js></script>')
        with self.assertRaisesRegex(ValueError, 'Missing local asset'):
            self.run_build()
        self.write('index.html', b'<script src=../escape.js></script>')
        with self.assertRaisesRegex(ValueError, 'escapes build directory'):
            self.run_build()

    def test_css_cycles_and_modified_hashed_content_are_rejected(self):
        self.write('css/a.css', b'@import url(a.css);')
        with self.assertRaisesRegex(ValueError, 'Circular CSS dependency'):
            self.run_build()
        self.write('css/a.css', b'body{color:red}')
        self.run_build()
        hashed = next((self.root / 'assets').glob('*-a.css'))
        hashed.write_text('tampered')
        with self.assertRaisesRegex(ValueError, 'Invalid fingerprint'):
            self.run_build()


if __name__ == '__main__':
    unittest.main()
