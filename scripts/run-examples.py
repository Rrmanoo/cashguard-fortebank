"""Analyze every supplied development video through the actual private API.

Run on the GPU server. Only aggregate progress is printed; all content stays there.
"""
import asyncio
import fcntl
import hashlib
import json
import os
import statistics
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

BASE = Path(os.getenv('CASHGUARD_BASE', str(Path(__file__).resolve().parents[1])))
ROOT = BASE / 'examples'
URL = 'http://127.0.0.1:9017'


def write_json(path, data):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    temp.replace(path)


async def main():
    os.umask(0o077)
    ROOT.mkdir(exist_ok=True)
    for folder in ('results', 'previews'):
        (ROOT / folder).mkdir(exist_ok=True)
    labels = json.loads((BASE / 'data/labels.json').read_text())
    saved = ROOT / 'manifest.json'
    if saved.exists():
        data = json.loads(saved.read_text())
    else:
        data = {'dataset': 'provided_development_set', 'status': 'processing',
                'started_at': datetime.now(timezone.utc).isoformat(), 'items': []}
        for row in labels:
            name = row['filename']
            data['items'].append({'id': hashlib.sha256(name.encode()).hexdigest()[:16],
                'filename': name, 'status': 'queued', 'expected_violation': row['violation'],
                'expected_timestamp_sec': row['timestamp_sec'], 'video_ready': False})
    data['status'] = 'processing'
    write_json(saved, data)
    headers = {'X-API-Key': (BASE / 'api.key').read_text().strip()}
    async with httpx.AsyncClient(headers=headers, timeout=60, trust_env=False) as client:
        for item in data['items']:
            if item['status'] == 'done':
                continue
            path = BASE / 'data/videos' / item['filename']
            item['status'] = 'processing'
            item.pop('error', None)
            write_json(saved, data)
            start = time.monotonic()
            try:
                # If a previous batch process stopped, finish its already admitted job.
                job = item.get('job_id')
                result = None
                if job:
                    prior = await client.get(URL + '/api/v1/jobs/' + job)
                    if prior.status_code == 200:
                        result = prior.json()
                        if result['status'] == 'failed':
                            result = None
                if result is None:
                    while True:
                        with path.open('rb') as video:
                            response = await client.post(URL + '/api/v1/analyze',
                                files={'file': (path.name, video, 'video/quicktime')})
                        if response.status_code != 429:
                            break
                        if time.monotonic() - start > 600:
                            raise RuntimeError('Service remained busy for ten minutes')
                        await asyncio.sleep(3)
                    response.raise_for_status()
                    job = response.json()['job_id']
                    item['job_id'] = job
                    item['submitted_at'] = time.time()
                    write_json(saved, data)
                while result is None or result['status'] == 'processing':
                    await asyncio.sleep(2)
                    response = await client.get(URL + '/api/v1/jobs/' + job)
                    response.raise_for_status()
                    result = response.json()
                    if time.time() - item.get('submitted_at', time.time()) > 310:
                        raise RuntimeError('Processing exceeded five minutes')
                elapsed = round(time.monotonic() - start, 2)
                if result['status'] != 'done':
                    raise RuntimeError(result.get('error', 'Analysis failed'))
                write_json(ROOT / 'results' / (item['id'] + '.json'), result)
                item.update(status='done', verdict=result['verdict'],
                    violation_count=len(result.get('violations', [])), elapsed_sec=elapsed,
                    completed_at=datetime.now(timezone.utc).isoformat())
                item['matches_reference'] = (result['verdict'] == 'violation') == item['expected_violation']
            except Exception as exc:
                item.update(status='failed', error=str(exc)[:250], elapsed_sec=round(time.monotonic() - start, 2))
            write_json(saved, data)
            # Browser-compatible silent preview; never sent to an external service.
            preview = ROOT / 'previews' / (item['id'] + '.mp4')
            if not preview.exists():
                temp = preview.with_suffix('.tmp.mp4')
                try:
                    subprocess.run(['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-y',
                        '-i', str(path), '-map', '0:v:0', '-an', '-vf',
                        'scale=1280:720:force_original_aspect_ratio=decrease:force_divisible_by=2',
                        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '25', '-threads', '2',
                        '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(temp)],
                        check=True, timeout=180, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    temp.replace(preview)
                except Exception:
                    temp.unlink(missing_ok=True)
            item['video_ready'] = preview.exists()
            write_json(saved, data)
            print(json.dumps({'finished': sum(x['status'] in ('done', 'failed') for x in data['items']),
                'total': len(data['items']), 'status': item['status'], 'elapsed_sec': item['elapsed_sec']}), flush=True)
    done = [x for x in data['items'] if x['status'] == 'done']
    data['metrics'] = {
        'total': len(data['items']), 'completed': len(done),
        'failed': sum(x['status'] == 'failed' for x in data['items']),
        'tp': sum(x['expected_violation'] and x['verdict'] == 'violation' for x in done),
        'tn': sum(not x['expected_violation'] and x['verdict'] == 'no_violation' for x in done),
        'fp': sum(not x['expected_violation'] and x['verdict'] == 'violation' for x in done),
        'fn': sum(x['expected_violation'] and x['verdict'] == 'no_violation' for x in done),
        'max_latency_sec': max((x['elapsed_sec'] for x in done), default=0),
        'median_latency_sec': statistics.median([x['elapsed_sec'] for x in done]) if done else None}
    data['status'] = 'done' if len(done) == len(data['items']) else 'completed_with_errors'
    data['finished_at'] = datetime.now(timezone.utc).isoformat()
    write_json(saved, data)
    print(json.dumps(data['metrics']), flush=True)


if __name__ == '__main__':
    ROOT.mkdir(exist_ok=True)
    with (ROOT / '.batch.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        asyncio.run(main())
