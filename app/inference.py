import asyncio,json,time,tempfile,os
from pathlib import Path
import httpx
from .config import ROOT,MODEL_URL,MODEL_NAME,DATA
from .video import probe
from .events import Window,SYSTEM,normalize
from .rules import evaluate

async def ask(prompt,images,schema=Window):
    content=[{'type':'text','text':prompt}]
    for f in images:
        content += [{'type':'text','text':f"Frame {f['timestamp_sec']:.3f}s; {f.get('label','full frame')}"},
                    {'type':'image_url','image_url':{'url':'data:image/jpeg;base64,'+f['image_base64']}}]
    async with httpx.AsyncClient(timeout=100,trust_env=False) as client:
        r=await client.post(MODEL_URL+'/chat/completions',json={
         'model':MODEL_NAME,'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':content}],
         'temperature':0,'seed':17,'max_tokens':2300,
         'response_format':{'type':'json_schema','json_schema':{'name':schema.__name__,'strict':True,'schema':schema.model_json_schema()}}})
        r.raise_for_status();choice=r.json()['choices'][0]
        if choice['finish_reason']=='length':raise RuntimeError('Truncated event response')
        return schema.model_validate_json(choice['message']['content'])

async def analyze(path:Path,progress=lambda stage:None):
    from .perception import decode,Perception,Redactor,encoded,crop
    import cv2
    started=time.monotonic();meta=await asyncio.to_thread(probe,path)
    DATA.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='frames-',dir=path.parent) as tmp:
        progress('Кадры и зоны наблюдения')
        samples=await asyncio.to_thread(decode,path,Path(tmp));perception=await asyncio.to_thread(Perception)
        try:
            zones=await asyncio.to_thread(perception.regions,samples)
            progress('Люди, траектории и движения рук')
            cashier=await asyncio.to_thread(perception.people,samples,zones)
            # Seven original-resolution samples per 2.8s window. Last frame overlaps
            # next window so boundary handovers remain visible. Crop supplements <= 4.
            windows=[]
            for start in range(0,len(samples),6):
                group=samples[start:start+7]
                if not group:continue
                middle=group[len(group)//2]
                cues=await asyncio.to_thread(perception.cues,middle,zones)
                windows.append((group,cues))
        finally:perception.release()
        perception_seconds=time.monotonic()-started
        progress('Наблюдаемые события по коротким окнам')
        gate=asyncio.Semaphore(4)
        async def tag(group,cues):
            async with gate:
                images=[]
                for f in group:
                    image=cv2.imread(str(f['path']))
                    images.append(encoded(image,f['timestamp_sec']))
                for f in [group[0],group[-1]]:
                    image=cv2.imread(str(f['path']))
                    for region in ('desk','safe'):
                        if region in zones:
                            roi=crop(image,zones[region])
                            if roi is not None:images.append(encoded(roi,f['timestamp_sec'],region+' crop, 2x interpolation; no additional real detail'))
                annotation=await ask('Annotate this ordered short window. Full frames and crops with the same timestamp are the SAME instant. '
                    'Return observable events only. Geometric/object/hand cues are fallible proposals, never proof. '
                    'No legal rules are supplied. Zones (normalized xyxy) and midpoint cues: '+json.dumps({'zones':zones,'cues':cues}),images)
                return {'start':group[0]['timestamp_sec'],'end':group[-1]['timestamp_sec'],
                        'timestamps':[f['timestamp_sec'] for f in group],'annotation':annotation}
        tagged=await asyncio.gather(*(tag(*w) for w in windows))
        timeline=normalize(tagged);progress('Правила последовательности и кадры-доказательства')
        findings=evaluate(timeline)
        catalog=json.loads((ROOT/'rules/catalog.json').read_text());registry={r['id']:r for r in catalog['rules']};source=catalog['source']
        redactor=Redactor();violations=[]
        for finding in findings:
            rule=registry[finding['rule_id']]
            if not rule['enabled']:continue
            evidence=[]
            for t in finding['evidence_times'][:3]:
                sample=min(samples,key=lambda f:abs(f['timestamp_sec']-t))
                evidence.append(redactor.evidence(sample))
            violations.append({'type':rule['name'],'timecode_sec':finding['time'],
                'description':finding['observed']+' Возможный признак для проверки человеком. '+source['title']+', '+rule['clause']+'. '+source['url'],
                'confidence':finding['confidence'],'evidence_frames':evidence,
                'rule':{'id':rule['id'],'document':source['title'],'clause':rule['clause'],'url':source['url']}})
        return {'verdict':'violation' if violations else 'no_violation','violations':violations,
          'processing_seconds':round(time.monotonic()-started,2),'duration_sec':meta['duration'],
          'analysis_stats':{'sampled_frames':len(samples),'windows':len(windows),'perception_seconds':round(perception_seconds,2),
                            'identified_cashier_track':cashier,'calibrated_regions':sorted(zones),'verified_event_count':len(violations)},
          'event_timeline':[{'start_sec':w['start'],'end_sec':w['end'],'facts':w['facts'],'observed':w['annotation'].observed} for w in timeline],
          'limitations':['Скрытые действия считаются неизвестными; вывод требует проверки человеком.',
           'Пропуск пересчета или осмотра по редкой выборке кадров не устанавливается.',
           'Размытие автоматически найденных лиц может пропустить мелкие или закрытые лица.',
           'Отсутствие выявленных признаков не подтверждает соблюдение всех требований.']}
