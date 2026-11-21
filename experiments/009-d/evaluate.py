"""Only the scorer accesses ground truth; verify frozen predictor, inputs and outputs first."""
from pathlib import Path
import hashlib,json,csv,importlib.util
import numpy as np
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[2];E=R/"results/009-semantic-hair-segmentation";D=E/"009-D"
def read(p):return json.loads(p.read_text(encoding="utf-8-sig"))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=1),encoding="utf8")
l=read(D/"prediction-lock.json")
for base,key in [(R,"code"),(D,"masks"),(R.parent,"inputs")]:
    for p,h in l[key].items():assert sha(base/p)==h
assert sha(D/"preregistered-methods.txt")==l["config"]==read(D/"preregistration.json")["sha256"].lower()
spec=importlib.util.spec_from_file_location("metrics008",R/"experiments/008-evaluate.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
metrics={};errors={};csvrows=[];gallery=D/"error-gallery";gallery.mkdir(exist_ok=True)
ranking=read(D/"root-ranking.json");paths=read(D/"path-comparison.json")
for i in ["01","02"]:
    ref=R/f"results/008-segmentation-accuracy/reference/asset-{i}"; c=E/f"009-C/predictions/asset-{i}"
    visible=m.read(c/"C/visible-hair.png")
    truth={n:m.read(ref/(n+".png")) for n in [*m.PRIMARY,"uncertain"]}
    lm=read(ref/"landmarks.json");yy,xx=np.ogrid[:visible.shape[0],:visible.shape[1]]
    graph=read(c/"hair-graph.json");coords=graph["nodes"];metrics[i]={};errors[i]={}
    for name,(rm,pm,om) in l["variants"].items():
        metrics[i][name]={};errors[i][name]={}
        for k,n in enumerate(m.PARTS):
            t=truth[n];pred=m.read(D/f"predictions/{i}/{name}/{n}.png")
            v=m.metric(pred,t,truth["uncertain"],truth["fixed"])
            if k<2:
                v["missed_visible_connection"]=int((t&visible&~pred).sum())
                root=coords[paths[i][name][k]["root"]]
                x,y=(lm[n+"-root"][a] for a in ("x","y"))
                distance=lambda xy:float(np.hypot(xy[0]-x,xy[1]-y))
                disk=(xx-x)**2+(yy-y)**2<=32**2
                er=dict(root=root,reference=[x,y],distance=distance(root),window_iou=m.iou(t&disk,pred&disk),
                        nearest_candidate=min(distance(r["xy"]) for r in ranking[i]))
                errors[i][name][n]=er
                if name=="formal":
                    ty=int(np.nonzero(t)[0].max());tx=int(np.median(np.flatnonzero(t[ty])))
                    sheet=Image.new("RGB",(512,282),"white")
                    for j,(cx,cy,title) in enumerate([(x,y,"reference root"),(tx,ty,"lowest visible tip")]):
                        cx=int(np.clip(cx,64,t.shape[1]-64));cy=int(np.clip(cy,64,t.shape[0]-64))
                        region=np.s_[cy-64:cy+64,cx-64:cx+64];a,b=pred[region],t[region]
                        crop=np.full((128,128,3),20,np.uint8);crop[a&b]=(100,195,115);crop[a&~b]=(245,85,70);crop[~a&b]=(75,150,255)
                        sheet.paste(Image.fromarray(crop).resize((256,256),Image.Resampling.NEAREST),(j*256,26))
                        ImageDraw.Draw(sheet).text((j*256+3,5),f"{title} ({cx},{cy})",fill="black")
                    sheet.save(gallery/f"{i}-{n}.png")
            metrics[i][name][n]=v
            csvrows.append(dict(asset=i,variant=name,root=rm,path=pm,ownership=om,part=n,iou=v["iou"],precision=v["precision"],
                recall=v["recall"],fp=v["false_positive_pixels"],fn=v["false_negative_pixels"],fixed_fp=v["fixed_pixels_misclassified"],
                missed_visible=v.get("missed_visible_connection"),root_error=errors[i][name].get(n,{}).get("distance"),
                root_iou=errors[i][name].get(n,{}).get("window_iou")))
    for n in m.PARTS:
        old=read(E/"009-C/metrics.json")["assets"][i]["C"][n]
        assert metrics[i]["baseline"][n]["iou"]==old["iou"]
dump(D/"metrics.json",dict(formal="formal",manual=0,per_asset_settings=0,threshold=.90,
     passed=sum(v["iou"]>=.9 for a in metrics.values() for v in a["formal"].values()),assets=metrics))
dump(D/"root-errors.json",errors)
with (D/"ablations.csv").open("w",encoding="utf8",newline="") as f:
    writer=csv.DictWriter(f,fieldnames=csvrows[0].keys());writer.writeheader();writer.writerows(csvrows)
for i,rs in metrics.items():
    for n,parts in rs.items():print(i,n,[round(v["iou"],4) for v in parts.values()])
