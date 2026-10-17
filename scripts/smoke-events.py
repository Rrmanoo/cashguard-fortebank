"""Private integration smoke. Emit numeric diagnostics and code locations only."""
import asyncio,sys,traceback,json,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.inference import analyze
async def main():
 labels=json.loads(Path(str(Path(__file__).resolve().parents[1])+'/data/labels.json').read_text())
 source=Path(str(Path(__file__).resolve().parents[1])+'/data/videos')/labels[0]['filename']
 try:
  r=await analyze(source,lambda stage:print('stage advanced',flush=True))
  print(json.dumps({'ok':True,'seconds':r['processing_seconds'],'stats':r['analysis_stats'],'finding_count':len(r['violations'])}),flush=True)
 except Exception as e:
  print(type(e).__name__,flush=True)
  for f in traceback.extract_tb(e.__traceback__): print(f.filename,f.lineno,f.name,flush=True)
  sys.exit(1)
asyncio.run(main())
