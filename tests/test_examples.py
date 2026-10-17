import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('CASHGUARD_API_KEY', 'local-test-key-at-least-24-characters')
from fastapi.testclient import TestClient
from app import examples, main, store


class ExampleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.patch = patch.object(examples, 'EXAMPLES', self.root)
        self.patch.start()
        self.ident = '0123456789abcdef'
        self.item = {'id': self.ident, 'filename': 'sample.mov', 'status': 'done', 'video_ready': True}
        (self.root / 'manifest.json').write_text(json.dumps({'items': [self.item]}))
        (self.root / 'results').mkdir()
        (self.root / 'results' / (self.ident + '.json')).write_text(json.dumps(
            {'status': 'done', 'verdict': 'no_violation', 'violations': []}))
        (self.root / 'previews').mkdir()
        (self.root / 'previews' / (self.ident + '.mp4')).write_bytes(b'private-video')
        self.ctx = TestClient(main.app)
        self.client = self.ctx.__enter__()
        self.headers = {'X-API-Key': main.api_key}

    def tearDown(self):
        self.ctx.__exit__(None, None, None)
        self.patch.stop()
        self.tmp.cleanup()

    def test_all_example_routes_require_key(self):
        for path in ['/examples', '/examples/' + self.ident, '/examples/' + self.ident + '/video']:
            self.assertEqual(self.client.get('/api/v1' + path).status_code, 401)

    def test_list_does_not_include_full_results(self):
        body = self.client.get('/api/v1/examples', headers=self.headers).json()
        self.assertEqual(len(body['items']), 1)
        self.assertNotIn('result', body['items'][0])

    def test_result_survives_job_expiration(self):
        store.create('gallery-expired-job')
        store.update('gallery-expired-job', status='done', result={'verdict': 'no_violation', 'violations': []})
        store.expire(time.time() + 1)
        self.assertIsNone(store.get('gallery-expired-job'))
        body = self.client.get('/api/v1/examples/' + self.ident, headers=self.headers).json()
        self.assertEqual(body['result']['verdict'], 'no_violation')

    def test_video_is_private_and_supports_ranges(self):
        response = self.client.get('/api/v1/examples/' + self.ident + '/video',
            headers={**self.headers, 'Range': 'bytes=0-6'})
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response.content, b'private')
        self.assertIn('private', response.headers['cache-control'])

    def test_unknown_example_rejected(self):
        self.assertEqual(self.client.get('/api/v1/examples/' + 'a' * 16, headers=self.headers).status_code, 404)
        self.assertEqual(self.client.get('/api/v1/examples/manifest.json', headers=self.headers).status_code, 404)

    def test_queued_result_is_not_fabricated(self):
        self.item['status'] = 'queued'
        (self.root / 'manifest.json').write_text(json.dumps({'items': [self.item]}))
        self.assertEqual(self.client.get('/api/v1/examples/' + self.ident, headers=self.headers).status_code, 409)

    def test_empty_gallery(self):
        (self.root / 'manifest.json').unlink()
        response = self.client.get('/api/v1/examples', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['items'], [])

    def test_session_survives_page_reload_without_exposing_key(self):
        response = self.client.post('/api/v1/session', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        cookie = response.headers['set-cookie']
        self.assertIn('HttpOnly', cookie)
        self.assertIn('SameSite=strict', cookie)
        self.assertNotIn(main.api_key, cookie)
        self.assertEqual(self.client.get('/api/v1/examples').status_code, 200)
        self.assertEqual(self.client.get('/').status_code, 200)
        self.assertEqual(self.client.get('/api/v1/examples/' + self.ident + '/video').status_code, 200)
        # Cookie authentication must pass the pre-upload middleware too.
        self.assertEqual(self.client.post('/api/v1/analyze', files={'file': ('x.txt', b'bad')}).status_code, 415)

    def test_forged_and_expired_sessions_rejected(self):
        self.client.cookies.set('cashguard_session', '9999999999.forged')
        self.assertEqual(self.client.get('/api/v1/examples').status_code, 401)
        self.client.cookies.set('cashguard_session', '1.expired')
        self.assertEqual(self.client.get('/api/v1/examples').status_code, 401)

    def test_wrong_explicit_key_does_not_fall_back_to_session(self):
        self.client.post('/api/v1/session', headers=self.headers)
        self.assertEqual(self.client.get('/api/v1/examples', headers={'X-API-Key': 'wrong'}).status_code, 401)

    def test_cookie_does_not_authorize_cross_origin_posts(self):
        self.client.post('/api/v1/session', headers=self.headers)
        response = self.client.post('/api/v1/session', headers={'Origin': 'http://unrelated.example'})
        self.assertEqual(response.status_code, 401)
