"""Ground-truth-free root selection; use the original C ownership for every hypothesis."""
import argparse,hashlib,json,shutil
from itertools import combinations
from pathlib import Path
import cv2
import networkx as nx
import numpy as np
from scipy import ndimage as nd
from PIL import Image

TAU=0.025
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding="utf-8-sig"))
def dump(p,x):p.write_text(json.dumps(x,indent=1),encoding="utf8")
def binary(p):return np.asarray(Image.open(p))>0
def mean(vals):return float(np.mean(vals))
def gradient(rgb):
    gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY).astype("float32")
    return np.clip(np.hypot(cv2.Sobel(gray,-1,1,0),cv2.Sobel(gray,-1,0,1))/255,0,1)
def travel(seq,xy):
    return float(np.linalg.norm(np.diff(xy[seq],axis=0),axis=1).sum())
def smooth(seq,xy):
    v=np.diff(xy[seq][::3],axis=0)
    if len(v)<2:return 0.5
    v=v/np.maximum(1,np.linalg.norm(v,axis=1))[:,None]
    return float((1+(v[:-1]*v[1:]).sum(1).mean())/2)

def predict(base,dst):
    repo=base/"StandRig";prior=repo/"results/009-semantic-hair-segmentation"
    inputs={};locks={};validity={};clusters={};pairlog={};stability={};decisions={}
    def pin(p):
        inputs[p.relative_to(base).as_posix()]=sha(p);return p
    for ii in (1,2):
        key=f"{ii:02}";c=prior/f"009-C/predictions/asset-{key}";local=base/f"b009/pred-{key}"
        rgb=np.array(Image.open(pin(repo/f"source_00{ii+6}/original.png")).convert("RGB"))
        grads=[gradient(x) for x in (rgb,cv2.GaussianBlur(rgb,(3,3),0.8),cv2.convertScaleAbs(rgb,alpha=0.97,beta=3))]
        graph=read(pin(c/"hair-graph.json"));cand=read(pin(c/"root-candidates.json"));xy=np.array(graph["nodes"])
        parent={int(k):v for k,v in graph["tree_parent"].items()};crown=graph["crown"]
        visible=binary(pin(c/"C/visible-hair.png"));h,w=visible.shape;full=np.zeros_like(visible)
        for p in sorted((local/"completed").glob("*-hair.png")):
            full|=np.asarray(Image.open(pin(p)).getchannel("A"))>=128
        face=binary(pin(next((local/"semantic-visible").glob("*-face.png"))))
        fy,fx=np.nonzero(face);xmin,xmax,ymin,ymax=fx.min(),fx.max(),fy.min(),fy.max();scale=float(xmax-xmin+1)
        def rect_distance(point):
            x,y=point
            return float(np.hypot(max(0,xmin-x,x-xmax),max(0,ymin-y,y-ymax))/scale)
        def chain(i):
            seq=[i]
            while seq[-1] in parent:seq.append(parent[seq[-1]])
            return seq[::-1]
        chains=[chain(i) for i in range(len(xy))]
        ids={tuple(p):i for i,p in enumerate(xy)}
        roots=sorted(set(ca["id"] for ca in cand))
        groupgraph=nx.Graph();groupgraph.add_nodes_from(roots)
        for a,b in combinations(roots,2):
            if np.linalg.norm(xy[a]-xy[b])/scale<=.06:groupgraph.add_edge(a,b)
        groups=[sorted(nodes) for nodes in nx.connected_components(groupgraph)]
        group_of={n:i for i,group in enumerate(groups) for n in group}
        x,y=(xy//2).T;sk=np.zeros((h//2,w//2),bool);sk[y,x]=True
        near=nd.distance_transform_edt(~sk,return_distances=False,return_indices=True)
        grid=np.zeros(sk.shape,int);grid[y,x]=np.arange(len(xy));nearest=grid[tuple(near)]
        surface={};subtree={};rows={}
        for root in roots:
            nodes=np.array([root in seq for seq in chains]);subtree[root]=set(np.flatnonzero(nodes))
            surface[root]=cv2.resize(nodes[nearest].astype("uint8"),(w,h),interpolation=cv2.INTER_NEAREST).astype(bool)&full
            paths=[]
            for ca in (ca for ca in cand if ca["id"]==root):
                tip=ids[tuple(ca["tip"])];seq=chains[tip];route=seq[seq.index(root):]
                length=travel(route,xy);up=travel(chains[root],xy);px,py=xy[route].T
                paths.append(dict(tip=tip,nodes=route,extent=length/scale,prox=up/max(1,up+length),
                                  continuity=smooth(route,xy),visible=mean(visible[py,px]),neck=float(ca["neck_score"]),C_rank=ca["rank"]))
            best=max(paths,key=lambda t:(t["visible"]+t["continuity"]+min(1,t["extent"]),t["extent"]))
            gap=rect_distance(xy[root]);head=any(rect_distance(xy[j])<=.5 for j in chains[root])
            near_head=1/(1+gap);area=surface[root].sum()/scale**2
            ok=bool(head and gap<=1 and min(t["prox"] for t in paths)<=.80 and area>0 and best["extent"]>0)
            score=mean([near_head,1-min(t["prox"] for t in paths),min(1,area),min(1,best["extent"]),
                        np.clip(max(t["neck"] for t in paths),0,1),best["continuity"]])
            rows[root]=dict(root=root,xy=xy[root].tolist(),cluster=group_of[root],head_connected=head,face_gap_widths=gap,
                crown_fraction_min=min(t["prox"] for t in paths),downstream_area_head_units=area,paths=paths,
                tip=best["tip"],valid=ok,score=score,reasons=[k for k,fail in
                [("outside_head_neighborhood",gap>1),("no_head_connection",not head),("distal",min(t["prox"] for t in paths)>.80),("no_downstream",area==0)] if fail])
        representatives=[max(gr,key=lambda n:(rows[n]["valid"],rows[n]["score"],-n)) for gr in groups]
        clusters[key]=dict(groups=groups,representatives=representatives,scale=scale)
        validity[key]=list(rows.values())
        original=tuple(sorted({ca["id"] for ca in cand if ca["selected"]},key=lambda n:xy[n,0]))
        base_masks=[binary(pin(c/f"C/{n}.png")) for n in ("hair-left","hair-right")]
        skirt=pin(c/"C/skirt.png")
        def masks(pair):
            l,r=pair
            return [surface[l]&visible&~surface[r],surface[r]&visible]
        assert all(np.array_equal(a,b) for a,b in zip(masks(original),base_masks))
        pairs={};cm=dst/f"candidate-masks/{key}";cm.mkdir(parents=True)
        for one,two in combinations(roots,2):
            if xy[one,0]==xy[two,0]:continue
            l,r=sorted((one,two),key=lambda n:xy[n,0]); pair=(l,r)
            compatible=[(a,b) for a in rows[l]["paths"] for b in rows[r]["paths"] if not set(a["nodes"])&set(b["nodes"])]
            if not compatible:continue
            old=max(a["C_rank"]+b["C_rank"]+min(2,abs(xy[l,0]-xy[r,0])/scale) for a,b in compatible)
            a,b=max(compatible,key=lambda ab:sum(t["visible"]+t["continuity"]+min(1,t["extent"]) for t in ab))
            ms=masks(pair);overlap=len(subtree[l]&subtree[r])/max(1,len(subtree[l]|subtree[r]))
            up1,up2=set(chains[l]),set(chains[r]);diverge=1-len(up1&up2)/max(1,len(up1|up2))
            e2=mean([1/(1+rows[l]["face_gap_widths"]),1/(1+rows[r]["face_gap_widths"]),1-overlap,diverge,
                       a["visible"],b["visible"],int(group_of[l]!=group_of[r])])
            sides=[]
            for n,t,m,baseline in zip(pair,(a,b),ms,base_masks):
                area=int(m.sum());support=area/max(1,int(surface[n].sum()));edge=bool(m[0].any() or m[-1].any() or m[:,0].any() or m[:,-1].any())
                ratio=area/max(1,int(baseline.sum()));boundary=m&~nd.binary_erosion(m)
                slices=nd.find_objects(m.astype("uint8"));roi=m[slices[0]] if slices else np.zeros((1,1),bool)
                count,_,stats,_=cv2.connectedComponentsWithStats(roi.astype("uint8"),8)
                connected=float(stats[1:,4].max()/area) if area else 0.
                holes=int((nd.binary_fill_holes(roi)&~roi).sum())
                intrusion=float((face&m).sum()/max(1,area))
                sides.append(dict(pixels=area,edge_contact=edge,area_vs_C=ratio,contours=[mean(g[boundary]) if area else 0 for g in grads],
                    visible_support=support,largest_fraction=connected,holes=holes,intrusion=intrusion,flow=t["continuity"],
                    path_visible=t["visible"],connectivity=int(t["nodes"][0]==n),collapse=bool(ratio<.2 and not edge)))
            q=[]
            for idx in range(3):
                value=mean([mean([s["contours"][idx],s["visible_support"],s["largest_fraction"],s["flow"],s["path_visible"],s["connectivity"],
                    1-s["holes"]/max(1,s["holes"]+s["pixels"]),1-s["intrusion"]]) for s in sides])
                q.append(value-.5*overlap-float(any(s["collapse"] for s in sides)))
            name=f"{l}-{r}"
            Image.fromarray(ms[0].astype("uint8")+ms[1].astype("uint8")*2).save(cm/(name+".png"))
            pairs[name]=dict(ids=pair,tips=[a["tip"],b["tip"]],old=old,e1=mean([rows[l]["score"],rows[r]["score"]]),e2=e2,e3=q,
                eligible=all(rows[n]["valid"] and n in representatives for n in pair) and group_of[l]!=group_of[r],
                downstream_overlap=overlap,upstream_divergence=diverge,sides=sides)
        baseline="-".join(map(str,original));assert baseline in pairs
        hi=max(v["old"] for v in pairs.values());lo=min(v["old"] for v in pairs.values())
        winners={"baseline":baseline}; audits={}
        for method in ["E1","E2","E3","combined"]:
            order=[]
            for idx in range(3):
                scores={}
                for name,v in pairs.items():
                    if method in ("E1","combined") and not v["eligible"]:continue
                    comp={"E1":v["e1"],"E2":v["e2"],"E3":v["e3"][idx]}
                    score=mean(list(comp.values())) if method=="combined" else comp[method]
                    scores[name]=score+.25*(v["old"]-lo)/max(1e-9,hi-lo)
                order.append(sorted(scores.items(),key=lambda kv:(-kv[1],kv[0])))
            choices=[o[0][0] if o else None for o in order];win=choices[0]
            margin=order[0][0][1]-order[0][1][1] if len(order[0])>=2 else None
            audits[method]=dict(winners=choices,rankings=order,margin=margin,stable=len(set(choices))==1)
            winners[method]=win
        win=winners["combined"];audit=audits["combined"];reason=[]
        if win is None:reason.append("no_feasible_pair")
        else:
            if audit["margin"] is not None and audit["margin"]<TAU:reason.append("small_margin")
            if not audit["stable"]:reason.append("perturbation_changed_winner")
            if any(s["collapse"] for s in pairs[win]["sides"]):reason.append("side_collapse")
        winners["auto"]=baseline if reason else win
        decisions[key]=dict(baseline=baseline,raw=win,auto=winners["auto"],diagnostic_confirmed=None if reason else win,
                            fallback=bool(reason),reasons=reason)
        pairlog[key]=pairs;stability[key]=audits
        for name,choice in winners.items():
            out=dst/f"predictions/{key}/{name}";out.mkdir(parents=True)
            labs=masks(pairs[choice]["ids"]) if choice else [np.zeros_like(visible)]*2
            for n,m in zip(("hair-left","hair-right"),labs):Image.fromarray(m.astype("uint8")*255).save(out/(n+".png"))
            shutil.copyfile(skirt,out/"skirt.png")
            for p in out.iterdir():locks[p.relative_to(dst).as_posix()]=sha(p)
    for n,v in [("root-validity",validity),("candidate-clusters",clusters),("pair-evaluation",pairlog),("selection-stability",stability),("fallback-decisions",decisions)]:dump(dst/(n+".json"),v)
    dump(dst/"prediction-lock.json",dict(formal="auto",inputs=inputs,code=sha(Path(__file__)),rules=sha(dst/"rules.txt"),masks=locks,
         decisions=sha(dst/"fallback-decisions.json"),pairs=sha(dst/"pair-evaluation.json"),candidate_masks={p.relative_to(dst).as_posix():sha(p) for p in (dst/"candidate-masks").rglob("*.png")}))

if __name__=="__main__":
    base=Path(__file__).resolve().parents[3]
    predict(base,base/"StandRig/results/009-semantic-hair-segmentation/009-E")
