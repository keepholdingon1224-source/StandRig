import hashlib,json,shutil
from pathlib import Path
import cv2,networkx as nx,numpy as np
from PIL import Image
from scipy import ndimage as nd
from ranking import select
from paths import trace
from ownership import assign,graph_cost
from features import orientation
R=Path(__file__).resolve().parents[2];E=R/"results/009-semantic-hair-segmentation";D=E/"009-D"
def read(p):return json.loads(p.read_text(encoding="utf-8-sig"))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,indent=1),encoding="utf8")
variants={"baseline":("old","A","nearest"),"root":("new","A","nearest"),"ownership":("old","A","geo"),
          "both":("new","A","geo"),"pathB":("new","B","geo"),"formal":("new","C","geo")}
inputs={};masks={};rankings={};pathlog={};ownership={};diagnostics=read(D/"graph-diagnostics.json")
def record(p):
    inputs[p.relative_to(R.parent).as_posix()]=sha(p)
    return p
for i in ("01","02"):
    c=E/f"009-C/predictions/asset-{i}"
    candidates=read(record(c/"root-candidates.json"));g=read(record(c/"hair-graph.json"))
    xy=np.array(g["nodes"]);parent={int(k):v for k,v in g["tree_parent"].items()}
    graph=nx.Graph();graph.add_nodes_from(range(len(xy)));graph.add_edges_from(g["edges"])
    visible=np.asarray(Image.open(record(c/"C/visible-hair.png")))>0
    skirt=record(c/"C/skirt.png");shape=visible.shape
    full=np.zeros(shape,bool)
    for p in sorted((R.parent/f"b009/pred-{i}/completed").glob("*-hair.png")):
        full|=np.asarray(Image.open(record(p)).getchannel("A"))>=128
    assert not (visible&~full).any()
    small=cv2.resize(full.astype("uint8"),(shape[1]//2,shape[0]//2),interpolation=cv2.INTER_AREA)>0
    small=nd.binary_closing(small,iterations=2);radius=nd.distance_transform_edt(small)
    source=np.asarray(Image.open(record(R/f"source_00{6+int(i)}/original.png")).convert("RGB"))
    rgb=cv2.resize(source,(small.shape[1],small.shape[0]),interpolation=cv2.INTER_AREA).astype(np.float32)
    norm,edge=orientation(rgb);vv=cv2.resize(visible.astype("uint8"),(small.shape[1],small.shape[0]),interpolation=cv2.INTER_NEAREST)>0
    x,y=(xy//2).T;v=vv[y,x];colors=rgb[y,x];normal=norm[y,x]
    ranks=select(candidates,xy,parent,g["crown"],radius[y,x],colors,normal,v)
    rankings[i]=ranks
    ids,sparse=graph_cost(small,rgb,norm,edge,vv)
    pathlog[i]={};ownership[i]={}
    diagnostics[i].update(bridge_candidates=g["bridges"],branch_nodes=[k for k,n in graph.degree() if n>2],
                          endpoint_nodes=[k for k,n in graph.degree() if n==1],mean_image_edge_at_nodes=float(edge[y,x].mean()))
    for name,(roots,method,assignment) in variants.items():
        pair=[r for r in ranks if r["selected" if roots=="new" else "old_selected"]]
        owners,paths=trace(method,pair,graph,xy,parent,g["crown"],colors,normal,v,{tuple(sorted(e)) for e in g["bridges"]})
        labels=assign(assignment,owners,xy,visible,small,ids,sparse,radius)
        out=D/f"predictions/{i}/{name}";out.mkdir(parents=True,exist_ok=False)
        for k,n in enumerate(["hair-left","hair-right"],1):
            mask=(labels==k)
            if name=="baseline":assert np.array_equal(mask,np.asarray(Image.open(record(c/f"C/{n}.png")))>0)
            Image.fromarray(mask.astype("uint8")*255).save(out/(n+".png"))
        shutil.copyfile(skirt,out/"skirt.png")
        for p in out.iterdir():masks[p.relative_to(D).as_posix()]=sha(p)
        pathlog[i][name]=paths
        ownership[i][name]=dict(left=int((labels==1).sum()),right=int((labels==2).sum()),
                fixed_visible_hair=int((visible&(labels==0)).sum()),excluded_from_evaluation=0)
dump(D/"graph-diagnostics.json",diagnostics);dump(D/"root-ranking.json",rankings);dump(D/"path-comparison.json",pathlog);dump(D/"ownership-analysis.json",ownership)
code={p.relative_to(R).as_posix():sha(p) for p in Path(__file__).parent.glob("*.py") if p.name not in ("evaluate.py","integrity.py")}
dump(D/"prediction-lock.json",dict(code=code,inputs=inputs,masks=masks,variants=variants,config=sha(D/"preregistered-methods.txt"),formal="formal"))
