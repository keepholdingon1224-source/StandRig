from pathlib import Path
import sys,json,hashlib,subprocess
R=Path(__file__).resolve().parents[2]; E=R/"results/009-semantic-hair-segmentation"; C=E/"009-C"
def sha(p):
 with p.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
expected=json.loads((E/"009-B/protected-start.json").read_text())
paths=subprocess.check_output(["git","-C",str(R),"ls-files","-z","--","source_007","source_008",":(glob)experiments/00[5-8]-*",":(glob)results/00[5-8]-*/**"]).decode().strip("\0").split("\0")
assert set(paths)==set(expected) and len(paths)==2373
assert all(sha(R/k)==v for k,v in expected.items())
prev=json.loads((E/"009-B/manifest.json").read_text())["files"]
assert all(sha(R.parent/i["path"])==i["sha256"] for i in prev)
(C/("integrity-"+sys.argv[1]+".json")).write_text(json.dumps(dict(protected=2373,previous_artifacts=len(prev),matched=True,protected_manifest_sha256=sha(E/"009-B/protected-start.json")),indent=2))
