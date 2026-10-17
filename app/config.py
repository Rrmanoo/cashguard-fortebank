import os
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.getenv('CASHGUARD_DATA', str(ROOT / 'runtime')))
MODEL_URL = os.getenv('MODEL_URL', 'http://127.0.0.1:9016/v1')
if urlparse(MODEL_URL).hostname not in ('127.0.0.1', 'localhost', '::1'):
    raise RuntimeError('Model endpoint must be loopback: cloud inference is prohibited')
MODEL_NAME = os.getenv('MODEL_NAME', 'cashier-vlm')
MAX_BYTES = 128 * 1024 * 1024
MAX_DURATION = 180
JOB_TIMEOUT = 270
RETENTION_HOURS = int(os.getenv('RETENTION_HOURS', '24'))

