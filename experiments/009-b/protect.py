import hashlib,json,sys,subprocess
from pathlib import Path
r=Path(__file__).resolve().parents[2]
dest=r/"results/009-semantic-hair-segmentation/009-B"
paths=subprocess.check_output(["git","-C",str(r),"ls-files","-z","--","source_007","source_008",":(glob)experiments/00[5-8]-*",":(glob)results/00[5-8]-*/**"]).decode().strip("\0").split("\0")
hashes={}
for name in paths:
 with (r/name).open("rb") as f:hashes[name]=hashlib.file_digest(f,"sha256").hexdigest()
p=dest/"protected-start.json"
if sys.argv[1]=="start":
 with p.open("x",encoding="utf8") as f:json.dump(hashes,f,indent=2)
else:
 assert hashes==json.loads(p.read_text(encoding="utf8"))
 (dest/"protected-end.json").write_text(json.dumps(dict(identical=True,files=len(hashes),start_manifest_sha256=hashlib.sha256(p.read_bytes()).hexdigest()),indent=2))
print("protected",len(hashes),flush=True)
