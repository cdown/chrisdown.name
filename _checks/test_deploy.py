import base64
import contextlib
from copy import deepcopy
from datetime import date
import hashlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest
from urllib.parse import parse_qsl

spec = importlib.util.spec_from_file_location('site_deploy', Path(__file__).resolve().parents[1] / '_scripts/deploy.py')
deploy = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = deploy
spec.loader.exec_module(deploy)

OWNER_ACL = {'Owner': {'ID': 'owner'}, 'Grants': [
    {'Grantee': {'Type': 'CanonicalUser', 'ID': 'owner'}, 'Permission': 'FULL_CONTROL'},
]}
PUBLIC_ACL = deepcopy(OWNER_ACL)
PUBLIC_ACL['Grants'].append({'Grantee': {'Type': 'Group', 'URI': 'http://acs.amazonaws.com/groups/global/AllUsers'}, 'Permission': 'READ'})


class FakeS3:
    """An S3 fixture that models replacement, ACL reset, tags and conditions."""
    def __init__(self):
        self.objects = {}
        self.calls = []
        self.fail_write = None
        self.fail_head = False
        self.concurrent_change = False

    def seed(self, key, body=b'page', acl=None, tags=None, **headers):
        self.objects[key] = dict(Body=body, ETag='"' + hashlib.md5(body).hexdigest() + '"',
                                 ContentLength=len(body), Metadata={},
                                 ACL=deepcopy(acl or OWNER_ACL), Tags=tags or [], **headers)

    def get_paginator(self, name):
        assert name == 'list_objects_v2'
        client = self

        class Paginator:
            def paginate(self, Bucket, Prefix):
                client.calls.append(('list', Prefix))
                items = [{'Key': key, 'ETag': obj['ETag']} for key, obj in sorted(client.objects.items()) if key.startswith(Prefix)]
                # Exercise pagination on every test with more than two keys.
                for index in range(0, len(items), 2):
                    yield {'Contents': items[index:index + 2]}
        return Paginator()

    def head_object(self, Bucket, Key):
        self.calls.append(('head', Key))
        if self.fail_head:
            raise RuntimeError('Access denied')
        return {name: deepcopy(value) for name, value in self.objects[Key].items() if name not in ('Body', 'ACL', 'Tags')}

    def get_object(self, Bucket, Key, IfMatch):
        self.calls.append(('get', Key))
        assert self.objects[Key]['ETag'] == IfMatch
        return {'Body': io.BytesIO(self.objects[Key]['Body'])}

    def get_object_acl(self, Bucket, Key):
        self.calls.append(('acl', Key))
        result = deepcopy(self.objects[Key]['ACL'])
        if self.concurrent_change:
            self.objects[Key]['ETag'] = '"concurrent"'
        return result

    def get_object_tagging(self, Bucket, Key):
        self.calls.append(('tags', Key))
        return {'TagSet': deepcopy(self.objects[Key]['Tags'])}

    def write(self, kind, kwargs, body, tags):
        key = kwargs['Key']
        self.calls.append((kind, key))
        if self.fail_write == key:
            raise RuntimeError('Injected write failure')
        old = self.objects.get(key)
        condition = kwargs.get('IfMatch', kwargs.get('CopySourceIfMatch'))
        if condition is not None and (not old or condition != old['ETag']):
            raise RuntimeError('Precondition failed')
        if kwargs.get('IfNoneMatch') == '*' and old:
            raise RuntimeError('Already exists')
        acl = deepcopy(OWNER_ACL)
        if old:
            expected = deploy.acl_headers(old['ACL'])
            if all(kwargs.get(name) == value for name, value in expected.items()):
                acl = deepcopy(old['ACL'])
        fields = set(deploy.PRESERVE) | {'ContentType', 'CacheControl', 'ContentEncoding', 'WebsiteRedirectLocation', 'Metadata'}
        headers = {name: deepcopy(value) for name, value in kwargs.items() if name in fields}
        metadata = headers.pop('Metadata', {})
        self.seed(key, body, acl, tags, **headers)
        self.objects[key]['Metadata'] = metadata

    def put_object(self, **kwargs):
        body = kwargs['Body'].read()
        assert len(body) == kwargs['ContentLength']
        assert base64.b64decode(kwargs['ContentMD5']) == hashlib.md5(body).digest()
        tags = [{'Key': key, 'Value': value} for key, value in parse_qsl(kwargs.get('Tagging', ''))]
        self.write('put', kwargs, body, tags)

    def copy_object(self, **kwargs):
        assert kwargs['MetadataDirective'] == 'REPLACE'
        assert kwargs['TaggingDirective'] == 'COPY'
        assert kwargs['CopySource']['Key'] == kwargs['Key']
        old = self.objects[kwargs['Key']]
        self.write('copy', kwargs, old['Body'], deepcopy(old['Tags']))

    def delete_object(self, Bucket, Key, IfMatch):
        self.calls.append(('delete', Key))
        assert self.objects[Key]['ETag'] == IfMatch
        del self.objects[Key]

    def writes(self):
        return [call for call in self.calls if call[0] in ('put', 'copy', 'delete')]


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.file('index.html', b'page')
        self.client = FakeS3()
        self.today = date(2026, 1, 1)

    def file(self, key, body=b'page'):
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)

    def run_deploy(self, redirects=None, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return deploy.reconcile(self.client, self.root, redirects or {}, today=kwargs.pop('today', self.today), workers=1, **kwargs)

    def deploy_once(self, redirects=None, **kwargs):
        self.run_deploy(redirects, **kwargs)
        self.client.calls.clear()

    def asset(self, body=b'body{}', name='style.css'):
        key = f'assets/{hashlib.sha256(body).hexdigest()}-{name}'
        self.file(key, body)
        return key

    def test_fingerprinted_assets_have_immutable_headers_and_precede_html(self):
        key = self.asset()
        self.file('2020/post.html')
        self.run_deploy()
        self.assertEqual('public, max-age=31536000, immutable', self.client.objects[key]['CacheControl'])
        self.assertEqual('text/css; charset=utf-8', self.client.objects[key]['ContentType'])
        writes = self.client.writes()
        self.assertLess(writes.index(('put', key)), writes.index(('put', '2020/post.html')))
        self.assertLess(writes.index(('put', key)), writes.index(('put', 'index.html')))

    def test_old_fingerprints_are_retained_with_prefix_but_old_pages_are_removed(self):
        old = self.asset()
        self.file('old.html')
        self.deploy_once(prefix='preview/')
        (self.root / old).unlink()
        (self.root / 'old.html').unlink()
        new = self.asset(b'body{color:red}')
        result = self.run_deploy(prefix='preview/')
        self.assertIn('preview/' + old, self.client.objects)
        self.assertIn('preview/' + new, self.client.objects)
        self.assertNotIn('preview/old.html', self.client.objects)
        self.assertEqual(1, result['delete'])

    def test_bad_fingerprint_or_unversioned_asset_fails_before_s3_access(self):
        key = self.asset()
        self.file(key, b'changed')
        with self.assertRaisesRegex(ValueError, 'does not match content'):
            self.run_deploy()
        self.assertEqual([], self.client.calls)
        (self.root / key).unlink()
        self.file('assets/style.css')
        with self.assertRaisesRegex(ValueError, 'Invalid fingerprinted asset name'):
            self.run_deploy()
        self.assertEqual([], self.client.calls)

    def test_existing_immutable_asset_is_never_overwritten(self):
        key = self.asset()
        self.client.seed(key, b'different bytes')
        with self.assertRaisesRegex(ValueError, 'Refusing to overwrite immutable asset'):
            self.run_deploy()
        self.assertEqual([], self.client.writes())

    def test_failed_asset_upload_leaves_html_and_stale_pages_untouched(self):
        key = self.asset()
        self.file('2020/post.html')
        self.client.seed('stale.html')
        self.client.fail_write = key
        with self.assertRaises(RuntimeError):
            self.run_deploy()
        self.assertNotIn('index.html', self.client.objects)
        self.assertNotIn('2020/post.html', self.client.objects)
        self.assertIn('stale.html', self.client.objects)

    def test_immutable_metadata_can_be_repaired_without_changing_bytes(self):
        key = self.asset(b'font', 'font.woff2')
        self.deploy_once()
        self.client.objects[key]['CacheControl'] = 'max-age=0'
        result = self.run_deploy()
        self.assertEqual(1, result['metadata'])
        self.assertEqual([('copy', key)], self.client.writes())
        self.assertEqual('font/woff2', self.client.objects[key]['ContentType'])
        self.assertEqual('public, max-age=31536000, immutable', self.client.objects[key]['CacheControl'])

    def test_photo_derivatives_have_explicit_mime_types(self):
        for extension in ('avif', 'webp'):
            key = self.asset(b'encoded image', f'photo.{extension}')
            self.run_deploy()
            self.assertEqual(f'image/{extension}', self.client.objects[key]['ContentType'])
            self.assertEqual('public, max-age=31536000, immutable', self.client.objects[key]['CacheControl'])

    def test_new_upload_has_final_headers_without_later_copy(self):
        self.file('feed.xml')
        self.file('.well-known/traffic-advice')
        self.file('css/style.css')
        self.file('js/app.js')
        result = self.run_deploy()
        self.assertEqual(5, result['upload'])
        self.assertEqual(0, result['metadata'])
        self.assertEqual('application/rss+xml; charset=utf-8', self.client.objects['feed.xml']['ContentType'])
        self.assertEqual('application/trafficadvice+json; charset=utf-8', self.client.objects['.well-known/traffic-advice']['ContentType'])
        self.assertEqual('public, max-age=86400', self.client.objects['css/style.css']['CacheControl'])
        self.assertTrue(all('ContentEncoding' not in obj for obj in self.client.objects.values()))
        self.assertFalse(any(kind == 'copy' for kind, _ in self.client.writes()))

    def test_second_deployment_reads_headers_but_makes_no_writes(self):
        self.file('space and \u00e9.html')
        self.file('.hidden-resource')
        self.deploy_once()
        result = self.run_deploy()
        self.assertEqual(3, result['unchanged'])
        self.assertEqual([], self.client.writes())
        self.assertEqual(3, sum(kind == 'head' for kind, _ in self.client.calls))

    def test_stale_headers_and_stored_checksum_are_repaired_by_one_copy(self):
        self.deploy_once()
        obj = self.client.objects['index.html']
        obj.update(ContentType='bad/type', ContentEncoding='gzip', CacheControl='max-age=1')
        obj['Metadata'] = {'custom': 'keep', 's3cmd-attrs': 'md5:' + '0' * 32}
        result = self.run_deploy()
        self.assertEqual(1, result['metadata'])
        self.assertEqual([('copy', 'index.html')], self.client.writes())
        obj = self.client.objects['index.html']
        self.assertNotIn('ContentEncoding', obj)
        self.assertEqual('keep', obj['Metadata']['custom'])
        self.assertEqual('md5:' + hashlib.md5(b'page').hexdigest(), obj['Metadata']['s3cmd-attrs'])

    def test_changed_body_and_headers_are_one_upload_and_preserve_properties(self):
        self.deploy_once()
        obj = self.client.objects['index.html']
        obj.update(ACL=deepcopy(PUBLIC_ACL), Tags=[{'Key': 'space', 'Value': 'a + b'}],
                   ServerSideEncryption='AES256', ContentDisposition='inline',
                   ContentLanguage='en', Expires='tomorrow', StorageClass='STANDARD_IA',
                   ContentEncoding='gzip', WebsiteRedirectLocation='/old', Metadata={'custom': 'keep'})
        self.file('index.html', b'changed')
        self.run_deploy()
        self.assertEqual([('put', 'index.html')], self.client.writes())
        obj = self.client.objects['index.html']
        self.assertEqual(b'changed', obj['Body'])
        self.assertEqual(PUBLIC_ACL, obj['ACL'])
        self.assertEqual([{'Key': 'space', 'Value': 'a + b'}], obj['Tags'])
        for name, value in {'ServerSideEncryption': 'AES256', 'ContentDisposition': 'inline',
                            'ContentLanguage': 'en', 'Expires': 'tomorrow', 'StorageClass': 'STANDARD_IA'}.items():
            self.assertEqual(value, obj[name])
        self.assertEqual({'custom': 'keep'}, obj['Metadata'])
        self.assertNotIn('ContentEncoding', obj)
        self.assertNotIn('WebsiteRedirectLocation', obj)

    def test_metadata_copy_preserves_acl_tags_and_unmanaged_properties(self):
        self.deploy_once()
        obj = self.client.objects['index.html']
        obj.update(ACL=deepcopy(PUBLIC_ACL), Tags=[{'Key': 'keep', 'Value': 'yes'}],
                   ContentType='wrong', ServerSideEncryption='AES256', ContentLanguage='ja')
        self.run_deploy()
        obj = self.client.objects['index.html']
        self.assertEqual(PUBLIC_ACL, obj['ACL'])
        self.assertEqual([{'Key': 'keep', 'Value': 'yes'}], obj['Tags'])
        self.assertEqual('AES256', obj['ServerSideEncryption'])
        self.assertEqual('ja', obj['ContentLanguage'])

    def test_cache_lifetimes_age_at_year_boundary_without_body_changes(self):
        self.file('2025/12/31/post.html')
        self.file('2026/01/01/post.html')
        self.file('404.html')
        self.file('talks/a.pdf')
        self.deploy_once()
        self.assertEqual('public, max-age=300', self.client.objects['2025/12/31/post.html']['CacheControl'])
        self.assertEqual('public, max-age=120', self.client.objects['404.html']['CacheControl'])
        self.assertEqual('public, max-age=86400', self.client.objects['talks/a.pdf']['CacheControl'])
        result = self.run_deploy(today=date(2026, 1, 3))
        self.assertEqual(2, result['metadata'])
        self.assertEqual(0, result['upload'])
        self.assertEqual('public, max-age=3600', self.client.objects['2025/12/31/post.html']['CacheControl'])

    def test_empty_redirect_target_changes_and_removal_are_metadata_changes(self):
        self.file('shortcut/index.html', b'')
        self.file('other.html')
        self.deploy_once({'shortcut': '/index.html'})
        result = self.run_deploy({'shortcut': '/other.html'})
        self.assertEqual(1, result['metadata'])
        self.assertEqual('/other.html', self.client.objects['shortcut/index.html']['WebsiteRedirectLocation'])
        self.client.calls.clear()
        self.run_deploy()
        self.assertEqual([('copy', 'shortcut/index.html')], self.client.writes())
        self.assertNotIn('WebsiteRedirectLocation', self.client.objects['shortcut/index.html'])

    def test_deleted_redirect_stub_is_removed_after_successful_writes(self):
        self.file('old.html', b'')
        self.deploy_once({'old.html': 'https://example.org/'})
        (self.root / 'old.html').unlink()
        self.file('new.html')
        self.run_deploy()
        self.assertEqual([('put', 'new.html'), ('delete', 'old.html')], self.client.writes())

    def test_gzip_object_is_replaced_with_plain_bytes_not_just_relabelled(self):
        import gzip
        self.client.seed('index.html', gzip.compress(b'page'), ContentEncoding='gzip')
        self.run_deploy()
        self.assertEqual([('put', 'index.html')], self.client.writes())
        self.assertEqual(b'page', self.client.objects['index.html']['Body'])
        self.assertNotIn('ContentEncoding', self.client.objects['index.html'])

    def test_stale_remembered_md5_does_not_hide_a_content_change(self):
        self.client.seed('index.html', b'xxxx')
        self.client.objects['index.html']['Metadata'] = {'s3cmd-attrs': 'md5:' + hashlib.md5(b'page').hexdigest()}
        self.run_deploy()
        self.assertEqual([('put', 'index.html')], self.client.writes())

    def test_multipart_and_kms_etags_compare_actual_content(self):
        for encryption, etag in [('AES256', 'opaque-2'), ('aws:kms', 'f' * 32), ('aws:kms:dsse', 'f' * 32)]:
            with self.subTest(encryption=encryption):
                self.client = FakeS3()
                self.deploy_once()
                self.client.objects['index.html'].update(ServerSideEncryption=encryption, ETag='"' + etag + '"')
                self.run_deploy()
                self.assertIn(('get', 'index.html'), self.client.calls)
                self.assertEqual([], self.client.writes())

    def test_dry_run_reports_all_changes_without_any_write(self):
        self.deploy_once()
        self.client.objects['index.html']['ContentType'] = 'wrong'
        self.client.seed('stale.html')
        self.file('new.html')
        result = self.run_deploy(dry_run=True)
        self.assertEqual({'upload': 1, 'metadata': 1, 'unchanged': 0, 'delete': 1}, result)
        self.assertEqual([], self.client.writes())

    def test_failed_upload_never_deletes_stale_objects(self):
        self.deploy_once()
        self.client.seed('stale.html')
        self.file('index.html', b'changed')
        self.client.fail_write = 'index.html'
        with self.assertRaisesRegex(RuntimeError, 'Injected'):
            self.run_deploy()
        self.assertIn('stale.html', self.client.objects)
        self.assertFalse(any(kind == 'delete' for kind, _ in self.client.calls))

    def test_concurrent_content_change_is_not_overwritten(self):
        self.deploy_once()
        self.file('index.html', b'changed')
        self.client.concurrent_change = True
        with self.assertRaisesRegex(RuntimeError, 'Precondition'):
            self.run_deploy()
        self.assertEqual(b'page', self.client.objects['index.html']['Body'])

    def test_concurrent_creation_is_not_overwritten(self):
        original_put = self.client.put_object
        def racing_put(**kwargs):
            self.client.seed(kwargs['Key'], b'created by someone else')
            return original_put(**kwargs)
        self.client.put_object = racing_put
        with self.assertRaisesRegex(RuntimeError, 'Already exists'):
            self.run_deploy()
        self.assertEqual(b'created by someone else', self.client.objects['index.html']['Body'])

    def test_metadata_repair_checks_for_concurrent_content_changes(self):
        self.deploy_once()
        self.client.objects['index.html']['ContentType'] = 'wrong/type'
        self.client.concurrent_change = True
        with self.assertRaisesRegex(RuntimeError, 'Precondition'):
            self.run_deploy()
        self.assertEqual('wrong/type', self.client.objects['index.html']['ContentType'])

    def test_failed_metadata_repair_does_not_delete_stale_objects(self):
        self.deploy_once()
        self.client.objects['index.html']['ContentType'] = 'wrong/type'
        self.client.seed('stale.html')
        self.client.fail_write = 'index.html'
        with self.assertRaisesRegex(RuntimeError, 'Injected'):
            self.run_deploy()
        self.assertIn('stale.html', self.client.objects)
        self.assertFalse(any(kind == 'delete' for kind, _ in self.client.calls))

    def test_head_errors_abort_before_any_writes_or_deletions(self):
        self.deploy_once()
        self.client.seed('stale.html')
        self.client.fail_head = True
        with self.assertRaisesRegex(RuntimeError, 'Access denied'):
            self.run_deploy()
        self.assertEqual([], self.client.writes())

    def test_prefix_scopes_inspection_writes_and_deletions(self):
        self.client.seed('outside.html')
        self.client.seed('test/stale.html')
        self.run_deploy(prefix='test/')
        self.assertEqual({'outside.html', 'test/index.html'}, set(self.client.objects))
        self.assertNotIn(('head', 'outside.html'), self.client.calls)

    def test_missing_build_gzipped_text_and_symlinks_fail_before_listing(self):
        import gzip
        for scenario in ('missing', 'empty', 'gzip', 'symlink'):
            with self.subTest(scenario=scenario):
                self.file('index.html')
                if scenario == 'missing':
                    (self.root / 'index.html').unlink()
                elif scenario == 'empty':
                    self.file('index.html', b'')
                elif scenario == 'gzip':
                    self.file('index.html', gzip.compress(b'page'))
                else:
                    (self.root / 'link').symlink_to(self.root / 'index.html')
                with self.assertRaises(ValueError):
                    self.run_deploy()
                self.assertEqual([], self.client.calls)

    def test_invalid_redirects_and_prefixes_fail_before_listing(self):
        self.file('shortcut/index.html', b'')
        for redirects, prefix in [({'shortcut': '/missing.html'}, ''),
                                  ({'shortcut': 'relative'}, ''),
                                  ({'shortcut': 'https://example.org/\r\nBad: x'}, ''),
                                  ({'shortcut': '/index.html', 'shortcut/index.html': '/index.html'}, ''),
                                  ({'../bad': '/index.html'}, ''), ({}, '../outside')]:
            with self.subTest(redirects=redirects, prefix=prefix):
                with self.assertRaises(ValueError):
                    self.run_deploy(redirects, prefix=prefix)
                self.assertEqual([], self.client.calls)


if __name__ == '__main__':
    unittest.main()
