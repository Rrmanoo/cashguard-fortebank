"""Private on-node perception. Never sends media or descriptions outside loopback."""
import base64, os, json
from pathlib import Path
from types import SimpleNamespace
import av, cv2, numpy as np, torch
from PIL import Image
from transformers import RTDetrV2ForObjectDetection, RTDetrImageProcessor, AutoProcessor, AutoModelForZeroShotObjectDetection
from .tracker.byte_tracker import BYTETracker

MODELS=Path(os.getenv('CASHGUARD_MODELS',str(Path(__file__).resolve().parents[1]/'models')))
FPS=2.5

def decode(path,folder):
    sampled=[]; next_t=0.; origin=None
    with av.open(str(path)) as container:
        stream=container.streams.video[0];stream.thread_type='AUTO'
        for frame in container.decode(stream):
            if frame.pts is None:continue
            raw=float(frame.pts*frame.time_base)
            if origin is None:origin=raw
            t=raw-origin
            if t+1e-5<next_t:continue
            dst=folder/f'{len(sampled):05d}.jpg'
            if not cv2.imwrite(str(dst),frame.to_ndarray(format='bgr24'),[cv2.IMWRITE_JPEG_QUALITY,95]):raise RuntimeError('Decode write failed')
            sampled.append({'timestamp_sec':round(t,3),'path':dst})
            next_t+=1/FPS
    if not sampled:raise ValueError('No frames')
    return sampled

def encoded(image,t,label='full frame'):
    ok,jpg=cv2.imencode('.jpg',image,[cv2.IMWRITE_JPEG_QUALITY,90])
    if not ok:raise RuntimeError('Encode failed')
    return {'timestamp_sec':t,'label':label,'image_base64':base64.b64encode(jpg).decode()}

def crop(image,box):
    h,w=image.shape[:2];x1,y1,x2,y2=box
    x1,y1,x2,y2=int(max(0,x1)*w),int(max(0,y1)*h),int(min(1,x2)*w),int(min(1,y2)*h)
    if x2<=x1 or y2<=y1:return None
    roi=image[y1:y2,x1:x2]
    return cv2.resize(roi,None,fx=2,fy=2,interpolation=cv2.INTER_CUBIC)

