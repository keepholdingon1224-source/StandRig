import hashlib,json,os,shutil
from pathlib import Path
from huggingface_hub import HfApi,snapshot_download
p=Path(__file__).resolve().parent
out=p/"run-nf4-preflight"
refs=json.loads((out/"revisions-nf4.json").read_text(encoding="utf-8-sig"))
api=HfApi(); audit={}
for model,pin in refs.items():
    info=api.model_info(model,revision="e53b344" if "marigold" in model else pin,files_metadata=True)
    assert info.sha==pin
    loc=Path(snapshot_download(model,revision=pin,max_workers=2))
    files={}
    for entry in info.siblings:
        fn=loc/entry.rfilename
        with fn.open("rb") as f: sha=hashlib.file_digest(f,"sha256").hexdigest()
        assert fn.stat().st_size==entry.size
        if entry.lfs: assert sha==entry.lfs.sha256
        files[entry.rfilename]={"size":fn.stat().st_size,"sha256":sha,"lfs_sha256":entry.lfs.sha256 if entry.lfs else None}
        if entry.rfilename in ("README.md","LICENSE","NOTICE"):
            to=out/"model-documents"/model.split("/")[-1];to.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(fn,to/fn.name)
    audit[model]={"revision":pin,"files":files}
    (out/"verified-files.json").write_text(json.dumps(audit,indent=2),encoding="utf8")
    print(model,len(files),"verified",flush=True)
