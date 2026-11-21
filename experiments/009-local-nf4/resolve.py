"""Resolve the two reviewed NF4 revisions against the registry before downloading."""
import json
from pathlib import Path
from huggingface_hub import HfApi
p=Path(__file__).resolve().parent
src=p/"StandRig/results/009-semantic-hair-segmentation/environment/model-revisions.json"
out=p/"run-nf4-preflight";out.mkdir(exist_ok=True)
pins={}
for model,entry in json.loads(src.read_text(encoding="utf-8-sig"))["nf4"]["models"].items():
    ref=entry.get("public_short_revision") or entry["revision"]
    sha=HfApi().model_info(model,revision=ref).sha
    if not sha.startswith(ref) or len(sha)!=40:raise ValueError((model,ref,sha))
    pins[model]=sha
(out/"revisions-nf4.json").write_text(json.dumps(pins,indent=2),encoding="utf8")
