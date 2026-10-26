#!/usr/bin/env python3
"""Reconcile site contents and HTTP metadata with S3, writing only changes."""

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, timedelta
import hashlib
import json
import mimetypes
from pathlib import Path, PurePosixPath
import re
from threading import Lock
from urllib.parse import urlencode


PRESERVE = (
    'ContentDisposition', 'ContentLanguage', 'Expires', 'StorageClass',
    'ServerSideEncryption', 'SSEKMSKeyId', 'BucketKeyEnabled', 'ObjectLockMode',
    'ObjectLockRetainUntilDate', 'ObjectLockLegalHoldStatus',
)
TYPES = {
    '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.xml': 'application/xml; charset=utf-8', '.txt': 'text/plain; charset=utf-8',
    '.woff2': 'font/woff2',
}


def safe_key(key):
    if not key or key.startswith('/') or '\\' in key or any(
            part in ('', '.', '..') for part in key.split('/')):
        raise ValueError(f'Invalid object key: {key!r}')
    return key


def redirect_keys(redirects):
    result = {}
    for key, target in redirects.items():
        key = safe_key(key if PurePosixPath(key).suffix else key + '/index.html')
        if key in result:
            raise ValueError(f'Duplicate redirect key: {key}')
        result[key] = target
    return result


def headers_for(key, redirects, today):
    lifetime = 3600
    if key.split('/')[0] in ('css', 'images', 'fonts', 'photos', 'talks'):
        lifetime = 86400
    if any(key.startswith(f'{day:%Y/%m/%d}/') for day in (today, today - timedelta(days=1))):
        lifetime = 300
    if key == '404.html':
        lifetime = 120
    content_type = TYPES.get(PurePosixPath(key).suffix.lower()) or mimetypes.guess_type(key)[0] or 'application/octet-stream'
    if key == 'feed.xml':
        content_type = 'application/rss+xml; charset=utf-8'
    if key == '.well-known/traffic-advice':
        content_type = 'application/trafficadvice+json; charset=utf-8'
    return {'ContentType': content_type, 'CacheControl': f'public, max-age={lifetime}',
            'ContentEncoding': None, 'WebsiteRedirectLocation': redirects.get(key)}


@dataclass
class LocalObject:
    key: str
    path: Path
    size: int
    md5: str
    headers: dict


def local_objects(root, redirects, today):
    root = Path(root).resolve()
    # An absent/empty build must never turn into a bucket-wide deletion.
    index = root / 'index.html'
    if not index.is_file() or not index.stat().st_size:
        raise ValueError('Build directory must contain a nonempty index.html')
    result = []
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError(f'Refusing symlink in build output: {path}')
        if not path.is_file():
            continue
        key = safe_key(path.relative_to(root).as_posix())
        digest = hashlib.md5()
        with path.open('rb') as stream:
            first = stream.read(1024 * 1024)
            if path.suffix in ('.html', '.css', '.js', '.xml', '.json') and first.startswith(b'\x1f\x8b'):
                raise ValueError(f'Expected plain content, found gzip bytes: {key}')
            digest.update(first)
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
        size = path.stat().st_size
        if size > 5 * 1024 ** 3:
            raise ValueError(f'Object exceeds single-PUT limit: {key}')
        result.append(LocalObject(key, path, size, digest.hexdigest(), headers_for(key, redirects, today)))
    found = {obj.key: obj for obj in result}
    for key, target in redirects.items():
        if key not in found or found[key].size:
            raise ValueError(f'Redirect must have an empty local stub: {key}')
        if '\r' in target or '\n' in target:
            raise ValueError(f'Invalid redirect target: {target!r}')
        if target.startswith('/'):
            if safe_key(target[1:]) not in found:
                raise ValueError(f'Missing redirect target: {target}')
        elif not target.startswith(('https://', 'http://')):
            raise ValueError(f'Redirect must be absolute or a local path: {target}')
    return result


def user_metadata(remote, obj):
    metadata = remote.get('Metadata', {}).copy()
    if 's3cmd-attrs' in metadata:
        metadata['s3cmd-attrs'] = re.sub(r'(?<=md5:)[0-9a-fA-F]{32}', obj.md5, metadata['s3cmd-attrs'])
    return metadata


def same_content(client, bucket, key, remote, obj):
    if remote['ContentLength'] != obj.size:
        return False
    etag = remote['ETag'].strip('"')
    # Single-part S3/SSE-S3 objects have content-MD5 ETags. Do not trust
    # a remembered checksum in user metadata, which another uploader can retain.
    if not remote.get('ServerSideEncryption', '').startswith('aws:kms') and re.fullmatch('[0-9a-f]{32}', etag):
        return etag == obj.md5
    # Multipart/KMS/opaque ETags are not content hashes. Compare actual bytes.
    response = client.get_object(Bucket=bucket, Key=key, IfMatch=remote['ETag'])
    digest = hashlib.md5()
    with response['Body'] as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest() == obj.md5


