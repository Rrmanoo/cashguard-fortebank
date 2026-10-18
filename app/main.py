import asyncio
from contextlib import asynccontextmanager
import hmac
import hashlib
import json
import os
import shutil
import signal
import sys
import time
import uuid
from pathlib import Path
import httpx
from fastapi import FastAPI, UploadFile, File, Header, HTTPException, Depends, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import APIKeyHeader
from . import store
from .config import DATA, ROOT, MAX_BYTES, JOB_TIMEOUT, RETENTION_HOURS
from . import model_client
from .examples import router as examples_router

active=False
tasks=set()
api_key=''

async def cleanup():
    while True:
        for job in store.expire(time.time()-RETENTION_HOURS*3600):
            shutil.rmtree(DATA/job,ignore_errors=True)
        await asyncio.sleep(300)

@asynccontextmanager
async def lifespan(app):
    global api_key
    keyfile=os.getenv('CASHGUARD_API_KEY_FILE')
    api_key=Path(keyfile).read_text().strip() if keyfile else os.getenv('CASHGUARD_API_KEY','')
    if len(api_key)<24: raise RuntimeError('Configure a strong API key of at least 24 characters')
    store.init()
    for orphan in DATA.glob('*/input.mov'):
        orphan.unlink(missing_ok=True)
    for orphan in list(DATA.glob('*/frames-*')) + list(DATA.glob('final-*')):
        if orphan.is_dir(): shutil.rmtree(orphan,ignore_errors=True)
    cleaner=asyncio.create_task(cleanup())
    yield
    cleaner.cancel()
    for t in list(tasks): t.cancel()
    await asyncio.gather(cleaner,*list(tasks),return_exceptions=True)

app=FastAPI(title='CashGuard',version='1.0.0',lifespan=lifespan)

class UploadLimit:
    def __init__(self,app): self.app=app
    async def __call__(self,scope,receive,send):
        if scope['type']!='http' or scope.get('method')!='POST':
            return await self.app(scope,receive,send)
        headers=dict(scope.get('headers',[]))
        if scope.get('path','').startswith('/api/v1/') and not authenticated(Request(scope)):
            await send({'type':'http.response.start','status':401,'headers':[(b'content-type',b'application/json')]})
            await send({'type':'http.response.body','body':b'{"detail":"Invalid API key"}'})
            return
        try: length=int(headers.get(b'content-length',b'0'))
        except ValueError: length=0
        if length>MAX_BYTES+1024*1024:
            await send({'type':'http.response.start','status':413,'headers':[(b'content-type',b'application/json')]})
            await send({'type':'http.response.body','body':b'{"detail":"Maximum upload size is 128 MB"}'})
            return
        size=0
        async def bounded():
            nonlocal size
            msg=await receive()
            size+=len(msg.get('body',b''))
            if size>MAX_BYTES+1024*1024:
                raise HTTPException(413,'Maximum upload size is 128 MB')
            return msg
        await self.app(scope,bounded,send)

app.add_middleware(UploadLimit)

def authenticated(request: Request):
    if not api_key:
        return False
    supplied = request.headers.get('x-api-key', '')
    if supplied:
        return hmac.compare_digest(supplied.encode(), api_key.encode())
    origin = request.headers.get('origin')
    if request.method not in ('GET', 'HEAD') and origin and origin != request.url.scheme + '://' + request.url.netloc:
        return False
    token = request.cookies.get('cashguard_session', '')
    try:
        expires, signature = token.split('.', 1)
        if not time.time() < int(expires) <= time.time() + 12 * 3600 + 60:
            return False
        expected = hmac.new(api_key.encode(), ('cashguard-session:' + expires).encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected)
    except (ValueError, TypeError):
        return False

api_key_header=APIKeyHeader(name='X-API-Key',auto_error=False)

def auth(request: Request, supplied=Depends(api_key_header)):
    if not authenticated(request):
        raise HTTPException(401,'Invalid API key')

app.include_router(examples_router, prefix='/api/v1', dependencies=[Depends(auth)])

