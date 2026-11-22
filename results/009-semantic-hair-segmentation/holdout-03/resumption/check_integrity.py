from pathlib import Path
import json,hashlib,subprocess,sys,datetime
R=Path.cwd()
P=R/'results/009-semantic-hair-segmentation'
D=P/'holdout-03'/'resumption'
def git(*args):return subprocess.check_output(['git',*args])
def sha(b):return hashlib.sha256(b).hexdigest()
def digest(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
base='0bc5af0cfef748e237cea4a4f4c9fec77c098afd'
phase=sys.argv[1]
refs=json.loads((P/'009-B/protected-start.json').read_text())
local=json.loads((P/'009-B/manifest.json').read_text())['files']
assert len(refs)==2373 and all(digest(R/p)==v for p,v in refs.items())
assert all(digest(R.parent/v['path'])==v['sha256'] for v in local)
paths=[p for p in git('ls-tree','-r','--name-only',base,'--','results/009-semantic-hair-segmentation','experiments').decode().splitlines() if p.startswith(('results/','experiments/009'))]
digests={p:digest(R/p) for p in paths}
for k in range(0,len(paths),60):git('diff','--quiet',base,'--',*paths[k:k+60])
summary=dict(protected=len(refs),local=len(local),tracked=len(paths),tracked_digest=sha(json.dumps(digests,sort_keys=True).encode()))
if phase=='end':assert json.loads((D/'integrity-start.json').read_text())==summary
(D/f'integrity-{phase}.json').write_text(json.dumps(summary,indent=2))
print(summary)

