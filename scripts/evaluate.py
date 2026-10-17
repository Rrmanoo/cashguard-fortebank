"""Run ONLY on the private server. Persist content locally, print aggregate metrics only.

This is a development-set benchmark, never evidence of unseen-video generalization.
Labels are read only by the evaluator, never passed to the model.
"""
import argparse
import asyncio
import json
import statistics
import time
import math
from pathlib import Path
import httpx

async def main():
    p=argparse.ArgumentParser()
    p.add_argument('--labels',required=True);p.add_argument('--videos',required=True)
    p.add_argument('--key-file',required=True);p.add_argument('--output',required=True)
    p.add_argument('--limit',type=int,default=0);p.add_argument('--url',default='http://127.0.0.1:9017')
    p.add_argument('--resume',action='store_true')
    args=p.parse_args();labels=json.loads(Path(args.labels).read_text())
    if args.limit:labels=labels[:args.limit]
    rows=json.loads(Path(args.output).read_text()) if args.resume and Path(args.output).exists() else []
    completed={r['filename'] for r in rows}
    async with httpx.AsyncClient(timeout=30,trust_env=False,headers={'X-API-Key':Path(args.key_file).read_text().strip()}) as client:
        for label in labels:
            if label['filename'] in completed:continue
            path=Path(args.videos)/label['filename'];start=time.monotonic()
            while True:
                attempt_start=time.monotonic()
                with path.open('rb') as f:
                    response=await client.post(args.url+'/api/v1/analyze',files={'file':(path.name,f,'video/quicktime')})
                if response.status_code!=429 or time.monotonic()-start>270:break
                await asyncio.sleep(1)
            response.raise_for_status();job=response.json()['job_id'];start=attempt_start
            while True:
                await asyncio.sleep(1)
                r=await client.get(args.url+'/api/v1/jobs/'+job);r.raise_for_status();result=r.json()
                if result['status']!='processing':break
                if time.monotonic()-start>300:result={'status':'failed','error':'Jury deadline'};break
            elapsed=time.monotonic()-start
            row={'filename':path.name,'job_id':job,'expected':label['violation'],'expected_timestamp_sec':label['timestamp_sec'],'elapsed_sec':round(elapsed,2),'status':result['status']}
            if result['status']=='done':
                row['predicted']=result['verdict']=='violation'
                row['predicted_timestamps_sec']=[v['timecode_sec'] for v in result['violations']]
                if label['timestamp_sec'] is not None and result['violations']:
                    row['nearest_timestamp_error_sec']=min(abs(v['timecode_sec']-label['timestamp_sec']) for v in result['violations'])
            else:row['error']=result.get('error','Unknown')
            rows.append(row)
            out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
            out.write_text(json.dumps(rows,ensure_ascii=False,indent=2))
            # No video descriptions, images, or scene-derived labels cross into cloud tooling.
            print(json.dumps({'completed':len(rows),'total':len(labels),'status':row['status'],'elapsed_sec':row['elapsed_sec']}),flush=True)
    done=[r for r in rows if r['status']=='done']
    tp=sum(r['expected'] and r['predicted'] for r in done)
    tn=sum(not r['expected'] and not r['predicted'] for r in done)
    fp=sum(not r['expected'] and r['predicted'] for r in done)
    fn=sum(r['expected'] and not r['predicted'] for r in done)
    metrics={'dataset':'provided development set','n':len(rows),'completed':len(done),'tp':tp,'tn':tn,'fp':fp,'fn':fn,
             'accuracy_including_failures':(tp+tn)/len(rows),
             'precision':tp/(tp+fp) if tp+fp else None,'recall_completed':tp/(tp+fn) if tp+fn else None,
             'max_latency_sec':max(r['elapsed_sec'] for r in rows)}
    latencies=sorted(r['elapsed_sec'] for r in rows)
    metrics['p50_latency_sec']=statistics.median(latencies)
    metrics['p95_latency_sec']=latencies[math.ceil(.95*len(latencies))-1]
    metrics['recall_including_failures']=tp/sum(r['expected'] for r in rows) if any(r['expected'] for r in rows) else None
    errors=[r['nearest_timestamp_error_sec'] for r in done if 'nearest_timestamp_error_sec' in r]
    if errors:metrics['median_nearest_event_timestamp_error_sec']=statistics.median(errors)
    Path(args.output).with_suffix('.metrics.json').write_text(json.dumps(metrics,indent=2))
    print(json.dumps(metrics),flush=True)

if __name__=='__main__':asyncio.run(main())
