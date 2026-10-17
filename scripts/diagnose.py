"""Numerical inference diagnostics. Never print image or description content."""
import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import inference

original=inference.ask
async def monitored(prompt,images,schema):
    result=await original(prompt,images,schema)
    if schema is inference.Scan:
        print(json.dumps({'stage':'overview','candidates':len(result.candidates),
                          'confidence_values':[c.confidence for c in result.candidates]}),flush=True)
    else:
        times=[f['timestamp_sec'] for f in images]
        print(json.dumps({'stage':'verification','supported':result.supported,'confidence':result.confidence,
                          'timestamp_in_range':min(times)-.1<=result.timestamp_sec<=max(times)+.1,
                          'evidence_timestamp_deltas':[round(min(abs(t-a) for a in times),4) for t in result.evidence_timestamps]}),flush=True)
    return result

async def main():
    inference.ask=monitored
    for p in sys.argv[1:]:
        result=await inference.analyze(Path(p))
        print(json.dumps({'final_event_count':len(result['violations']),'processing_seconds':result['processing_seconds']}),flush=True)

if __name__=='__main__':asyncio.run(main())
