"""A disposable subprocess makes the wall-clock deadline enforceable."""
import asyncio
import sys
from pathlib import Path
from . import store
from .inference import analyze

async def main():
    job,path=sys.argv[1:]
    try:
        result=await analyze(Path(path),lambda stage:store.update(job,stage=stage))
        store.update(job,status='done',stage='Готово',result=result)
    except Exception as exc:
        # Never log frames, descriptions, or request bodies.
        store.update(job,status='failed',error='Analysis failed: '+type(exc).__name__)
        raise SystemExit(1)

if __name__=='__main__': asyncio.run(main())

