#!/usr/bin/env python3
"""Run site Python commands with private, automatically installed dependencies.

Usage: python3 -I _scripts/python_env.py [--prepare | Python arguments...]
The host needs Python 3.11+, venv and network access on the first run.
"""

import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ENV_VERSION = 1
PREFLIGHT = '''
import io, site, sys
import boto3
from PIL import Image
assert sys.prefix != sys.base_prefix, "Expected a virtual environment"
assert not site.ENABLE_USER_SITE, "User packages must be disabled"
for format in ("AVIF", "WEBP"):
    Image.new("RGB", (1, 1)).save(io.BytesIO(), format=format)
'''


class PythonEnvironment:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.requirements = self.root / 'requirements.txt'
        # A requirements or interpreter change gets a fresh environment, never
        # a partially upgraded set of packages from another build.
        identity = json.dumps([ENV_VERSION, str(Path(sys.executable).resolve()), sys.version,
                               sys.implementation.cache_tag]).encode()
        self.key = hashlib.sha256(identity + self.requirements.read_bytes()).hexdigest()
        self.path = self.root / '.build' / ('python-' + self.key[:16])
        self.python = self.path / 'bin/python'
        self.ready = self.path / '.ready'

    def prepare(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Concurrent rake invocations must not install into the same venv.
        with (self.path.parent / 'python.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if self.python.is_file() and self.ready.is_file() and self.ready.read_text() == self.key:
                return self.python
            self.ready.unlink(missing_ok=True)
            print(f'Preparing private Python environment: {self.path}', flush=True)
            if not self.python.is_file():
                subprocess.check_call([sys.executable, '-I', '-m', 'venv', str(self.path)])
            subprocess.check_call([
                str(self.python), '-I', '-m', 'pip', '--isolated',
                '--require-virtualenv', '--disable-pip-version-check',
                'install', '--no-input', '--only-binary=:all:',
                '--cache-dir', str(self.path.parent / 'pip-cache'),
                '-r', str(self.requirements),
            ])
            subprocess.check_call([str(self.python), '-I', '-m', 'pip', '--isolated', 'check'])
            # Test real encoders, not just version strings or plugin names.
            subprocess.check_call([str(self.python), '-I', '-c', PREFLIGHT])
            self.ready.write_text(self.key)
        return self.python

    def run(self, args):
        python = str(self.prepare())
        # Ignore PYTHONPATH/PYTHONHOME and user packages, while retaining the
        # command's script directory for imports between site scripts.
        os.execv(python, [python, '-E', '-s', *args])


def main():
    if sys.version_info < (3, 11):
        raise SystemExit('The site build requires Python 3.11 or newer')
    environment = PythonEnvironment(Path(__file__).resolve().parents[1])
    if sys.argv[1:] == ['--prepare']:
        print(environment.prepare())
    elif sys.argv[1:]:
        environment.run(sys.argv[1:])
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
