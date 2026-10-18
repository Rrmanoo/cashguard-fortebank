"""Authenticated deployment smoke test. Writes no credentials to output."""
import argparse,base64,json,time
from pathlib import Path
import httpx

def run(a):
 Path(a.output).parent.mkdir(parents=True,exist_ok=True);key=Path(a.key_file).read_text().strip();base=a.url.rstrip('/');report={'base_url':base,'checks':{}}
 with httpx.Client(base_url=base,timeout=90,trust_env=False,follow_redirects=False,headers={'ngrok-skip-browser-warning':'1'}) as client:
  check=report['checks'];r=client.get('/healthz');r.raise_for_status();report['health']=r.json();check['health']=True
  for label,headers in [('no_key',{}),('wrong_key',{'X-API-Key':'wrong-key'})]:
   r=client.get('/api/v1/examples',headers=headers);assert r.status_code==401;check[label+'_401']=True
  headers={'X-API-Key':key};r=client.get('/');r.raise_for_status();assert key not in r.text;check['no_key_in_html']=True
  r=client.get('/api/v1/rules',headers=headers);r.raise_for_status();assert len(r.json()['rules'])==20;check['twenty_rules']=True
  r=client.post('/api/v1/session',headers=headers);r.raise_for_status();cookie=r.headers.get('set-cookie','');assert 'HttpOnly'in cookie and 'SameSite=strict'in cookie and ('Secure'in cookie or not base.startswith('https://'));check['private_session']=True
  gallery=client.get('/api/v1/examples');gallery.raise_for_status();items=gallery.json()['items'];report['examples']={'total':len(items),'done':sum(i['status']=='done' for i in items)}
  if items:
   item=next(i for i in items if i.get('video_ready'));r=client.get('/api/v1/examples/'+item['id']+'/video',headers={'Range':'bytes=0-127'});assert r.status_code==206 and len(r.content)==128;check['private_video_range']=True
  if a.video:
   begin=time.monotonic()
   with Path(a.video).open('rb') as video:r=client.post('/api/v1/analyze',headers=headers,files={'file':(Path(a.video).name,video,'video/quicktime')})
   assert r.status_code==202,r.text[:250];job=r.json()['job_id'];report['job_id']=job;check['accepted_202']=True
   while time.monotonic()-begin<310:
    r=client.get('/api/v1/jobs/'+job,headers=headers);r.raise_for_status();result=r.json()
    if result['status']!='processing':break
    time.sleep(2)
   report['end_to_end_seconds']=round(time.monotonic()-begin,3);report['job_status']=result['status'];assert result['status']=='done',result.get('error','Timeout')
   assert result['verdict'] in ['violation','no_violation'];assert (result['verdict']=='violation')==bool(result['violations'])
   for v in result['violations']:
    assert 0<=v['timecode_sec']<=result['duration_sec'];assert 1<=len(v['evidence_frames'])<=3
    for f in v['evidence_frames']:assert 0<=f['timestamp_sec']<=result['duration_sec'] and base64.b64decode(f['image_base64']).startswith(b'\xff\xd8')
    assert v['rule']['url'].startswith('https://adilet.zan.kz/')
   check['result_contract']=True;check['under_five_minutes']=report['end_to_end_seconds']<300;report['verdict']=result['verdict'];report['predicted_types']=[v['type_id'] for v in result['violations']];report['analysis_stats']=result['analysis_stats']
   Path(a.output).with_suffix('.result.json').write_text(json.dumps(result,ensure_ascii=False))
 Path(a.output).parent.mkdir(parents=True,exist_ok=True);Path(a.output).write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--key-file',required=True);p.add_argument('--output',required=True);p.add_argument('--video');run(p.parse_args())
