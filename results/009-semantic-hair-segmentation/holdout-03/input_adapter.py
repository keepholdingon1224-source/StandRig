"""Input/output plumbing for the frozen two-slot G executable. No scoring."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from PIL import Image

OUT = Path(__file__).resolve().parent
P = OUT.parent
R = P.parents[1]
BASE = R.parent
EXP = R/"experiments"
WORK = BASE/"ho03"
SRC = OUT/"source/original.png"
PROV = OUT/"provenance.json"
def sha(p):
    with p.open("rb") as f:
        return hashlib.file_digest(f,"sha256").hexdigest()
def copy(src,dst):
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(src,dst)
    assert sha(src)==sha(dst)
def write(p,obj):
    tmp=p.with_suffix(".pending")
    tmp.write_text(json.dumps(obj,indent=2),encoding="utf8")
    tmp.replace(p)
def log(msg):
    with (OUT/"run.log").open("a",encoding="utf8") as f:
        print(datetime.datetime.now(datetime.timezone.utc).isoformat(),msg,file=f)
def main():
    rec=json.loads(PROV.read_text(encoding="utf-8-sig"))
    assert sha(Path(__file__))==rec["adapter"]["sha256"]
    assert sha(SRC)==rec["input"]["expected_sha256"] and Image.open(SRC).size==(1152,2048)
    for row in rec["code"].values():
        assert sha(R/row["path"])==row["sha256"]
    assert not (OUT/"prediction-lock.json").exists()
    # Exclusive creation prevents accidental second inference after any partial run.
    WORK.mkdir(exist_ok=False)
    ar=WORK/"r"
    ap=ar/"results/009-semantic-hair-segmentation"
    sg=ar/"experiments/009-g/predict.py"
    gr=ap/"009-G"
    copy(EXP/"009-g/predict.py",sg)
    copy(P/"009-G/rules.md",gr/"rules.md")
    copy(R/"source_007/original.png",ar/"source_007/original.png")
    copy(SRC,ar/"source_008/original.png")
    c1=Path("009-C/predictions/asset-01")
    for fname in ["centerlines.json","C/hair-left.png","C/hair-right.png","C/visible-hair.png","C/skirt.png"]:
        copy(P/c1/fname,ap/c1/fname)
    for file in (BASE/"b009/pred-01/completed").glob("*.png"):
        copy(file,WORK/"b009/pred-01/completed"/file.name)
    env=dict(os.environ,CUDA_VISIBLE_DEVICES="GPU-cf2220a2-aaf6-affa-ea59-8951594faf5e",
        HF_HOME=str(BASE/"hf"),HF_HUB_OFFLINE="1",PYTHONDONTWRITEBYTECODE="1",PYTHONUTF8="1",
        PYTHONUNBUFFERED="1",MPLCONFIGDIR=str(BASE/"mpl-cache"),OMP_NUM_THREADS="8",PYTHONPATH=str(BASE/"see-through/common"))
    settings=rec["planned_settings"]["A"]
    hub=BASE/"hf/hub"
    layer=next(hub.glob("models--*layerdiff3d_nf4/snapshots/"+settings["layerdiff_revision"]))
    depth=next(hub.glob("models--*marigold_nf4/snapshots/"+settings["marigold_revision"]))
    a=WORK/"A";a.mkdir()
    b=WORK/"b009/pred-02"
    c=ap/"009-C/predictions/asset-02"
    commands=[
        ("009-A",BASE/"see-through",[EXP/"009-local-nf4/a3_smoke.py",layer,depth,SRC,BASE/"a3-body-1/cache.safetensors",a]),
        ("009-B",R,[EXP/"009-b/predict.py",a/"original.psd",SRC,b,WORK/"B-share",P/"009-B/rules.json"]),
        ("009-C",R,[EXP/"009-c/predict.py",SRC,b,c]),
        ("009-G",ar,[sg])]
    for stage,cwd,args in commands:
        if stage=="009-A":rec["attempts"]=1
        rec["status"]="running "+stage
        rec["code"][stage]["executed"]=True
        write(PROV,rec);log(rec["status"])
        with (OUT/"resumption"/(stage+".log")).open("xb") as f:
            rc=subprocess.run([sys.executable,"-B",*map(str,args)],cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT).returncode
        rec["code"][stage]["returncode"]=rc
        if rc:
            rec["status"]="stopped "+stage;write(PROV,rec);log(rec["status"])
            raise SystemExit(rc)
        log(stage+" finished")
    expected=json.loads((gr/"prediction-lock.json").read_text())["masks"]
    hashes={}
    for name in ["hair-left","hair-right","skirt"]:
        rel="predictions/02/auto/"+name+".png"
        mask=gr/rel
        assert sha(mask)==expected[rel] and Image.open(mask).size==(1152,2048)
        dst=OUT/"predictions"/mask.name
        copy(mask,dst)
        hashes[dst.name]=sha(dst)
    write(OUT/"prediction-lock.json",dict(sha256=hashes,size=[1152,2048],adapter_commit=rec["adapter"]["commit"],
        source_sha256=sha(SRC),method_commit=rec["code"]["009-G"]["commit"],scored=False))
    rec.update(status="predictions locked",locked_predictions=hashes,
        fallback=json.loads((gr/"safety-decisions.json").read_text())["02"])
    write(PROV,rec)
    log("three masks locked; no scoring")
    for fname in ["safety-decisions.json","prediction-lock.json"]:
        copy(gr/fname,OUT/"resumption"/("G-"+fname))
if __name__=="__main__":
    main()
