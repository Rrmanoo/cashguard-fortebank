import os
import tempfile
import unittest
import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

tmp=tempfile.TemporaryDirectory()
os.environ['CASHGUARD_DATA']=tmp.name
os.environ['CASHGUARD_API_KEY']='test-key-at-least-24-characters-long'
from fastapi.testclient import TestClient
from app.main import app
from app import store

class ContractTests(unittest.TestCase):
    def setUp(self):
        self.ctx=TestClient(app);self.client=self.ctx.__enter__()
        self.headers={'X-API-Key':os.environ['CASHGUARD_API_KEY']}
    def tearDown(self):self.ctx.__exit__(None,None,None)
    def test_authentication(self):
        self.assertEqual(self.client.get('/api/v1/jobs/unknown').status_code,401)
        self.assertEqual(self.client.get('/api/v1/jobs/unknown',headers={'X-API-Key':'wrong'}).status_code,401)
    def test_unknown_job(self):
        self.assertEqual(self.client.get('/api/v1/jobs/unknown',headers=self.headers).status_code,404)
    def test_format(self):
        r=self.client.post('/api/v1/analyze',headers=self.headers,files={'file':('x.txt',b'bad')})
        self.assertEqual(r.status_code,415)
    def test_done_result(self):
        store.create('test-result')
        store.update('test-result',status='done',result={'verdict':'no_violation','violations':[]})
        body=self.client.get('/api/v1/jobs/test-result',headers=self.headers).json()
        self.assertEqual(body['status'],'done');self.assertEqual(body['violations'],[])
    def test_restart_marks_interrupted_failed(self):
        store.create('interrupted');store.init()
        self.assertEqual(store.get('interrupted')['status'],'failed')
    def test_rule_catalog(self):
        r=self.client.get('/api/v1/rules',headers=self.headers)
        self.assertEqual(r.status_code,200)
        self.assertTrue(all(x['clause'] for x in r.json()['rules']))
    def test_ui(self):
        self.assertEqual(self.client.get('/').status_code,200)
    def test_oversized_upload_rejected_before_parsing(self):
        r=self.client.post('/api/v1/analyze',headers={**self.headers,'Content-Length':str(140*1024*1024)},content=b'x')
        self.assertEqual(r.status_code,413)
    def test_unauthorized_upload_rejected_before_parsing(self):
        self.assertEqual(self.client.post('/api/v1/analyze',content=b'invalid multipart').status_code,401)

class DeadlineTests(unittest.IsolatedAsyncioTestCase):
    async def test_worker_deadline_is_failure_and_removes_upload(self):
        from app import main
        store.init();store.create('deadline-test')
        path=Path(tmp.name)/'deadline.mov';path.write_bytes(b'test')
        real_spawn=asyncio.create_subprocess_exec
        async def sleeping_worker(*args,**kwargs):
            return await real_spawn(sys.executable,'-c','import time;time.sleep(30)',start_new_session=True)
        with patch.object(main,'JOB_TIMEOUT',.1),patch.object(main.asyncio,'create_subprocess_exec',sleeping_worker):
            await main.run('deadline-test',path)
        self.assertEqual(store.get('deadline-test')['status'],'failed')
        self.assertFalse(path.exists())

if __name__=='__main__':unittest.main()
