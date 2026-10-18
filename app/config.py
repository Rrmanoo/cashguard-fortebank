import os
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.getenv('CASHGUARD_DATA', str(ROOT / 'runtime')))
MODEL_URL = os.getenv('MODEL_URL', 'http://127.0.0.1:9003/v1').rstrip('/')
endpoint = urlparse(MODEL_URL)
local = endpoint.hostname in ('127.0.0.1', 'localhost', '::1')
allowed = {h.strip() for h in os.getenv('MODEL_ALLOWED_HOSTS', '').split(',') if h.strip()}
if endpoint.username or endpoint.password or endpoint.query or endpoint.fragment:
    raise RuntimeError('Model URL must not contain credentials, a query, or a fragment')
if endpoint.path != '/v1' or endpoint.scheme not in ('http', 'https'):
    raise RuntimeError('Configure an OpenAI-compatible /v1 model endpoint')
private_http = os.getenv('MODEL_ALLOW_PRIVATE_HTTP', '0') == '1' and endpoint.scheme == 'http' and endpoint.hostname in allowed
if not local and not private_http and (endpoint.scheme != 'https' or endpoint.hostname not in allowed):
    raise RuntimeError('Remote model endpoint requires HTTPS and an explicit hostname allowlist')
MODEL_NAME = os.getenv('MODEL_NAME', 'qwen')
MODEL_API_KEY_FILE = os.getenv('MODEL_API_KEY_FILE', '')
if not local and not MODEL_API_KEY_FILE:
    raise RuntimeError('Remote model endpoint requires a private API key file')
FRAME_MAX_EDGE = int(os.getenv('FRAME_MAX_EDGE', '1024'))
if not 512 <= FRAME_MAX_EDGE <= 2048:
    raise RuntimeError('FRAME_MAX_EDGE must be 512..2048')
MAX_BYTES = 128 * 1024 * 1024
MAX_DURATION = 180
JOB_TIMEOUT = 270
RETENTION_HOURS = int(os.getenv('RETENTION_HOURS', '24'))

