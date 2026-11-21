import hashlib,json,sys,subprocess,platform,datetime
from pathlib import Path
P=Path(__file__).resolve().parent;out=P/"run-nf4-preflight"
def sha(f):
    with f.open("rb") as s:return hashlib.file_digest(s,"sha256").hexdigest()
def sums(d):
    m=d/"SHA256SUMS"
    files=[f for f in sorted(d.rglob("*")) if f.is_file() and f!=m]
    m.write_text("".join(f"{sha(f)}  {f.relative_to(d).as_posix()}\n" for f in files),encoding="utf8")
    for line in m.read_text().splitlines():
        value,name=line.split("  ",1);assert sha(d/name)==value
    return len(files)
if __name__=="__main__":
    print("preflight verified:",sums(out))
    d=P/"run-nf4-1024"
    if d.exists():
        for line in (d/"SHA256SUMS").read_text().splitlines():
            value,name=line.split("  ",1);assert sha(d/name)==value
        print("official runner checksums verified")
