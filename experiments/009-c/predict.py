"""Formal predictor. Inputs are source RGB and 009-B aligned layer PNGs only."""
import argparse,hashlib,json,os
from pathlib import Path
import cv2
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from topology import topology


def dump(path,obj):
    path.write_text(json.dumps(obj,indent=1),encoding="utf8")


def composite(canvas,rgb,alpha):
    return canvas*(1-alpha)+rgb*alpha


def photo(source,hair,other,alpha_h,alpha_o,composed):
    def gpu(im):
        return torch.from_numpy(im).to(device="cuda",dtype=torch.float32).permute(2,0,1)[None]
    def smooth(x,n):return F.avg_pool2d(x,n,stride=1,padding=n//2,count_include_pad=False)
    original=gpu(source)
    def cost(im):
        delta=gpu(im)-original
        color=delta.abs().mean(1,keepdim=True)
        edges=(delta[:,:,:,1:]-delta[:,:,:,:-1]).abs().mean(1,keepdim=True)
        dy=(delta[:,:,1:]-delta[:,:,:-1]).abs().mean(1,keepdim=True)
        return .5*color+.5*smooth(color,5)+.5*smooth(F.pad(edges,(0,1))+F.pad(dy,(0,0,0,1)),3)
    hair_top=hair+(1-alpha_h)*other
    other_top=other+(1-alpha_o)*hair
    delta=(cost(other_top)-cost(hair_top))[0,0].cpu().numpy()
    baseline=cost(composed)[0,0].cpu().numpy()
    return delta,baseline


def run(a):
    assert torch.cuda.device_count()==1 and "3060 Ti" in torch.cuda.get_device_name()
    src=np.asarray(Image.open(a.source).convert("RGB"),dtype=np.float32)
    h,w=src.shape[:2]
    visible=np.zeros((h,w),bool);face=visible.copy()
    completed=visible.copy(); skirt=visible.copy();othermask=visible.copy();alternative_skirt=visible.copy()
    prem=[np.zeros_like(src) for _ in range(2)]
    opacity=[np.zeros((h,w,1),np.float32) for _ in range(2)]
    full=np.zeros_like(src)
    for path in sorted((a.layers/"completed").glob("*.png")):
        name=path.stem.split("-",1)[1]
        image=np.array(Image.open(path).convert("RGBA"))
        rgb=image[:,:,:3].astype(np.float32);alpha=image[:,:,3:].astype(np.float32)/255
        hair=name in ("front-hair","back-hair");g=int(hair)
        full=composite(full,rgb,alpha)
        prem[g]=composite(prem[g],rgb,alpha);opacity[g]+=alpha*(1-opacity[g])
        hard=image[:,:,3]>=128
        if hair:completed|=hard
        else:
            othermask|=hard
            alternative_skirt[hard]=name=="bottomwear"
        ownership=np.asarray(Image.open(a.layers/"semantic-visible"/path.name))>0
        if hair:visible|=ownership
        if name=="face":face=ownership
        if name=="bottomwear":skirt=ownership
    branch,dr,roots,graph,lines=topology(completed,face)
    a.out.mkdir(parents=True,exist_ok=False)
    for name,data in [("root-candidates",roots),("hair-graph",graph),("centerlines",lines)]:dump(a.out/(name+".json"),data)
    margin,error=photo(src,prem[1],prem[0],opacity[1],opacity[0],full)
    overlap=completed&othermask
    b=(visible&~(overlap&(margin< -4)))|(overlap&(margin>4))
    yy,xx=np.indices((h,w),dtype=np.float32)
    norm=np.maximum(1,np.linalg.norm(dr,axis=2))
    votes=margin.copy()
    count=np.ones_like(margin)
    for sign in (-1,1):
        mx=xx+sign*8*dr[:,:,1]/norm;my=yy+sign*8*dr[:,:,0]/norm
        neighbor=cv2.remap(branch,mx,my,cv2.INTER_NEAREST)
        evidence=cv2.remap(margin,mx,my,cv2.INTER_LINEAR)
        same=(branch>0)&(neighbor==branch)
        votes+=np.where(same,evidence,0);count+=same
    extra=overlap&(branch>0)&(margin>1)&(votes/count>4)
    c=b|extra
    pins={}
    for method,owner in [("A",visible),("B",b),("C",c)]:
        folder=a.out/method;folder.mkdir()
        masks={"hair-left":owner&(branch==1),"hair-right":owner&(branch==2),
               "skirt":(skirt&~owner)|(visible&~owner&alternative_skirt)}
        pins[method]={}
        for name,m in {**masks,"visible-hair":owner}.items():
            path=folder/(name+".png");Image.fromarray(m.astype(np.uint8)*255).save(path)
            pins[method][name]=hashlib.sha256(path.read_bytes()).hexdigest()
        assert np.all(sum(m.astype("uint8") for m in masks.values())<=1)
    dump(a.out/"occlusion-analysis.json",dict(baseline_overlap_pixels=int(overlap.sum()),mean_recomposition_cost_on_overlap=float(error[overlap].mean()),
        B_restored=int((b&~visible).sum()),B_removed=int((visible&~b).sum()),C_added_over_B=int((c&~b).sum()),
        completed_hair_pixels=int(completed.sum()),not_visible_C=int((completed&~c).sum()),gpu=torch.cuda.get_device_name(),uuid=os.environ["CUDA_VISIBLE_DEVICES"]))
    dump(a.out/"lock.json",pins)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for key in ["source","layers","out"]:p.add_argument(key,type=Path)
    run(p.parse_args())
