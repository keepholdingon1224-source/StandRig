"""Index source-resolution intermediate files and output hashes relative to the local study."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(p):
    with p.open("rb") as f:
        return hashlib.file_digest(f,"sha256").hexdigest()


def main(base,dest):
    repo=base/"StandRig"
    conditions={
        "inference":dict(code="fc4440db7c076518e313f378e28b1504e9886a95",layer="96f9311ff449dc86cfaba101ce4dfb4fd4958b80",
            depth="e53b344b5aa5beec7c141bd5601decaaff0898c9",cache_sha256=sha(base/"a3-body-1/cache.safetensors"),
            mode="NF4; A3 whole-model transfers using 009-A a3_smoke.py",seed=42,resolution=1024,depth_resolution=768,
            steps=30,marigold_steps=4,gpu="RTX 3060 Ti",gpu_uuid="GPU-cf2220a2-aaf6-affa-ea59-8951594faf5e",
            versions=["Python 3.12.10","torch 2.8.0+cu128","bitsandbytes 0.49.2","driver 610.88"]),
        "prediction":dict(rules_sha256=sha(dest/"rules.json"),manual_inputs=0)
    }
    files=[]
    def add(p,asset,origin):
        files.append(dict(path=p.relative_to(base).as_posix(),bytes=p.stat().st_size,sha256=sha(p),asset=asset,origin=origin))
    prev=dest.parent/"environment/nf4-intervention/run.json"
    pins=json.loads(prev.read_text())["replicates"][0]["outputs"]
    for idx,folder in [(1,base/"a3-smoke-1"),(2,base/"b009/asset-02")]:
        add(repo/f"source_00{idx+6}/original.png",idx,"input")
        for p in sorted(folder.rglob("*")):
            if p.is_file():
                add(p,idx,"inference")
                if idx==1 and p.name!="inference.txt":
                    assert files[-1]["sha256"]==pins[p.relative_to(folder).as_posix()]["sha256"]
        for p in sorted((base/f"b009/pred-{idx:02}").rglob("*")):
            if p.is_file():add(p,idx,"prediction")
    add(base/"b009/inference-02.txt",2,"inference log")
    add(base/"b009/inference-exit.txt",2,"inference exit")
    (dest/"manifest.json").write_text(json.dumps(dict(path_root="Live2D_009A",conditions=conditions,files=files),indent=2),encoding="utf8")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("base",type=Path);p.add_argument("dest",type=Path)
    args=p.parse_args();main(args.base.resolve(),args.dest.resolve())
