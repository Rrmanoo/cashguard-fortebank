import json
import sqlite3
import time
from .config import DATA

def connect():
    DATA.mkdir(parents=True,exist_ok=True,mode=0o700)
    c=sqlite3.connect(DATA/'jobs.sqlite',timeout=10)
    c.row_factory=sqlite3.Row
    return c

def init():
    with connect() as c:
        c.execute('PRAGMA journal_mode=WAL')
        c.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, status TEXT NOT NULL, stage TEXT, created REAL NOT NULL, result TEXT, error TEXT)')
        c.execute("UPDATE jobs SET status='failed', error='Processing interrupted by service restart' WHERE status='processing'")

def create(job):
    with connect() as c:
        c.execute('INSERT INTO jobs VALUES (?, ?, ?, ?, NULL, NULL)',(job,'processing','Загрузка завершена',time.time()))

def update(job,**fields):
    assert set(fields)<= {'status','stage','result','error'}
    if 'result' in fields: fields['result']=json.dumps(fields['result'],ensure_ascii=False)
    with connect() as c:
        c.execute('UPDATE jobs SET '+','.join(k+'=?' for k in fields)+' WHERE id=?',[*fields.values(),job])

def get(job):
    with connect() as c: row=c.execute('SELECT * FROM jobs WHERE id=?',(job,)).fetchone()
    if row is None: return None
    result={'job_id':row['id'],'status':row['status'],'stage':row['stage']}
    if row['result']: result.update(json.loads(row['result']))
    if row['error']: result['error']=row['error']
    return result

def expire(before):
    with connect() as c:
        rows=c.execute("SELECT id FROM jobs WHERE created < ? AND status != 'processing'",(before,)).fetchall()
        c.execute("DELETE FROM jobs WHERE created < ? AND status != 'processing'",(before,))
    return [r['id'] for r in rows]