class Perception:
    def __init__(self):
        # CUDA_VISIBLE_DEVICES is set to physical GPU1 by the launcher. Refuse default GPU0.
        if os.getenv('CUDA_VISIBLE_DEVICES')!='1':raise RuntimeError('GPU1 isolation required')
        torch.set_num_threads(4)
        self.processor=RTDetrImageProcessor.from_pretrained(MODELS/'rtdetr-v2',local_files_only=True)
        self.detector=RTDetrV2ForObjectDetection.from_pretrained(MODELS/'rtdetr-v2',local_files_only=True).to('cuda').eval()
        self.gp=AutoProcessor.from_pretrained(MODELS/'grounding-dino',local_files_only=True)
        self.gd=AutoModelForZeroShotObjectDetection.from_pretrained(MODELS/'grounding-dino',local_files_only=True).to('cuda').eval()
        from rtmlib import RTMPose
        self.pose=RTMPose(str(MODELS/'rtmpose-m-wholebody.onnx'),model_input_size=(192,256),backend='onnxruntime',device='cpu')
        self.tracker=BYTETracker(SimpleNamespace(track_thresh=.35,track_buffer=60,match_thresh=.8,mot20=False),frame_rate=FPS)
        self.history={}

    @torch.inference_mode()
    def objects(self,image,prompt):
        inputs=self.gp(images=Image.fromarray(cv2.cvtColor(image,cv2.COLOR_BGR2RGB)),text=prompt,return_tensors='pt').to('cuda')
        out=self.gd(**inputs)
        result=self.gp.post_process_grounded_object_detection(out,inputs.input_ids,threshold=.25,text_threshold=.25,target_sizes=[image.shape[:2]])[0]
        labels=result.get('text_labels',result.get('labels',[]))
        return [{'label':str(l),'score':round(float(s),3),'box':b.tolist()} for l,s,b in zip(labels,result['scores'].cpu(),result['boxes'].cpu())]

    def regions(self,samples):
        # Calibrate independently for each clip; no fixed-camera assumption.
        candidates={'desk':[],'safe':[],'door':[]}
        for f in [samples[0],samples[len(samples)//2],samples[-1]]:
            im=cv2.imread(str(f['path']));h,w=im.shape[:2]
            for o in self.objects(im,'desk. safe. door.'):
                key=next((k for k in candidates if k in o['label']),None)
                if key:
                    b=np.array(o['box'])/np.array([w,h,w,h])
                    if 0.002<(b[2]-b[0])*(b[3]-b[1])<.9:candidates[key].append((o['score'],b.tolist()))
        return {k:max(v,key=lambda x:x[0])[1] for k,v in candidates.items() if v}

    @torch.inference_mode()
    def people(self,samples,zones):
        for f in samples:
            image=cv2.imread(str(f['path']));h,w=image.shape[:2]
            inputs=self.processor(images=Image.fromarray(cv2.cvtColor(image,cv2.COLOR_BGR2RGB)),return_tensors='pt').to('cuda')
            result=self.processor.post_process_object_detection(self.detector(**inputs),target_sizes=torch.tensor([[h,w]],device='cuda'),threshold=.1)[0]
            mask=result['labels']==0
            boxes=result['boxes'][mask].cpu().numpy();scores=result['scores'][mask].cpu().numpy()
            det=np.column_stack([boxes,scores]).astype(np.float64)
            tracks=self.tracker.update(det,(h,w),(h,w));f['tracks']=[]
            for track in tracks:
                box=track.tlbr.tolist();center=[(box[0]+box[2])/2/w,(box[1]+box[3])/2/h]
                row={'id':track.track_id,'box':[round(v,1) for v in box],'center':center}
                self.history.setdefault(track.track_id,[]).append((f['timestamp_sec'],center))
                f['tracks'].append(row)
        desk=zones.get('desk');door=zones.get('door')
        def inside(p,b,margin=0):return b and b[0]-margin<=p[0]<=b[2]+margin and b[1]-margin<=p[1]<=b[3]+margin
        dwell={i:sum(bool(inside(p,desk,.12)) for _,p in hist)/FPS for i,hist in self.history.items()}
        ordered=sorted(dwell,key=dwell.get,reverse=True)
        cashier=ordered[0] if ordered and dwell[ordered[0]]>=3 and (len(ordered)==1 or dwell[ordered[0]]>1.25*dwell[ordered[1]]) else None
        for f in samples:
            for tr in f['tracks']:
                history=self.history[tr['id']]
                enters=history[0][0]>0.8 and inside(history[0][1],door,.1)
                tr['role_hint']='cashier' if tr['id']==cashier else ('client' if enters else 'unknown')
        return cashier

    def cues(self,sample,zones):
        image=cv2.imread(str(sample['path']));h,w=image.shape[:2]
        tracks=sample['tracks'];cues={'tracks':tracks,'objects':[],'hands':[]}
        # Pose crops only for tracked people; face landmarks are discarded, no embeddings.
        if tracks:
            keypoints,scores=self.pose(image,bboxes=[x['box'] for x in tracks[:3]])
            for tr,k,s in zip(tracks,keypoints,scores):
                hands=[{'xy':[round(float(x)/w,3),round(float(y)/h,3)],'confidence':round(float(c),2)} for (x,y),c in zip(k[91:133],s[91:133]) if c>.45]
                cues['hands'].append({'track_id':tr['id'],'points':hands})
        for name in ('desk','safe'):
            if name in zones:
                roi=crop(image,zones[name])
                if roi is not None:cues['objects'] += [{'region':name,**o} for o in self.objects(roi,'banknote bundle. identity card. counting machine. safe door.')]
        return cues

    def release(self):
        del self.detector,self.gd,self.pose
        torch.cuda.empty_cache()

class Redactor:
    def __init__(self):
        self.net=cv2.FaceDetectorYN.create(str(MODELS/'yunet.onnx'),'',(320,320),.6,.3,5000)
    def evidence(self,sample):
        image=cv2.imread(str(sample['path']));h,w=image.shape[:2]
        self.net.setInputSize((w,h));_,faces=self.net.detect(image)
        for face in ([] if faces is None else faces):
            x,y,bw,bh=face[:4];pad=.25
            x1=max(0,int(x-pad*bw));y1=max(0,int(y-pad*bh));x2=min(w,int(x+(1+pad)*bw));y2=min(h,int(y+(1+pad)*bh))
            if x2>x1 and y2>y1:image[y1:y2,x1:x2]=cv2.GaussianBlur(image[y1:y2,x1:x2],(0,0),max(12,bw/4))
        result=encoded(image,sample['timestamp_sec']);result.pop('label')
        return result