@app.post('/api/v1/session', dependencies=[Depends(auth)])
async def session(request: Request):
    expires = str(int(time.time()) + 12 * 3600)
    signature = hmac.new(api_key.encode(), ('cashguard-session:' + expires).encode(), hashlib.sha256).hexdigest()
    response = JSONResponse({'authenticated': True})
    response.set_cookie('cashguard_session', expires + '.' + signature, max_age=12 * 3600,
                        httponly=True, samesite='strict', secure=request.url.scheme == 'https')
    return response

@app.get('/healthz')
async def health():
    try:
        await model_client.available()
    except Exception: raise HTTPException(503,'Model unavailable')
    return {'status':'ok','busy':active,'pipeline':'qwen_fixed_facts_final','architecture_version':'2026.10.18-final.1'}

async def run(job,path):
    global active
    process=None
    try:
        process=await asyncio.create_subprocess_exec(sys.executable,'-m','app.worker',job,str(path),
                    cwd=str(ROOT),start_new_session=True,stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL)
        await asyncio.wait_for(process.wait(),JOB_TIMEOUT)
        if store.get(job)['status']=='processing':
            store.update(job,status='failed',error='Worker terminated unexpectedly')
    except (asyncio.TimeoutError,asyncio.CancelledError):
        if process and process.returncode is None:
            os.killpg(process.pid,signal.SIGKILL)
            await process.wait()
        store.update(job,status='failed',error='Processing deadline exceeded or service stopped')
    except Exception as exc:
        store.update(job,status='failed',error='Worker failure: '+type(exc).__name__)
    finally:
        # Evidence JPEGs persist in the result until expiry. Original uploads are removed immediately.
        path.unlink(missing_ok=True)
        for scratch in list(path.parent.glob('frames-*')) + list(DATA.glob('final-*')):
            if scratch.is_dir(): shutil.rmtree(scratch,ignore_errors=True)
        active=False

@app.post('/api/v1/analyze',dependencies=[Depends(auth)],status_code=202)
async def submit(file:UploadFile=File(...)):
    global active
    if not (file.filename or '').lower().endswith('.mov'):
        raise HTTPException(415,'A .mov video is required')
    if active: raise HTTPException(429,'Analysis worker is busy; retry shortly',headers={'Retry-After':'10'})
    await health()
    # A single application worker owns admission. No unbounded queue can consume the five-minute SLA.
    if active: raise HTTPException(429,'Analysis worker is busy; retry shortly',headers={'Retry-After':'10'})
    active=True
    job=uuid.uuid4().hex
    folder=DATA/job
    folder.mkdir(parents=True,mode=0o700)
    path=folder/'input.mov'
    try:
        total=0
        with path.open('wb') as out:
            while chunk:=await file.read(1024*1024):
                total+=len(chunk)
                if total>MAX_BYTES: raise HTTPException(413,'Maximum upload size is 128 MB')
                out.write(chunk)
        if total==0: raise HTTPException(400,'Empty video')
        store.create(job)
        task=asyncio.create_task(run(job,path));tasks.add(task);task.add_done_callback(tasks.discard)
        return {'job_id':job,'status':'processing'}
    except BaseException:
        active=False
        shutil.rmtree(folder,ignore_errors=True)
        raise
    finally: await file.close()

@app.get('/api/v1/jobs/{job_id}',dependencies=[Depends(auth)])
async def status(job_id:str):
    result=store.get(job_id)
    if result is None: raise HTTPException(404,'Job not found or expired')
    return result

@app.get('/api/v1/rules',dependencies=[Depends(auth)])
async def rules(): return json.loads((ROOT/'rules/catalog.json').read_text())

@app.get('/')
async def index(): return FileResponse(ROOT/'app/static/index.html')

@app.get('/examples', include_in_schema=False)
async def examples_page(): return FileResponse(ROOT/'app/static/index.html')

app.mount('/static',StaticFiles(directory=ROOT/'app/static'),name='static')