def acl_headers(acl):
    names = {'FULL_CONTROL': 'GrantFullControl', 'READ': 'GrantRead',
             'READ_ACP': 'GrantReadACP', 'WRITE_ACP': 'GrantWriteACP'}
    result = {}
    for grant in acl['Grants']:
        grantee = grant['Grantee']
        field = {'CanonicalUser': 'ID', 'Group': 'URI'}[grantee['Type']]
        value = f'{field.lower()}="{grantee[field]}"'
        result.setdefault(names[grant['Permission']], []).append(value)
    return {name: ', '.join(values) for name, values in result.items()}


def reconcile(client, root, redirects, bucket='chrisdown.name', prefix='', today=None,
              dry_run=False, workers=8):
    if prefix:
        prefix = safe_key(prefix.rstrip('/')) + '/'
    if not 1 <= workers <= 32:
        raise ValueError('Workers must be between 1 and 32')
    objects = local_objects(root, redirect_keys(redirects), today or date.today())
    remote_objects = {}
    for page in client.get_paginator('list_objects_v2').paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get('Contents', []):
            if not obj['Key'].startswith(prefix):
                raise ValueError('S3 listing returned an object outside the deployment prefix')
            remote_objects[obj['Key']] = obj

    def plan(obj):
        key = prefix + obj.key
        if key not in remote_objects:
            return ('upload', obj, {})
        # Read real metadata on every deployment, including unchanged bodies.
        remote = client.head_object(Bucket=bucket, Key=key)
        if not same_content(client, bucket, key, remote, obj):
            return ('upload', obj, remote)
        matches = all((remote.get(name) or None) == value for name, value in obj.headers.items())
        matches = matches and remote.get('Metadata', {}) == user_metadata(remote, obj)
        return ('unchanged' if matches else 'metadata', obj, remote)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        actions = list(pool.map(plan, objects))
        counts = {name: sum(action[0] == name for action in actions)
                  for name in ('upload', 'metadata', 'unchanged')}
        wanted = {prefix + obj.key for obj in objects}
        stale = [obj for key, obj in remote_objects.items() if key not in wanted]
        counts['delete'] = len(stale)
        output_lock = Lock()

        def log(message):
            with output_lock:
                print(message, flush=True)

        def apply(action):
            kind, obj, remote = action
            if kind == 'unchanged':
                return
            key = prefix + obj.key
            log(f'{"Would " if dry_run else ""}{kind}: {key}')
            if dry_run:
                return
            kwargs = {name: remote[name] for name in PRESERVE if name in remote}
            kwargs.update({name: value for name, value in obj.headers.items() if value is not None})
            kwargs.update(Bucket=bucket, Key=key, Metadata=user_metadata(remote, obj))
            if remote:
                kwargs.update(acl_headers(client.get_object_acl(Bucket=bucket, Key=key)))
            if kind == 'metadata':
                client.copy_object(**kwargs, CopySource={'Bucket': bucket, 'Key': key},
                                   CopySourceIfMatch=remote['ETag'],
                                   MetadataDirective='REPLACE', TaggingDirective='COPY')
            else:
                if remote:
                    tags = client.get_object_tagging(Bucket=bucket, Key=key)['TagSet']
                    if tags:
                        kwargs['Tagging'] = urlencode({tag['Key']: tag['Value'] for tag in tags})
                    kwargs['IfMatch'] = remote['ETag']
                else:
                    kwargs['IfNoneMatch'] = '*'
                with obj.path.open('rb') as stream:
                    client.put_object(**kwargs, Body=stream, ContentLength=obj.size,
                                      ContentMD5=base64.b64encode(bytes.fromhex(obj.md5)).decode())

        # Finish all writes successfully before considering any deletions.
        list(pool.map(apply, actions))

        def delete(obj):
            log(f'{"Would " if dry_run else ""}delete: {obj["Key"]}')
            if not dry_run:
                client.delete_object(Bucket=bucket, Key=obj['Key'], IfMatch=obj['ETag'])

        list(pool.map(delete, stale))
    print(('DRY RUN ' if dry_run else '') + json.dumps(counts, sort_keys=True), flush=True)
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default='_deploy', type=Path)
    parser.add_argument('--redirects', default='redirects.json', type=Path)
    parser.add_argument('--bucket', default='chrisdown.name')
    parser.add_argument('--prefix', default='')
    parser.add_argument('--workers', default=8, type=int)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    import boto3
    from botocore.config import Config
    client = boto3.client('s3', config=Config(max_pool_connections=args.workers,
                                            retries={'mode': 'standard', 'max_attempts': 3}))
    reconcile(client, args.source, json.loads(args.redirects.read_text()),
              args.bucket, args.prefix, dry_run=args.dry_run, workers=args.workers)


if __name__ == '__main__':
    main()
