import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import httpx
from app import model_client

class ModelClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_schema_and_auth_survive_remote_transport(self):
        calls=[]
        def handle(request):
            calls.append(request);payload=json.loads(request.content)
            self.assertEqual(payload['model'],'qwen')
            self.assertEqual(request.headers['Authorization'],'Bearer '+'a'*32)
            self.assertFalse(payload['chat_template_kwargs']['enable_thinking'])
            self.assertIn('image_url',str(payload['messages']))
            return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'facts':[],'desk_visible':'yes','doorway_visible':'unknown','observed':'Кассир за столом.'})}}]})
        async with httpx.AsyncClient(base_url='https://model.example/v1/',headers={'Authorization':'Bearer '+'a'*32},transport=httpx.MockTransport(handle)) as client:
            result=await model_client.ask(client,[{'timestamp_sec':0.,'image_base64':'YWJj'}])
        self.assertEqual(len(calls),1);self.assertEqual(result.facts,[])
    async def test_truncated_response_is_failure(self):
        async with httpx.AsyncClient(base_url='https://model.example/v1/',transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'choices':[{'finish_reason':'length'}]}))) as client:
            with self.assertRaises(RuntimeError):await model_client.ask(client,[])
    async def test_redirect_does_not_forward_credentials(self):
        calls=[]
        def handle(request):
            calls.append(request)
            return httpx.Response(307,headers={'Location':'https://untrusted.example/steal'})
        async with httpx.AsyncClient(base_url='https://model.example/v1/',follow_redirects=False,transport=httpx.MockTransport(handle)) as client:
            with self.assertRaises(httpx.HTTPStatusError):await model_client.ask(client,[])
        self.assertEqual(len(calls),1)
