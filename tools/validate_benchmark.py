"""Verify benchmark artifact integrity, not visual truth of model statements."""
import argparse,base64,hashlib,json,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.release.logic import evaluate
FROZEN=['app/release/engine.py','app/release/logic.py','app/config.py','app/model_client.py','app/video.py','rules/criteria.json','rules/catalog.json']
def run(a):
 root=Path(a.benchmark);repo=Path(a.repo);summary=json.loads((root/'summary.json').read_text());protocol=json.loads((root/'protocol.json').read_text());catalog=json.loads((repo/'rules/criteria.json').read_text());ids={c['id'] for c in catalog};frozen={p:hashlib.sha256((repo/p).read_bytes()).hexdigest()==protocol['source_hashes'][p] for p in FROZEN};errors=[];seen=set();evidence=0;calls=0
 for row in summary['records']:
  h=row['sha256']
  if h in seen:continue
  seen.add(h)
  if row['status']!='done':continue
  folder=Path(row['result_path']).parent;result=json.loads(Path(row['result_path']).read_text());checks=json.loads((folder/'checks.json').read_text())
  def check(ok,message):
   if not ok:errors.append({'input_digest':h,'check':message})
  check(len(checks)==20 and {c['type_id'] for c in checks}==ids,'all20checks');check(result['analysis_stats']['thinking'] is False,'thinking_disabled');check(not result['analysis_stats']['reasoning_returned'],'no_returned_reasoning');check(result['verdict']==('violation' if result['violations'] else 'no_violation'),'verdict_consistency');check(len({v['type_id'] for v in result['violations']})==len(result['violations']),'no_duplicate_types')
  supported=set()
  for c in checks:
   calculated=evaluate(c['formula'],{p:f['status'] for p,f in c['facts'].items()});check(c['status']==calculated,'formula_consistency')
   if calculated=='supported':supported.add(c['type_id']);check(all(c['facts'][p]['status']=='supported' for p in c['proof_fact_ids']),'supported_proof_atoms')
  check(supported=={v['type_id'] for v in result['violations']},'emitted_types_match_formula')
  for v in result['violations']:
   check(0<=v['timecode_sec']<=row['duration_sec'],'violation_timestamp');check(1<=len(v['evidence_frames'])<=3,'evidence_count')
   for f in v['evidence_frames']:
    evidence+=1;data=base64.b64decode(f['image_base64'],validate=True);check(data.startswith(b'\xff\xd8') and data.endswith(b'\xff\xd9'),'real_jpeg_bytes');check((folder/'images'/(hashlib.sha256(data).hexdigest()+'.jpg')).exists(),'evidence_present_in_supplied_images');check(0<=f['timestamp_sec']<=row['duration_sec'],'frame_timestamp')
  for req in folder.glob('calls/**/request.json'):
   calls+=1;text=req.read_text();check(not any(r['filename'] in text for r in summary['records']),'filename_not_in_prompt');check((req.parent/'parsed.json').exists() and (req.parent/'completion.json').exists(),'call_outputs_saved')
 output={'scope':'Structural integrity only; this does not prove correct visual interpretation or legal applicability.','file_records':len(summary['records']),'unique_inputs':len(seen),'completed_unique':len({r['sha256'] for r in summary['records'] if r['status']=='done'}),'failed_unique':len({r['sha256'] for r in summary['records'] if r['status']!='done'}),'evidence_frames_verified':evidence,'calls_verified':calls,'frozen_inference_files_match':frozen,'errors':errors,'passed':not errors and all(frozen.values()),'git_revision_at_validation':subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()}
 (root/'validation.json').write_text(json.dumps(output,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in output.items() if k!='errors'},ensure_ascii=False,indent=2))
 if not output['passed']:raise SystemExit('Artifact integrity validation failed; inspect private validation.json')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--benchmark',required=True);p.add_argument('--repo',default=str(Path(__file__).resolve().parents[1]));run(p.parse_args())
