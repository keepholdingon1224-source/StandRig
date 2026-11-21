"""Check the two PSDs, their part metadata, decoded layers, and the source transform."""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from psd_tools import PSDImage


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f,"sha256").hexdigest()


def validate(source, output):
    name = source.stem
    layers_dir = output/name
    rgba = np.array(Image.open(source).convert("RGBA"))
    h,w = rgba.shape[:2]
    side=max(h,w)
    px,py=(side-w)//2,(side-h)//2
    padded=np.zeros((side,side,4),np.uint8)
    padded[py:py+h,px:px+w]=rgba
    expected=cv2.resize(padded,(1024,1024),interpolation=cv2.INTER_AREA)
    observed=np.array(Image.open(layers_dir/"src_img.png").convert("RGBA"))
    matches=bool(np.array_equal(expected,observed))
    parts=json.loads((output/(name+".psd.json")).read_text(encoding="utf-8-sig"))["parts"]
    errors=[] if matches else ["Source transform pixel mismatch"]
    tags=["front hair","back hair","head","neck","neckwear","topwear","handwear","bottomwear","legwear","footwear",
          "tail","wings","objects","headwear","face","irides","eyebrow","eyewhite","eyelash","eyewear","ears",
          "earwear","nose","mouth"]
    raw={}
    for tag in tags:
        image=Image.open(layers_dir/(tag+".png"))
        depth_size=None
        if tag!="head":
            depth=Image.open(layers_dir/(tag+"_depth.png"))
            depth.load()
            depth_size=depth.size
        alpha=np.array(image.getchannel("A"))
        raw[tag]=dict(size=image.size,depth_size=depth_size,alpha_over_15=int((alpha>15).sum()),in_psd=tag in parts)
        if image.size!=(1024,1024) or (tag!="head" and depth_size!=(1024,1024)):
            errors.append(tag+" raster size")
        expected_in_psd = tag!="head" and int((alpha[:-102,:-102]>10).sum())>4
        if expected_in_psd != (tag in parts):errors.append(tag+" alpha eligibility and manifest differ")
    documents=[]
    for filename in [name+".psd",name+"_depth.psd"]:
        path=output/filename
        psd=PSDImage.open(path)
        rows=[]
        if psd.size!=(1024,1024):errors.append(filename+" canvas size")
        for layer in psd:
            tag=layer.name
            box=list(layer.bbox)
            if tag not in parts:
                errors.append("unexpected layer "+tag)
                continue
            im=layer.topil()
            im.load()
            x,y,r,b=box
            valid=0<=x<r<=1024 and 0<=y<b<=1024 and im.size==(r-x,b-y) and box==parts[tag]["xyxy"]
            if not valid:errors.append(filename+" invalid geometry: "+tag)
            alpha_matches=None
            if filename==name+".psd" and valid and tag in raw:
                canvas_alpha=np.array(Image.open(layers_dir/(tag+".png")).getchannel("A"))
                if "A" in im.getbands():
                    decoded=np.array(im.getchannel("A"))
                    alpha_matches=bool(np.array_equal(decoded>10,canvas_alpha[y:b,x:r]>10))
                    if not alpha_matches:errors.append(tag+" PSD alpha does not match the positioned raw layer")
                else:
                    errors.append(tag+" missing PSD alpha channel")
            rows.append(dict(name=tag,box=box,mode=im.mode,alpha_matches=alpha_matches,
                source_box_unclipped=[x*side/1024-px,y*side/1024-py,r*side/1024-px,b*side/1024-py]))
        names=[r["name"] for r in rows]
        if len(names)!=len(parts) or set(names)!=set(parts):errors.append(filename+" layer list mismatch")
        documents.append(dict(file=filename,sha256=sha(path),size=psd.size,layers=rows))
    if [r["name"] for r in documents[0]["layers"]]!=[r["name"] for r in documents[1]["layers"]]:
        errors.append("layer order mismatch")
    if not parts:errors.append("empty PSD")
    return dict(pass_gate=not errors,errors=errors,source_hash=sha(source),source_wh=[w,h],pad_xy=[px,py],
                canvas_scale=1024/side,source_image_pixel_exact=matches,raw=raw,documents=documents)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for key in ["source","output","result"]:
        p.add_argument(key,type=Path)
    a=p.parse_args()
    result=validate(a.source,a.output)
    a.result.write_text(json.dumps(result,indent=2),encoding="utf8")
    print("Gate 5",result["pass_gate"],result["errors"])
