"""Oracle-only evaluation; writes derived masks exclusively below oracle/."""
from pathlib import Path
import json,importlib.util
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[2]; E=R/"results/009-semantic-hair-segmentation"; C=E/"009-C"
spec=importlib.util.spec_from_file_location("baseline",R/"experiments/009-b/predict.py")
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
def mask(p):return np.asarray(Image.open(p))>0
out={}
for i in ["01","02"]:
 work=R.parent/f"b009/pred-{i}"
 rows=json.loads((E/f"009-B/asset-{i}/prediction-lock.json").read_text())["layers_front_to_back"]
 visible=mask(work/"semantic-hair.png"); completed=np.zeros_like(visible)
 for row in rows:
  if row["name"] in ("front hair","back hair"):
   completed |= np.asarray(Image.open(work/"completed"/row["file"]).getchannel("A"))>=128
  if row["name"]=="face": face=mask(work/"semantic-visible"/row["file"])
 envelopes,_=b.motion(completed,face)
 ref=R/f"results/008-segmentation-accuracy/reference/asset-{i}"
 dst=C/"oracle"/i;dst.mkdir(exist_ok=True)
 out[i]={}
 for name,envelope in zip(["hair-left","hair-right"],envelopes):
  t=mask(ref/(name+".png"))
  vals={}
  for key,available in [("candidate",completed),("visibility",envelope),("connectivity",visible),("both",completed)]:
   m=t&available
   vals[key]=dict(upper=float(m.sum()/t.sum()),missing=int((t&~available).sum()),truth=int(t.sum()))
   Image.fromarray(m.astype("uint8")*255).save(dst/f"{key}-{name}.png")
  out[i][name]=vals
print(json.dumps(out))
(C/"oracle-diagnostics.json").write_text(json.dumps(dict(definitions={"candidate":"coverage of truth by completed hair alpha >=128","visibility":"optimistic IoU ceiling under frozen B topology: run B motion on completed hair, grant perfect visibility rejection (including removal of every FP); not an attainable semantic-owner prediction","connectivity":"perfect root/side labels restricted to B visible hair","both":"perfect visibility and labels restricted to completed hair; equals candidate coverage mathematically"},assets=out),indent=2))
