"""Build a private authenticated gallery from benchmark outputs, preserving preview IDs."""
import argparse,json,shutil,datetime,re
from pathlib import Path

def timestamp_seconds(value):
 if value is None:return None
 if isinstance(value,(int,float)):return float(value)
 text=str(value).strip().lower().replace(',','.')
 minute=re.search(r'(\d+(?:\.\d+)?)\s*мин',text)
 second=re.search(r'(\d+(?:\.\d+)?)\s*сек',text)
 if minute or second:return (float(minute.group(1))*60 if minute else 0)+(float(second.group(1)) if second else 0)
 return float(text)

def build(benchmark,previous,output):
 root=Path(benchmark);out=Path(output);out.mkdir(parents=True,exist_ok=True);(out/'results').mkdir(exist_ok=True)
 manifest=json.loads(Path(previous).read_text());summary=root/'summary.json';complete=summary.exists();data=json.loads((summary if complete else root/'progress.json').read_text());records={r['filename']:r for r in data['records']}
 for item in manifest['items']:
  row=records.get(item['filename']);item.pop('job_id',None);item.pop('submitted_at',None);item.pop('completed_at',None);item.pop('error',None)
  item.update(status='queued',model='qwen',architecture_version='2026.10.18-final.1',elapsed_sec=0,matches_reference=False)
  for k in ['verdict','violation_count']:item.pop(k,None)
  if row:
   item.update(expected_violation=row['expected'],expected_timestamp_sec=timestamp_seconds(row['reference_timestamp_sec']),status=row['status'],elapsed_sec=row['elapsed_sec'],expected_types=row['expected_types'],human_type=row['human_type'])
   if row['status']=='done':
    result=json.loads(Path(row['result_path']).read_text());item.update(verdict=result['verdict'],violation_count=len(result['violations']),matches_reference=(result['verdict']=='violation')==row['expected'],primary_type_matches=sorted(set(row['expected_types'])&set(row['predicted_types'])))
    (out/'results'/(item['id']+'.json')).write_text(json.dumps(result,ensure_ascii=False))
   else:item['error']=row.get('error','Analysis failed')
 manifest.update(status='done' if complete else 'processing',model_label='Qwen3.6 · финальная версия',architecture_version='2026.10.18-final.1',updated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),source='development benchmark, 42 file records / 40 unique inputs; reference is never passed to inference')
 if complete:manifest['metrics']=data['metrics_42']
 (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2));print('Gallery:',sum(x['status']=='done' for x in manifest['items']),'done of',len(manifest['items']))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--benchmark',required=True);p.add_argument('--previous',required=True);p.add_argument('--output',required=True);a=p.parse_args();build(a.benchmark,a.previous,a.output)
