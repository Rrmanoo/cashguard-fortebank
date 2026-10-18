import unittest
from pydantic import ValidationError
from app.contracts import JobStatus
from app.main import app
class PublicSchemaTests(unittest.TestCase):
    def test_done_without_verdict_is_invalid(self):
        with self.assertRaises(ValidationError):JobStatus(job_id='x',status='done')
    def test_violation_requires_evidence(self):
        with self.assertRaises(ValidationError):JobStatus(job_id='x',status='done',verdict='violation',violations=[dict(type='test',timecode_sec=1,description='test',evidence_frames=[])])
    def test_openapi_exposes_jury_contract(self):
        schema=app.openapi();responses=schema['paths']['/api/v1/jobs/{job_id}']['get']['responses'];self.assertIn('JobStatus',str(responses));self.assertIn('X-API-Key',str(schema['components']['securitySchemes']))
