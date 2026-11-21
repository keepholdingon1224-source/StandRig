"""Post-lock diagnostic: distinguish occlusion by stack order from missing hair coverage."""
import argparse,json
from pathlib import Path
import hashlib
import numpy as np
from PIL import Image

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for key in ["pred","shared","reference"]:
        p.add_argument(key,type=Path)
    a=p.parse_args()
    lock=json.loads((a.shared/"prediction-lock.json").read_text())
    sem=a.pred/"semantic-hair.png"
    assert hashlib.sha256(sem.read_bytes()).hexdigest()==lock["mask_sha256"]["semantic-hair"]
    visible=np.asarray(Image.open(sem))!=0
    completed=np.zeros_like(visible)
    for row in lock["layers_front_to_back"]:
        if row["name"] in ("front hair","back hair"):
            completed |= np.asarray(Image.open(a.pred/"completed"/row["file"]).getchannel("A"))>=128
    rows={}
    for part in ["hair-left","hair-right"]:
        truth=np.asarray(Image.open(a.reference/(part+".png")))!=0
        rows[part]=dict(reference_pixels=int(truth.sum()),visible_semantic_hair=int((truth&visible).sum()),
            occluded_by_other_semantics=int((truth&completed&~visible).sum()),absent_even_from_completed_hair=int((truth&~completed).sum()))
        assert sum(list(rows[part].values())[1:])==int(truth.sum())
    (a.shared/"hair-coverage.json").write_text(json.dumps(rows,indent=2))
    print(rows)
