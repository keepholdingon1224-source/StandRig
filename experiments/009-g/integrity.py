import hashlib,json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2]
P=R/'results/009-semantic-hair-segmentation'
D=P/'009-G'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(R),*args])
base='51caa13'
old=json.loads((P/'009-B/protected-start.json').read_text())
assert len(old)==2373 and all(sha(R/p)==h for p,h in old.items())
local=json.loads((P/'009-B/manifest.json').read_text())['files']
assert all(sha(R.parent/f['path'])==f['sha256'] for f in local)
paths=[p for p in git('ls-tree','-r','--name-only',base,'--','results/009-semantic-hair-segmentation','experiments').decode().splitlines() if p.startswith(('results/','experiments/009'))]
h={p:sha(R/p) for p in paths}
for group in range(0,len(paths),60):
    git('diff','--quiet',base,'--',*paths[group:group+60])
report=dict(protected=len(old),local=len(local),records=h)
if sys.argv[1]=='end':assert report==json.loads((D/'integrity-start.json').read_text())
(D/f'integrity-{sys.argv[1]}.json').write_text(json.dumps(report,indent=1))
print(len(old),len(local),len(h))

