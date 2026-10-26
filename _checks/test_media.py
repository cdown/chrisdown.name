import hashlib
from html.parser import HTMLParser
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_scripts'))
import optimise_media as media


class Images(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.tags = []
        self.feed(text)
    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class MediaTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.cache = self.root / 'cache'
        self.photo = self.root / 'photo.jpg'
        Image.new('RGB', (600, 300), '#3c7b9a').save(self.photo)
        Image.new('RGB', (40, 20)).save(self.root / 'screen.png')

    def render(self, text):
        return media.MediaHTML(text, media.Photos(self.root, self.cache), self.root / 'index.html').result()

    def test_dimensions_loading_and_explicit_choices_are_preserved(self):
        tags = Images(self.render('''<img src=screen.png><img src=screen.png>
<img src=screen.png width=80 loading=eager decoding=sync>
<img src=screen.png height=10><iframe src=https://example.org></iframe>''')).tags
        images = [attrs for tag, attrs in tags if tag == 'img']
        self.assertEqual(('40', '20', 'eager', 'async'), tuple(images[0][key] for key in ('width', 'height', 'loading', 'decoding')))
        self.assertEqual('lazy', images[1]['loading'])
        self.assertEqual(('80', '40', 'eager', 'sync'), tuple(images[2][key] for key in ('width', 'height', 'loading', 'decoding')))
        self.assertEqual('20', images[3]['width'])
        self.assertEqual('lazy', next(attrs for tag, attrs in tags if tag == 'iframe')['loading'])

    def test_responsive_formats_hashes_and_jpeg_fallback(self):
        result = self.render('<a href=original><img src=photo.jpg alt="A &amp; B"></a>')
        tags = Images(result).tags
        self.assertEqual(1, result.count('<picture>'))
        self.assertEqual(1, result.count('<a '))
        sources = [attrs for tag, attrs in tags if tag == 'source']
        self.assertEqual(['image/avif', 'image/webp'], [attrs['type'] for attrs in sources])
        for attrs in sources:
            for candidate in attrs['srcset'].split(', '):
                url, width = candidate.split()
                data = (self.root / url.lstrip('/')).read_bytes()
                self.assertIn(hashlib.sha256(data).hexdigest(), url)
                with Image.open(self.root / url.lstrip('/')) as image:
                    self.assertEqual(int(width[:-1]), image.width)
                    self.assertLessEqual(image.width, 600)
                    self.assertEqual(2 * image.height, image.width)
        img = next(attrs for tag, attrs in tags if tag == 'img')
        self.assertEqual('photo.jpg', img['src'])
        self.assertEqual('A & B', img['alt'])
        self.assertEqual(result, self.render(result))

    def test_exif_orientation_is_used_for_dimensions_and_derivatives(self):
        image = Image.new('RGB', (600, 300))
        exif = Image.Exif()
        exif[274] = 6
        image.save(self.photo, exif=exif)
        result = self.render('<img src=photo.jpg>')
        img = next(attrs for tag, attrs in Images(result).tags if tag == 'img')
        self.assertEqual(('300', '600'), (img['width'], img['height']))
        for path in (self.root / 'assets').iterdir():
            with Image.open(path) as variant:
                self.assertEqual((300, 600), variant.size)
                self.assertNotIn(274, variant.getexif())

    def test_existing_picture_custom_widgets_and_remote_urls(self):
        text = '<picture><img src=photo.jpg></picture><img class=nonstandard src=missing.png><img class=leaflet-marker-icon src=missing.png><img src=https://example.org/a.png>'
        result = self.render(text)
        self.assertEqual(1, result.count('<picture>'))
        tags = Images(result).tags
        images = [attrs for tag, attrs in tags if tag == 'img']
        self.assertNotIn('width', images[1])
        self.assertNotIn('width', images[2])
        self.assertNotIn('width', images[3])
        self.assertEqual('lazy', images[3]['loading'])

    def test_cache_reuse_source_and_settings_invalidation(self):
        self.render('<img src=photo.jpg>')
        before = {p: p.stat().st_mtime_ns for p in self.cache.rglob('*') if p.is_file()}
        self.render('<img src=photo.jpg>')
        self.assertEqual(before, {p: p.stat().st_mtime_ns for p in self.cache.rglob('*') if p.is_file()})
        Image.new('RGB', (600, 300), 'red').save(self.photo)
        self.render('<img src=photo.jpg>')
        self.assertEqual(2, len(list(self.cache.iterdir())))
        with patch.object(media, 'WIDTHS', (200,)):
            self.render('<img src=photo.jpg>')
        self.assertEqual(3, len(list(self.cache.iterdir())))

    def test_missing_files_and_paths_outside_build_fail(self):
        for url in ('missing.png', '../outside.png'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.render(f'<img src={url}>')

    def test_explicit_responsive_sources_and_priority_are_preserved(self):
        result = self.render('<img src=photo.jpg srcset="photo.jpg 600w" sizes="50vw"><img src=screen.png fetchpriority=high>')
        self.assertNotIn('<picture>', result)
        images = [attrs for tag, attrs in Images(result).tags if tag == 'img']
        self.assertEqual('photo.jpg 600w', images[0]['srcset'])
        self.assertEqual('50vw', images[0]['sizes'])
        self.assertEqual('eager', images[1]['loading'])

    def test_extreme_aspect_ratio_never_generates_zero_height(self):
        Image.new('RGB', (2000, 1)).save(self.photo)
        self.render('<img src=photo.jpg>')
        for path in (self.root / 'assets').iterdir():
            with Image.open(path) as image:
                self.assertEqual(1, image.height)


if __name__ == '__main__':
    unittest.main()
