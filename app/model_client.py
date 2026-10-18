"""Backend-only, authenticated access to the team's Qwen deployment."""
import asyncio
from pathlib import Path
import httpx
from .config import MODEL_URL,MODEL_NAME,MODEL_API_KEY_FILE
from .events import SYSTEM,Window

def headers():
    values={'ngrok-skip-browser-warning':'1'}
    if MODEL_API_KEY_FILE:
        key=Path(MODEL_API_KEY_FILE).read_text().strip()
        if len(key)<24:raise RuntimeError('Invalid model gateway credential')
        values['Authorization']='Bearer '+key
    return values

def client(timeout=180):
    return httpx.AsyncClient(base_url=MODEL_URL+'/',headers=headers(),timeout=timeout,
        trust_env=False,follow_redirects=False,
        limits=httpx.Limits(max_connections=4,max_keepalive_connections=4))

async def available():
    async with client(timeout=8) as connection:
        response=await connection.get('models');response.raise_for_status()
        if MODEL_NAME not in [x['id'] for x in response.json().get('data',[])]:raise RuntimeError('Configured model is unavailable')

async def ask(connection,images):
    content=[{'type':'text','text':
        'Annotate this ordered short window of the SAME video. Return visible physical events only. '
        'No detector, tracking, pose, or geometric cues are available. Infer cashier/client roles '
        'only from visible behavior and workstation layout; uncertain roles remain unknown. '
        'Reflections are not extra participants. Use EXACT supplied timestamps.'}]
    for f in images:
        content += [{'type':'text','text':f"Frame {f['timestamp_sec']:.3f}s; full frame"},
            {'type':'image_url','image_url':{'url':'data:image/jpeg;base64,'+f['image_base64']}}]
    payload={'model':MODEL_NAME,'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':content}],
        'temperature':0,'seed':17,'max_tokens':2300,'chat_template_kwargs':{'enable_thinking':False},
        'response_format':{'type':'json_schema','json_schema':{'name':'Window','strict':True,'schema':Window.model_json_schema()}}}
    for attempt in range(3):
        try:
            response=await connection.post('chat/completions',json=payload)
            if response.status_code in (429,502,503,504) and attempt<2:
                await asyncio.sleep(2*(attempt+1));continue
            response.raise_for_status();choice=response.json()['choices'][0]
            if choice['finish_reason']=='length':raise RuntimeError('Truncated event response')
            return Window.model_validate_json(choice['message']['content'])
        except (httpx.ConnectError,httpx.ConnectTimeout,httpx.ReadTimeout):
            if attempt==2:raise
            await asyncio.sleep(2*(attempt+1))
