import json,hashlib,sys,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[2]; E=R/"results/009-semantic-hair-segmentation"; D=E/"009-D"
def sha(p):
 with p.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
original=json.loads((E/"009-B/protected-start.json").read_text())
assert len(original)==2373 and all(sha(R/p)==v for p,v in original.items())
prior=json.loads((E/"009-B/manifest.json").read_text())["files"]
assert all(sha(R.parent/f["path"])==f["sha256"] for f in prior)
paths=subprocess.check_output(["git","-C",str(R),"ls-tree","-r","--name-only","14b101d","--",*[str((E/name).relative_to(R).as_posix()) for name in ("009-B","009-C")],"experiments/009-b","experiments/009-c"]).decode().splitlines()
records={p:sha(R/p) for p in paths}
assert not subprocess.check_output(["git","-C",str(R),"diff","14b101d","--",*paths])
report=dict(protected_005_008=len(original),prior_local=len(prior),pinned_records=records)
if sys.argv[1]=="end":assert report==json.loads((D/"integrity-start.json").read_text())
(D/f"integrity-{sys.argv[1]}.json").write_text(json.dumps(report,indent=1))
print(len(paths))
