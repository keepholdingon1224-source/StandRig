from pathlib import Path
import json,hashlib,subprocess,sys,datetime
R=Path.cwd()
P=R/'results/009-semantic-hair-segmentation'
D=P/'holdout-03'
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
if phase=='start':
    fixed='38ff2140c8f1358305931276d450040986657973'
    stages={}
    for stage,path,commit in [('009-A','experiments/009-local-nf4/a3_smoke.py',base),('009-B','experiments/009-b/predict.py',base),('009-C','experiments/009-c/predict.py',base),('009-G','experiments/009-g/predict.py',fixed),('rules',str((P/'009-G/rules.md').relative_to(R).as_posix()),fixed)]:
        h=sha(git('show',f'{commit}:{path}'))
        assert git("hash-object","--path",path,path).strip()==git("rev-parse",f"{commit}:{path}").strip()
        stages[stage]=dict(path=path,commit=commit,git_blob_sha256=h,sha256=digest(R/path),executed=False)
    assert stages['009-G']['sha256']=='e7b5b641e161a577082a0cf34ff351130aff52abcea71bc811d7737c92d5513d'
    assert stages['rules']['sha256']=='5d5401cfac8d4e3e08599859b7237e018e9b14bb736189fa1b41e72f8283436a'
    record=dict(status='stopped_preflight',input=dict(expected_sha256='8c9bf2c4b8a6f7e553dd9f54578ec0f02178fb698fcc87c4e33ca24cddc87083',expected_size=[1152,2048],actual_sha256=None,actual_size=None,verification='source not supplied'),code=stages,
    planned_settings=dict(A=dict(gpu='RTX 3060 Ti',quantization='NF4',offload='A3',resolution=1024,depth=768,seed=42,layerdiff_steps=30,marigold_steps=4,layerdiff_revision='96f9311ff449dc86cfaba101ce4dfb4fd4958b80',marigold_revision='e53b344b5aa5beec7c141bd5601decaaff0898c9'),B='frozen visible masks',C='C2-C',G='D with whole-asset fallback to A'),
    blocker='Frozen G main loops over 01 and 02; Asset selects source_007 or source_008. No audited holdout adapter identified in pinned repository.',attempts=0,scored=False,fallback=None,locked_predictions=[])
    (D/'provenance.json').write_text(json.dumps(record,indent=2))
with (D/'run.log').open('a') as f:f.write(f'{datetime.datetime.now(datetime.timezone.utc).isoformat()} preflight {phase}: protection verified; inference launches=0\n')

