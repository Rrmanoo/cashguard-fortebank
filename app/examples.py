"""Private, persistent development examples, independent of expiring upload jobs."""
import json
import os
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

EXAMPLES = Path(os.getenv('CASHGUARD_EXAMPLES', str(Path(__file__).resolve().parents[1]/'examples')))
router = APIRouter()


def manifest():
    path = EXAMPLES / 'manifest.json'
    if not path.exists():
        return {'items': [], 'status': 'not_started'}
    return json.loads(path.read_text())


def example(ident):
    if not re.fullmatch(r'[a-f0-9]{16}', ident):
        raise HTTPException(404, 'Example not found')
    item = next((x for x in manifest()['items'] if x['id'] == ident), None)
    if item is None:
        raise HTTPException(404, 'Example not found')
    return item


@router.get('/examples')
async def listing():
    return manifest()


@router.get('/examples/{ident}')
async def detail(ident: str):
    item = example(ident)
    path = EXAMPLES / 'results' / (ident + '.json')
    if item['status'] != 'done' or not path.exists():
        raise HTTPException(409, 'Example result is not ready')
    return {'example': item, 'result': json.loads(path.read_text())}


@router.get('/examples/{ident}/video')
async def video(ident: str):
    item = example(ident)
    path = EXAMPLES / 'previews' / (ident + '.mp4')
    if not item.get('video_ready') or not path.exists():
        raise HTTPException(404, 'Video preview is not ready')
    return FileResponse(path, media_type='video/mp4', headers={'Cache-Control': 'private, max-age=3600'})
