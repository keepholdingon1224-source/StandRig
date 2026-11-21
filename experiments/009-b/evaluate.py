"""Independent scorer. Verify the prediction lock and frozen input hashes before scoring."""
import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

spec=importlib.util.spec_from_file_location("metrics008",Path(__file__).resolve().parents[1]/"008-evaluate.py")
metrics=importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics)


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main(a):
    lock=json.loads((a.share/"prediction-lock.json").read_text("utf8"))
    assert all(digest(a.work/(n+".png"))==h for n,h in lock["mask_sha256"].items())
    pred={n: metrics.read(a.work/(n+".png")) for n in lock["mask_sha256"]}
    assert (sum(pred[n].astype("uint8") for n in metrics.PRIMARY)==1).all()
    section=(a.reference.parent/"REVIEW-AND-FREEZE.md").read_text("utf8").split("### "+a.reference.name)[1].split("### asset-")[0]
    frozen=dict(re.findall(r"\| ([^|]+?) \| `([0-9a-f]{64})` \|",section))
    ref={}
    for n in [*metrics.PRIMARY,"uncertain"]:
        path=a.reference/(n+".png")
        assert frozen[path.name]==digest(path),path
        ref[n]=metrics.read(path)
    landmarks_path=a.reference/"landmarks.json"
    assert frozen[landmarks_path.name]==digest(landmarks_path)
    landmarks=json.loads(landmarks_path.read_text("utf8"))
    h,w=pred["skirt"].shape
    y,x=np.ogrid[:h,:w]
    truth_hair=ref["hair-left"]|ref["hair-right"]
    hair=pred["semantic-hair"]
    summary=dict(accepted_if_all=0.9,manual_interventions=0,truth_pngs_verified=True,
                 direct=dict(all_semantic_hair_pixels=int(hair.sum()),movable_hair_coverage=metrics.divide((hair & truth_hair).sum(),truth_hair.sum()),
                 hair_overlap_with_fixed=int((hair&ref["fixed"]).sum()),all_hair_ground_truth="unavailable: fixed hair is mixed with fixed non-hair",
                 bottomwear_vs_skirt_iou=metrics.iou(pred["semantic-bottomwear"],ref["skirt"])),parts={})
    # Attribute false negatives to the eligible semantic owner, using locked visible outputs.
    sources={r["name"]:np.asarray(Image.open(a.work/"semantic-visible"/r["file"]))>0 for r in lock["layers_front_to_back"]}
    sources["background"]=pred["background"]
    error_sheet=Image.new("RGB",(810,520),"white")
    for i,n in enumerate(metrics.PARTS):
        m,t=pred[n],ref[n]
        values=metrics.metric(m,t,ref["uncertain"],ref["fixed"])
        fn=t & ~m
        fp=m & ~t
        values["fn_by_semantic_owner"]={k:int((fn&v).sum()) for k,v in sources.items() if (fn&v).any()}
        values["fp_by_true_class"]={k:int((fp&ref[k]).sum()) for k in metrics.PRIMARY if (fp&ref[k]).any()}
        if n!="skirt":
            root=landmarks[n+"-root"]; rx,ry=root["x"],root["y"]
            window=(x-rx)**2+(y-ry)**2<=32**2
            pxy=metrics.root_xy(m)
            values["root32"]=dict(reference_xy=[rx,ry],prediction_top_xy=pxy,
                distance_px=float(np.hypot(pxy[0]-rx,pxy[1]-ry)) if pxy else None,
                iou=metrics.iou(m&window,t&window),fp=int((fp&window).sum()),fn=int((fn&window).sum()))
        summary["parts"][n]=values
        im=np.full((h,w,3),26,np.uint8)
        im[m&t]=(107,196,126);im[fp]=(248,90,76);im[fn]=(65,167,248)
        error_sheet.paste(Image.fromarray(im).resize((270,480),Image.Resampling.NEAREST),(270*i,26))
        ImageDraw.Draw(error_sheet).text((270*i+5,6),n,fill="black")
    ImageDraw.Draw(error_sheet).text((5,506),"green TP | red FP | blue FN",fill="black")
    error_sheet.save(a.share/"errors.png")
    (a.share/"evaluation.json").write_text(json.dumps(summary,indent=2),encoding="utf8")
    print(a.reference.name,[(n,v["iou"]) for n,v in summary["parts"].items()])


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for key in ["work","share","reference"]:
        p.add_argument(key,type=Path)
    main(p.parse_args())
