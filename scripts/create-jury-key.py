"""Create once; do not print or overwrite an existing jury key."""
import os,secrets
from pathlib import Path
path=Path('private/jury-api.key');path.parent.mkdir(mode=0o700,exist_ok=True)
fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as out:out.write(secrets.token_urlsafe(40)+'\n')
print('Created private/jury-api.key (mode 0600). Keep outside version control.')
