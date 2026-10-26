#!/usr/bin/env python3
"""Fingerprint final CSS, JavaScript and fonts after minification/PurgeCSS."""

import argparse
import hashlib
from html import escape, unescape
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit, urlunsplit

ASSET = re.compile(r'assets/([0-9a-f]{64})-[^/]+\.(?:css|js|woff2|webp|avif)\Z')
ATTR = re.compile(r'''\s+([a-z_:][-a-z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))''', re.I)
CSS_URL = re.compile(r'''url\(\s*(['"]?)(.*?)\1\s*\)''', re.I)
EXTENSIONS = {'.css', '.js', '.woff2'}


class HTMLAssets(HTMLParser):
    def __init__(self, text, rewrite):
        super().__init__(convert_charrefs=False)
        self.text, self.rewrite, self.edits = text, rewrite, []
        self.lines = [0]
        self.lines.extend(match.end() for match in re.finditer('\n', text))
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        raw = self.get_starttag_text()
        def replace(match):
            if match[1].lower() not in ('src', 'href'):
                return match[0]
            old = unescape(next(value for value in match.groups()[1:] if value is not None))
            new = self.rewrite(old)
            return match[0] if old == new else f' {match[1]}="{escape(new, quote=True)}"'
        updated = ATTR.sub(replace, raw)
        if updated != raw:
            line, column = self.getpos()
            start = self.lines[line - 1] + column
            self.edits.append((start, start + len(raw), updated))

    handle_startendtag = handle_starttag

    def result(self):
        text = self.text
        for start, end, replacement in reversed(self.edits):
            text = text[:start] + replacement + text[end:]
        return text


class Fingerprinter:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.done, self.pending = {}, set()

    def url(self, url, relative_to):
        parts = urlsplit(url)
        if parts.scheme or parts.netloc or not parts.path:
            return url
        if Path(parts.path).suffix.lower() not in EXTENSIONS:
            return url
        path = (self.root / unquote(parts.path).lstrip('/') if parts.path.startswith('/')
                else relative_to.parent / unquote(parts.path)).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError(f'Asset escapes build directory: {url}')
        if not path.is_file():
            raise ValueError(f'Missing local asset: {url} in {relative_to}')
        key = path.relative_to(self.root).as_posix()
        existing = ASSET.fullmatch(key)
        if existing:
            if hashlib.sha256(path.read_bytes()).hexdigest() != existing[1]:
                raise ValueError(f'Invalid fingerprint: {key}')
            return url
        target = self.asset(path)
        return urlunsplit(('', '', target, parts.query, parts.fragment))

    def asset(self, path):
        if path in self.done:
            return self.done[path]
        if path in self.pending:
            raise ValueError(f'Circular CSS dependency: {path}')
        self.pending.add(path)
        data = path.read_bytes()
        if path.suffix.lower() == '.css':
            def replace(match):
                old = match[2].strip()
                new = self.url(old, path)
                return match[0] if old == new else f'url("{new}")'
            data = CSS_URL.sub(replace, data.decode()).encode()
        digest = hashlib.sha256(data).hexdigest()
        target = f'/assets/{digest}-{path.name}'
        destination = self.root / target.lstrip('/')
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and destination.read_bytes() != data:
            raise ValueError(f'Fingerprint collision: {target}')
        destination.write_bytes(data)
        self.pending.remove(path)
        self.done[path] = target
        return target

    def run(self):
        for page in sorted(self.root.rglob('*.html')):
            text = page.read_text()
            updated = HTMLAssets(text, lambda url: self.url(url, page)).result()
            if updated != text:
                page.write_text(updated)
        print(f'Fingerprinted {len(self.done)} assets')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', nargs='?', default='_deploy', type=Path)
    Fingerprinter(parser.parse_args().root).run()
