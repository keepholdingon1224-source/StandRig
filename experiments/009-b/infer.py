"""Reproduce B4 with the 009-A A3 script, pinned models and validated text-only cache."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

def run(base,out,validation):
    repo=base/"StandRig"
    official=base/"see-through"
    tools=repo/"experiments/009-local-nf4"
    pin=repo/"results/009-semantic-hair-segmentation/environment/nf4-intervention/gate3.json"
    cache=base/"a3-body-1/cache.safetensors"
    with cache.open("rb") as f:
        assert hashlib.file_digest(f,"sha256").hexdigest()==json.loads(pin.read_text())[0]["cache_file_sha256"]
    assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=official,text=True).strip()=="fc4440db7c076518e313f378e28b1504e9886a95"
    assert not subprocess.check_output(["git","status","--porcelain"],cwd=official)
    if out.exists():raise FileExistsError(out)
    out.parent.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,CUDA_VISIBLE_DEVICES="GPU-cf2220a2-aaf6-affa-ea59-8951594faf5e",HF_HOME=str(base/"hf"),
             HF_HUB_OFFLINE="1",PYTHONDONTWRITEBYTECODE="1",PYTHONUTF8="1",PYTHONUNBUFFERED="1",OMP_NUM_THREADS="8",
             MPLCONFIGDIR=str(base/"mpl-cache"),PYTHONPATH=str(official/"common"))
    hub=base/"hf/hub"
    layer=hub/"models--24yearsold--seethroughv0.0.2_layerdiff3d_nf4/snapshots/96f9311ff449dc86cfaba101ce4dfb4fd4958b80"
    depth=hub/"models--24yearsold--seethroughv0.0.1_marigold_nf4/snapshots/e53b344b5aa5beec7c141bd5601decaaff0898c9"
    source=repo/"source_008/original.png"
    with (out.parent/"inference-02.txt").open("xb") as log:
        proc=subprocess.run([sys.executable,"-B",tools/"a3_smoke.py",layer,depth,source,cache,out],
                            cwd=official,env=env,stdout=log,stderr=subprocess.STDOUT)
    (out.parent/"inference-exit.txt").write_text(str(proc.returncode))
    proc.check_returncode()
    subprocess.run([sys.executable,"-B",tools/"a3_validate.py",source,out,validation],cwd=official,env=env,check=True)
    assert json.loads(validation.read_text())["pass_gate"]


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for name in ["base","output","validation"]:p.add_argument(name,type=Path)
    args=p.parse_args()
    run(args.base.resolve(),args.output.resolve(),args.validation.resolve())
