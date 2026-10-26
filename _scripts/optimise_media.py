#!/usr/bin/env python3
"""Reserve image space and generate cached responsive photo derivatives."""

import argparse
import hashlib
from html import escape
from io import BytesIO
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

from PIL import Image, ImageOps, features, __version__ as pillow_version
from fingerprint import HTMLAssets

WIDTHS = (480, 960, 1440)
FORMATS = {'avif': {'quality': 60, 'speed': 6, 'max_threads': 2},
           'webp': {'quality': 82, 'method': 6}}
SIZES = '(min-width: 780px) 720px, calc(100vw - 54px)'
CACHE_VERSION = 1


def start_tag(tag, attrs):
    return '<' + tag + ''.join(' ' + key if value is None else
                              f' {key}="{escape(str(value), quote=True)}"'
                              for key, value in attrs.items()) + '>'


class Photos:
    def __init__(self, root, cache):
        self.root, self.cache = Path(root).resolve(), Path(cache)
        self.done = {}

    def image(self, url, page):
        parts = urlsplit(url)
        if parts.scheme or parts.netloc or not parts.path:
            return None
        path = (self.root / unquote(parts.path).lstrip('/') if parts.path.startswith('/')
                else page.parent / unquote(parts.path)).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError(f'Image escapes build directory: {url}')
        # SVGs already have their own viewBox; leave their representation alone.
        if path.suffix.lower() not in ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.avif'):
            return None
        if not path.is_file():
            raise ValueError(f'Missing local image: {url}')
        if path in self.done:
            return self.done[path]
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source)
            width, height = image.size
            sources = []
            if source.format == 'JPEG':
                settings = json.dumps([CACHE_VERSION, WIDTHS, FORMATS, pillow_version,
                                       features.version('avif'), features.version('webp')], sort_keys=True).encode()
                key = hashlib.sha256(path.read_bytes() + settings).hexdigest()
                cache = self.cache / key
                cache.mkdir(parents=True, exist_ok=True)
                image = image.convert('RGB')
                for fmt, options in FORMATS.items():
                    candidates = []
                    for target_width in sorted({min(w, width) for w in WIDTHS}):
                        cached = cache / f'{target_width}.{fmt}'
                        if not cached.is_file():
                            resized = image.resize((target_width, max(1, round(height * target_width / width))), Image.Resampling.LANCZOS)
                            stream = BytesIO()
                            resized.save(stream, format=fmt, icc_profile=source.info.get('icc_profile'), **options)
                            temporary = cached.with_suffix('.tmp')
                            temporary.write_bytes(stream.getvalue())
                            temporary.replace(cached)
                        data = cached.read_bytes()
                        name = f'{hashlib.sha256(data).hexdigest()}-{path.stem}-{target_width}.{fmt}'
                        destination = self.root / 'assets' / name
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        destination.write_bytes(data)
                        candidates.append(f'/assets/{name} {target_width}w')
                    sources.append(start_tag('source', {'type': f'image/{fmt}',
                                                       'srcset': ', '.join(candidates), 'sizes': SIZES}))
            result = (width, height, ''.join(sources))
            self.done[path] = result
            return result


class MediaHTML(HTMLAssets):
    def __init__(self, text, photos, page):
        self.photos, self.page = photos, page
        self.image_index, self.picture_depth = 0, 0
        super().__init__(text, None)

    def handle_starttag(self, tag, attributes):
        if tag == 'picture':
            self.picture_depth += 1
        if tag not in ('img', 'iframe'):
            return
        attrs = dict(attributes)
        original = self.get_starttag_text()
        if tag == 'iframe':
            attrs.setdefault('loading', 'lazy')
            updated = start_tag(tag, attrs)
        else:
            classes = (attrs.get('class') or '').split()
            if 'nonstandard' in classes or 'leaflet-marker-icon' in classes:
                return
            self.image_index += 1
            attrs.setdefault('loading', 'eager' if self.image_index == 1 or attrs.get('fetchpriority') == 'high' else 'lazy')
            attrs.setdefault('decoding', 'async')
            info = self.photos.image(attrs.get('src', ''), self.page)
            sources = ''
            if info:
                width, height, sources = info
                if 'width' not in attrs and 'height' not in attrs:
                    attrs.update(width=str(width), height=str(height))
                elif 'width' in attrs and 'height' not in attrs and str(attrs['width']).isdigit():
                    attrs['height'] = str(round(height * int(attrs['width']) / width))
                elif 'height' in attrs and 'width' not in attrs and str(attrs['height']).isdigit():
                    attrs['width'] = str(round(width * int(attrs['height']) / height))
            updated = start_tag(tag, attrs)
            if sources and not self.picture_depth and 'srcset' not in attrs:
                updated = '<picture>' + sources + updated + '</picture>'
        if updated != original:
            line, column = self.getpos()
            start = self.lines[line - 1] + column
            self.edits.append((start, start + len(original), updated))

    handle_startendtag = handle_starttag

    def handle_endtag(self, tag):
        if tag == 'picture':
            self.picture_depth -= 1


def optimise(root, cache):
    root = Path(root).resolve()
    photos = Photos(root, cache)
    for page in sorted(root.rglob('*.html')):
        text = page.read_text()
        updated = MediaHTML(text, photos, page).result()
        if updated != text:
            page.write_text(updated)
    print(f'Optimised {len(photos.done)} local images')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', nargs='?', default='_deploy', type=Path)
    parser.add_argument('--cache', default='.jekyll-cache/media', type=Path)
    args = parser.parse_args()
    optimise(args.root, args.cache)
