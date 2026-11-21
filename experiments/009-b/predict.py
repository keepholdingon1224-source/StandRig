"""Prediction reads only source size, original PSD and fixed rule. Output in original coordinates."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw
from psd_tools import PSDImage

EXP = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("official_extract", EXP/"009-run-seethrough.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
NAMES = ["hair-left","hair-right","skirt","fixed","background"]
COLORS = [(247,64,84),(243,184,42),(48,161,250),(113,115,144),(23,24,30)]


def binary(path, mask):
    Image.fromarray(np.uint8(mask)*255).save(path)


def motion(hair, face):
    output = [np.zeros_like(hair), np.zeros_like(hair)]
    y,x=np.nonzero(face)
    parts=[]
    if not len(y):
        return output,dict(face=None,components=parts)
    split=(int(x.min())+int(x.max())+1)/2
    jaw=int(y.max())+1
    candidate=hair.copy()
    candidate[:jaw]=False
    count,labels,stats,_=cv2.connectedComponentsWithStats(candidate.astype("uint8"),8)
    for i in range(1,count):
        left,top,width,height,area=map(int,stats[i])
        side=None
        if top==jaw and left+width-0.5<=split:
            side=0
        elif top==jaw and left+0.5>=split:
            side=1
        if side is not None:
            roi=np.s_[top:top+height,left:left+width]
            output[side][roi] |= labels[roi]==i
        parts.append(dict(bbox=[left,top,width,height],area=area,assigned=None if side is None else NAMES[side]))
    return output,dict(face_mid_x=split,face_bottom=jaw,components=parts)


def main(a):
    a.work.mkdir(parents=True,exist_ok=False)
    a.share.mkdir(parents=True,exist_ok=True)
    psd=PSDImage.open(a.psd)
    assert all(l.is_visible() and l.opacity==255 and l.blend_mode.value==b"norm" for l in psd)
    src=Image.open(a.source).convert("RGBA")
    inv=runner.extract(a.psd,a.source,a.work)
    assert inv["original_size"]==list(src.size)
    layers=inv["layers_front_to_back"]
    blank=np.zeros((src.height,src.width),bool)
    masks={row["name"]:np.asarray(Image.open(a.work/"semantic-visible"/row["file"]))>0 for row in layers}
    owned=np.logical_or.reduce(list(masks.values()))
    hair=masks.get("front hair",blank)|masks.get("back hair",blank)
    (left,right),geometry=motion(hair,masks.get("face",blank))
    skirt=masks.get("bottomwear",blank)
    primary=[left,right,skirt,owned&~(left|right|skirt),~owned]
    assert np.all(sum(x.astype("uint8") for x in primary)==1)
    for label,mask in zip(NAMES+["semantic-hair","semantic-bottomwear"],primary+[hair,skirt]):
        binary(a.work/(label+".png"),mask)
    h=runner.digest
    pins={n:h(a.work/(n+".png")) for n in NAMES+["semantic-hair","semantic-bottomwear"]}
    source_hash=h(a.source)
    composite=Image.new("RGBA",src.size)
    for row in reversed(layers):
        img=Image.open(a.work/"completed"/row["file"])
        alpha=np.array(img.getchannel("A"))
        row["alpha_histogram_0_to_255"]=np.bincount(alpha.ravel(),minlength=256).tolist()
        composite=Image.alpha_composite(composite,img)
        if row["name"] in ("front hair","back hair","bottomwear"):
            img.save(a.share/(row["name"].replace(" ","-")+".png"))
    inv.update(psd_sha256=h(a.psd),source_sha256=source_hash,geometry=geometry,mask_sha256=pins,
               rules_sha256=h(a.rules),predictor_sha256=h(Path(__file__)),extract_sha256=h(Path(runner.__file__)),
               manual_inputs=0)
    (a.share/"prediction-lock.json").write_text(json.dumps(inv,indent=2),encoding="utf8")
    def thumb(im):
        bg=Image.new("RGBA",src.size,(245,245,245,255))
        return Image.alpha_composite(bg,im.convert("RGBA")).convert("RGB").resize((270,480),Image.Resampling.LANCZOS)
    preview=Image.fromarray(np.asarray(COLORS,dtype="uint8")[np.argmax(np.stack(primary),axis=0)])
    preview.resize((360,640),Image.Resampling.NEAREST).save(a.share/"visible-mask.png")
    sheet=Image.new("RGB",(810,510),"white")
    for i,(title,im) in enumerate([("Source",src),("PSD recomposition",composite),("50% overlay",Image.blend(thumb(src),thumb(composite),.5))]):
        sheet.paste(thumb(im) if i<2 else im,(270*i,25));ImageDraw.Draw(sheet).text((270*i+6,5),title,fill="black")
    sheet.save(a.share/"recomposition.png")
    stack=Image.new("RGB",(480,25*(len(layers)+1)),"white")
    draw=ImageDraw.Draw(stack)
    draw.text((6,4),"Front to back | PSD bounds | owned pixels",fill="black")
    for i,row in enumerate(layers):
        draw.text((6,27+i*25),f"{i+1:02}  {row['name']:16}  {row['bounds_in_psd']}   {row['visible_pixels']}",fill="black")
    stack.save(a.share/"stack.png")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for key in ["psd","source","work","share","rules"]:
        p.add_argument(key,type=Path)
    main(p.parse_args())
