"""D1 chooses pairs from existing candidate IDs. No new candidate coordinates."""
from itertools import combinations
import numpy as np
from features import unit

def select(candidates,xy,parent,crown,radius,color,normal,vis):
    at={tuple(v):i for i,v in enumerate(xy)}
    records=[]
    for c in candidates:
        root=c["id"];tip=at[tuple(c["tip"])]
        seq=[tip]
        while seq[-1]!=crown:seq.append(parent[seq[-1]])
        seq.reverse();j=seq.index(root);lo=max(0,j-6);hi=min(len(seq)-1,j+6)
        r=radius[seq];v=unit(xy[seq[hi]]-xy[root]);u=unit(xy[root]-xy[seq[lo]])
        drop=np.clip((r[lo:j+1].max()-r[j:hi+1].mean())/max(1,r[lo:j+1].max()),0,1)
        pinch=np.clip((min(r[lo:j+1].max(),r[j:hi+1].max())-r[j])/max(1,r[j]),0,1)
        features=dict(thickness_drop=float(drop),pinch=float(pinch),tangent=float((1+u@v)/2),
           flow=float(1-abs(v@normal[root])),contrast=float(np.abs(color[seq[lo]]-color[seq[hi]]).mean()/255),
           route_support=float(vis[seq[j:]].mean()))
        score=(sum(features.values())+drop+pinch)/8
        records.append(dict(id=root,tip_id=tip,xy=c["xy"],tip_xy=c["tip"],features=features,score=float(score),
            radius=float(r[j]),old_selected=c["selected"],path=seq[j:],old_rank=c["rank"]))
    feasible=[]
    for a,b in combinations(records,2):
        if a["xy"][0]==b["xy"][0] or set(a["path"])&set(b["path"]):continue
        widths=[max(1,v["radius"]) for v in (a,b)]
        feasible.append((a["score"]+b["score"]+min(widths)/max(widths)/8,a,b))
    _,a,b=max(feasible,key=lambda row:row[0])
    for rank,row in enumerate(sorted(records,key=lambda v:-v["score"]),1):
        row["rank"]=rank;row["selected"]=(row is a or row is b)
    return records
