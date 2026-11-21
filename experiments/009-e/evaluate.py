"""Independent scorer; do not import the predictor. All masks are scored in full."""
import csv,hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[2];E=R/"results/009-semantic-hair-segmentation";D=E/"009-E"
def read(p):return json.loads(p.read_text(encoding="utf-8-sig"))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def mask(p):
    im=Image.open(p);assert im.size==(1152,2048) and im.mode=="L"
    arr=np.asarray(im);assert np.isin(arr,[0,255]).all()
    return arr>0
lock=read(D/"prediction-lock.json")
assert sha(R/"experiments/009-e/predict.py")==lock["code"]
assert sha(D/"rules.txt")==lock["rules"]==read(D/"preregistration.json")["sha256"].lower()
for k,n in [("decisions","fallback-decisions.json"),("pairs","pair-evaluation.json")]:assert sha(D/n)==lock[k]
for bc,table in [(R.parent,lock["inputs"]),(D,lock["masks"]),(D,lock["candidate_masks"])]:
    for name,h in table.items():assert sha(bc/name)==h
gallery=D/"error-gallery";gallery.mkdir(exist_ok=True)
rows=[];metrics={};dec=read(D/"fallback-decisions.json");st=read(D/"selection-stability.json")
valid=read(D/"root-validity.json")
for i in ("01","02"):
    metrics[i]={};ref=R/f"results/008-segmentation-accuracy/reference/asset-{i}"
    points=read(ref/"landmarks.json");roots={r["root"]:r for r in valid[i]}
    for mode in ("baseline","E1","E2","E3","combined","auto"):
        folder=D/f"predictions/{i}/{mode}";selection=dec[i][mode] if mode in ("baseline","auto") else st[i][mode]["winners"][0]
        ids=list(map(int,selection.split("-"))) if selection else []
        parts={}
        for j,n in enumerate(["hair-left","hair-right","skirt"]):
            p=mask(folder/(n+".png"));t=mask(ref/(n+".png"));tp=int((p&t).sum());fp=int((p&~t).sum());fn=int((~p&t).sum())
            v=dict(iou=tp/(tp+fp+fn),tp=tp,fp=fp,fn=fn,pixels=int(p.sum()),precision=tp/(tp+fp) if tp+fp else 0,recall=tp/(tp+fn))
            if j<2 and ids:
                selected=roots[ids[j]]["xy"];lm=points[n+"-root"];x,y=lm["x"],lm["y"]
                yy,xx=np.ogrid[:p.shape[0],:p.shape[1]];disk=(xx-x)**2+(yy-y)**2<=32**2
                v.update(root_xy=selected,root_error=float(np.hypot(selected[0]-x,selected[1]-y)),root_iou=float((p&t&disk).sum()/((p|t)&disk).sum()))
            if mode=="baseline":assert v["iou"]==read(E/"009-C/metrics.json")["assets"][i]["C"][n]["iou"]
            parts[n]=v;rows.append(dict(asset=i,method=mode,pair=selection,part=n,**v))
            if mode=="auto":
                img=np.full((*p.shape,3),24,np.uint8);img[p&t]=(110,200,120);img[p&~t]=(240,75,65);img[~p&t]=(70,155,245)
                overview=Image.fromarray(img).resize((288,512),Image.Resampling.NEAREST)
                if j<2:
                    bottom=np.nonzero(t)[0].max();tipx=int(np.median(np.flatnonzero(t[bottom])))
                    sheet=Image.new("RGB",(548,536),"white");sheet.paste(overview,(0,24));draw=ImageDraw.Draw(sheet)
                    for k,(cx,cy,title) in enumerate([(x,y,"root"),(tipx,bottom,"lowest visible tip")]):
                        cx=int(np.clip(cx,64,p.shape[1]-64));cy=int(np.clip(cy,64,p.shape[0]-64))
                        crop=Image.fromarray(img[cy-64:cy+64,cx-64:cx+64]).resize((240,240),Image.Resampling.NEAREST)
                        draw.text((294,k*264+3),title,fill="black");sheet.paste(crop,(294,k*264+22))
                    sheet.save(gallery/f"{i}-{n}.png")
                else:overview.save(gallery/f"{i}-{n}.png")
        metrics[i][mode]=parts
with (D/"ablations.csv").open("w",encoding="utf8",newline="") as f:
    writer=csv.DictWriter(f,fieldnames=sorted(set().union(*(row.keys() for row in rows))));writer.writeheader();writer.writerows(rows)
passed=sum(row["iou"]>=.9 for a in metrics.values() for row in a["auto"].values())
(D/"metrics.json").write_text(json.dumps(dict(formal="auto",passed=passed,total=6,manual_interventions=0,per_asset_parameters=0,per_asset_postprocessing=0,all_six_pass=passed==6,assets=metrics),indent=2))
for i,a in metrics.items():print(i,[(n,round(v["iou"],6),v.get("root_error"),v["pixels"]) for n,v in a["auto"].items()])
