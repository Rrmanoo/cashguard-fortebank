"""CPU sampling and evidence only; no learned perception models."""
import base64
from pathlib import Path
import av,cv2
FPS=2.5

def decode(path,folder,max_edge=None):
    samples=[];next_t=0.;origin=None
    with av.open(str(path)) as container:
        stream=container.streams.video[0]
        stream.thread_type='AUTO';stream.codec_context.thread_count=2
        for frame in container.decode(stream):
            if frame.pts is None:continue
            raw=float(frame.pts*frame.time_base)
            if origin is None:origin=raw
            timestamp=raw-origin
            if timestamp+1e-5<next_t:continue
            image=frame.to_ndarray(format='bgr24');h,w=image.shape[:2]
            if max_edge and max(h,w)>max_edge:
                scale=max_edge/max(h,w)
                image=cv2.resize(image,(round(w*scale),round(h*scale)),interpolation=cv2.INTER_AREA)
            destination=Path(folder)/f'{len(samples):05d}.jpg'
            if not cv2.imwrite(str(destination),image,[cv2.IMWRITE_JPEG_QUALITY,95]):raise RuntimeError('Frame write failed')
            samples.append({'timestamp_sec':round(timestamp,3),'path':destination})
            next_t+=1/FPS
    if not samples:raise ValueError('No decodable video frames')
    return samples

def encoded(image,t,label='full frame'):
    ok,jpg=cv2.imencode('.jpg',image,[cv2.IMWRITE_JPEG_QUALITY,90])
    if not ok:raise RuntimeError('JPEG encoding failed')
    return {'timestamp_sec':t,'label':label,'image_base64':base64.b64encode(jpg).decode()}

def evidence(sample):
    image=cv2.imread(str(sample['path']))
    if image is None:raise ValueError('Evidence frame is unavailable')
    result=encoded(image,sample['timestamp_sec']);result.pop('label');return result
