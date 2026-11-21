"""Ideal moving-hair visibility first, followed by unmodified B connectivity. Oracle only."""
import importlib.util,json
from pathlib import Path
from PIL import Image
import numpy as np
R=Path(__file__).resolve().parents[2]
E=R/"results/009-semantic-hair-segmentation";C=E/"009-C"
spec=importlib.util.spec_from_file_location("old",R/"experiments/009-b/predict.py")
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
p=C/"oracle-diagnostics.json";data=json.loads(p.read_text())
data["visibility_first_note"]="Apply ideal moving-hair visibility (no left/right identity passed), retain B's visible hair on reference fixed pixels because fixed-hair truth is not annotated. Then rerun the original B connectivity rule. This conditional IoU measures order dependence; it need not be bounded by the separate fixed-envelope ceiling."
for i in ("01","02"):
 src=R.parent/f"b009/pred-{i}";ref=R/f"results/008-segmentation-accuracy/reference/asset-{i}"
 read=lambda p:np.asarray(Image.open(p))>0
 truth=[read(ref/(n+".png")) for n in ("hair-left","hair-right")]
 completed=np.zeros_like(truth[0])
 rows=json.loads((E/f"009-B/asset-{i}/prediction-lock.json").read_text())["layers_front_to_back"]
 for r in rows:
  if r["name"] in ("front hair","back hair"):completed|=np.asarray(Image.open(src/"completed"/r["file"]).getchannel("A"))>=128
  if r["name"]=="face":face=read(src/"semantic-visible"/r["file"])
 ideal=completed&(truth[0]|truth[1]) | (read(src/"semantic-hair.png")&read(ref/"fixed.png"))
 preds,_=b.motion(ideal,face)
 for n,t,m in zip(("hair-left","hair-right"),truth,preds):
  val=float((m&t).sum()/(m|t).sum());data["assets"][i][n]["visibility_first_conditional_iou"]=val
  Image.fromarray(m.astype("uint8")*255).save(C/f"oracle/{i}/visibility-first-{n}.png")
  print(i,n,val)
p.write_text(json.dumps(data,indent=2))
