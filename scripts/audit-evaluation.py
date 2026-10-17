"""Run on the private server. Print aggregate metrics, never scene descriptions."""
import json,sqlite3,statistics
from pathlib import Path
rows=json.loads(Path(str(Path(__file__).resolve().parents[1])+'/evaluation/events.json').read_text())
done=[r for r in rows if r['status']=='done']
metrics={'n':len(rows),'completed':len(done),'tp':sum(r['expected'] and r['predicted'] for r in done),
 'tn':sum(not r['expected'] and not r['predicted'] for r in done),
 'fp':sum(not r['expected'] and r['predicted'] for r in done),
 'fn':sum(r['expected'] and not r['predicted'] for r in done),
 'p50_seconds':statistics.median(r['elapsed_sec'] for r in rows),
 'max_seconds':max(r['elapsed_sec'] for r in rows)}
print(json.dumps(metrics))
