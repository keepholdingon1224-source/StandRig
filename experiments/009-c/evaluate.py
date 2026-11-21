"""Independent scoring of all pre-registered variants after both output locks exist."""
from pathlib import Path
import json,hashlib,importlib.util
import numpy as np
from PIL import Image,ImageDraw
import cv2
R=Path(__file__).resolve().parents[2];E=R/"results/009-semantic-hair-segmentation";C=E/"009-C"
spec=importlib.util.spec_from_file_location("metric008",R/"experiments/008-evaluate.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def read(p):return json.loads(p.read_text(encoding="utf-8-sig"))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for n,v in read(C/"preregistration.json")["files"].items():assert sha(R/n)==v
for idx in ("01","02"):
 folder=C/f"predictions/asset-{idx}"
 for method,items in read(folder/"lock.json").items():
  for n,v in items.items():assert sha(folder/method/(n+".png"))==v
metrics={};gallery=C/"error-gallery";gallery.mkdir(exist_ok=True)
for idx in ("01","02"):
 ref=R/f"results/008-segmentation-accuracy/reference/asset-{idx}";folder=C/f"predictions/asset-{idx}"
 truth={n:m.read(ref/(n+".png")) for n in (*m.PRIMARY,"uncertain")}
 landmarks=read(ref/"landmarks.json");lines=read(folder/"centerlines.json");roots=read(folder/"root-candidates.json")
 baseline=R.parent/f"b009/pred-{idx}";old_hair=m.read(baseline/"semantic-hair.png")
 completed=np.zeros_like(old_hair)
 for row in read(E/f"009-B/asset-{idx}/prediction-lock.json")["layers_front_to_back"]:
  if row["name"] in ("front hair","back hair"):completed|=np.asarray(Image.open(baseline/"completed"/row["file"]).getchannel("A"))>=128
 yy,xx=np.ogrid[:old_hair.shape[0],:old_hair.shape[1]]
 methods={};sheet=Image.new("RGB",(3*256,3*280),"white");draw=ImageDraw.Draw(sheet)
 for j,method in enumerate("ABC"):
  parts={}; owner=m.read(folder/method/"visible-hair.png")
  for k,n in enumerate(m.PARTS):
   mask=m.read(folder/method/(n+".png"));t=truth[n];fp=mask&~t;fn=t&~mask
   v=m.metric(mask,t,truth["uncertain"],truth["fixed"])
   v["fp_from_left_hair"]=int((fp&truth["hair-left"]).sum())
   if n!="skirt":
    lm=landmarks[n+"-root"];x,y=lm["x"],lm["y"]
    root=lines.get(n,{}).get("root_xy")
    def distance(pt):return float(np.hypot(pt[0]-x,pt[1]-y))
    disk=(xx-x)**2+(yy-y)**2<=32**2
    v.update(root_xy=root,reference_xy=[x,y],root_distance=distance(root) if root else None,
             nearest_candidate_distance=min((distance(r["xy"]) for r in roots),default=None),
             root_iou=m.iou(t&disk,mask&disk),fn_absent_from_hair=int((fn&~completed).sum()),
             fn_hidden_completed=int((fn&completed&~owner).sum()),fn_topology=int((fn&owner).sum()))
   else:
    bx,by=int(np.median(np.nonzero(t)[1])),int(np.median(np.nonzero(t)[0]))
    err=(fp|fn).astype("float32")
    wy,wx=np.unravel_index(cv2.blur(err,(128,128)).argmax(),err.shape)
    x,y=int(wx),int(wy)
   parts[n]=v
   x=int(np.clip(x,64,t.shape[1]-64));y=int(np.clip(y,64,t.shape[0]-64))
   region=np.s_[y-64:y+64,x-64:x+64]
   crop=np.full((128,128,3),20,np.uint8);crop[(t&mask)[region]]=(95,195,115);crop[fp[region]]=(250,90,80);crop[fn[region]]=(70,165,255)
   sheet.paste(Image.fromarray(crop).resize((256,256),Image.Resampling.NEAREST),(k*256,j*280+22))
   draw.text((k*256+4,j*280+4),f"{method} {n} ({x},{y})",fill="black")
  methods[method]=parts
 sheet.save(gallery/f"asset-{idx}.png");metrics[idx]=methods
passed=sum(v["passes_0_90"] for idx in metrics.values() for v in idx["C"].values())
(C/"metrics.json").write_text(json.dumps(dict(formal_method="C",threshold=.90,passes=passed,total=6,all_pass=passed==6,manual=0,per_asset_settings=0,assets=metrics),indent=2))
for i,rows in metrics.items():
 for method,row in rows.items():print(i,method,[(n,round(v["iou"],5),v.get("root_distance")) for n,v in row.items()])
