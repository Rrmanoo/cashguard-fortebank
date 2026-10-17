"""Local decoding only. No face recognition, audio, or external media URLs."""
import base64
import json
import math
import subprocess
from pathlib import Path
import cv2

def probe(path: Path):
    p = subprocess.run(['ffprobe', '-v', 'error', '-protocol_whitelist', 'file,pipe', '-show_streams', '-show_format',
                        '-of', 'json', str(path)], capture_output=True, timeout=20, check=True)
    info = json.loads(p.stdout)
    if 'mov' not in info.get('format', {}).get('format_name', '').split(','):
        raise ValueError('File content is not a MOV container')
    stream = next((s for s in info['streams'] if s['codec_type'] == 'video'), None)
    if not stream:
        raise ValueError('No video stream')
    duration = float(info['format'].get('duration', stream.get('duration', 0)))
    if not math.isfinite(duration) or not 0 < duration <= 180:
        raise ValueError('Video must be between 0 and 180 seconds')
    if stream['width'] * stream['height'] > 4096 * 2160:
        raise ValueError('Maximum resolution is 4096 × 2160')
    return {'duration': duration, 'width': stream['width'], 'height': stream['height']}

def frames(path: Path, targets: list[float], edge=768):
    """Decode sequentially and use presentation timestamps, not nominal frame rate."""
    cap = cv2.VideoCapture(str(path))
    targets = sorted(set(max(0., float(t)) for t in targets))
    result = []
    index = 0
    try:
        while index < len(targets):
            ok, frame = cap.read()
            if not ok:
                break
            timestamp = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
            if not math.isfinite(timestamp):
                raise ValueError('Invalid video timestamp')
            if timestamp + 0.0001 < targets[index]:
                continue
            h, w = frame.shape[:2]
            if max(h, w) > edge:
                frame = cv2.resize(frame, (round(w * edge / max(h,w)), round(h * edge / max(h,w))))
            ok, jpg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 88])
            if not ok:
                raise ValueError('Frame encoding failed')
            result.append({'timestamp_sec': round(timestamp, 3),
                           'image_base64': base64.b64encode(jpg).decode()})
            while index < len(targets) and targets[index] <= timestamp + 0.0001:
                index += 1
    finally:
        cap.release()
    if not result:
        raise ValueError('No decodable frames')
    return result

def uniform(start, end, count):
    return [start + (end-start)*i/max(count-1,1) for i in range(count)]
