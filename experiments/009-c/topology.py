"""Medial-axis tree of completed hair; no image-coordinate cuts in branch ownership."""
import math
import networkx as nx
import numpy as np
import cv2
from scipy import ndimage as nd
from scipy.spatial import cKDTree
from skimage.morphology import skeletonize


def topology(mask,face):
    h,w=mask.shape
    small=cv2.resize(mask.astype("uint8"),(w//2,h//2),interpolation=cv2.INTER_AREA)>0
    small=nd.binary_closing(small,iterations=2)
    radius=nd.distance_transform_edt(small)
    sk=skeletonize(small)
    coords=np.array(np.nonzero(sk)).T
    ys,xs=np.nonzero(face)
    axis=np.array([np.median(ys)/2,np.median(xs)/2])
    scale=max(6,(xs.max()-xs.min()+1)/2)
    ids={tuple(p):i for i,p in enumerate(coords)}
    graph=nx.Graph()
    graph.add_nodes_from(range(len(coords)))
    for i,(y,x) in enumerate(coords):
        for dy,dx in [(0,1),(1,-1),(1,0),(1,1)]:
            j=ids.get((y+dy,x+dx))
            if j is not None:graph.add_edge(i,j,weight=math.hypot(dy,dx))
    rad=radius[tuple(coords.T)]
    crown=int(np.argmax(rad-np.linalg.norm(coords-axis,axis=1)*0.30))
    main=nx.node_connected_component(graph,crown)
    tree=cKDTree(coords[list(sorted(main))])
    main_ids=np.array(sorted(main))
    bridges=[]
    for comp in list(nx.connected_components(graph)):
        if crown in comp or len(comp)<4:continue
        seq=np.array(sorted(comp))
        distances,indices=tree.query(coords[seq])
        k=int(distances.argmin())
        if distances[k]<=scale*0.35:
            u,v=int(seq[k]),int(main_ids[indices[k]])
            graph.add_edge(u,v,weight=float(distances[k])+1)
            bridges.append([u,v])
    dist,paths=nx.single_source_dijkstra(graph,crown)
    ends=[i for i in dist if graph.degree(i)==1 and dist[i]>scale*.75 and coords[i,0]>coords[crown,0]]
    candidates=[]
    for tip in ends:
        path=paths[tip]; points=coords[path]; length=np.array([dist[i] for i in path])
        if len(path)<7:continue
        unit=max(3,int(round(scale*.15)))
        best=None
        for j in range(2,len(path)-2):
            if length[j]<scale*.25 or length[-1]-length[j]<scale*.40:continue
            lo=max(0,j-unit);hi=min(len(path)-1,j+unit)
            a=points[j]-points[lo];b=points[hi]-points[j]
            bend=1-np.dot(a,b)/max(1,np.linalg.norm(a)*np.linalg.norm(b))
            neck=(min(max(rad[path[lo:j+1]]),max(rad[path[j:hi+1]]))-rad[path[j]])/max(1,rad[path[j]])
            separation=np.linalg.norm(points[j]-coords[crown])/scale
            score=neck+0.25*bend+0.20*min(1,separation)-0.15*length[j]/length[-1]
            if best is None or score>best[0]:best=(float(score),j)
        if best:
            score,j=best
            candidates.append(dict(tip=tip,root=path[j],parent=path[j-1],score=score,
              rank=score+min(3,(length[-1]-length[j])/scale),path=path[j:]))
    # Anchor identity is the order of root coordinates. Favor opposite departing branches.
    pairs=[]
    for i,a in enumerate(candidates):
        for b in candidates[i+1:]:
            if set(a["path"])&set(b["path"]):continue
            spread=abs(coords[a["root"],1]-coords[b["root"],1])/scale
            if spread==0:continue
            pairs.append((a["rank"]+b["rank"]+min(2,spread),i,candidates.index(b)))
    selected=[]
    if pairs:
        _,i,j=max(pairs)
        selected=sorted([candidates[i],candidates[j]],key=lambda c:coords[c["root"],1])
    assignment=np.zeros(len(coords),np.uint8)
    tangent=np.zeros((len(coords),2),np.float32)
    for v,path in paths.items():
        for k,c in enumerate(selected,1):
            if c["root"] in path:
                assignment[v]=k
                tangent[v]=coords[v]-coords[path[max(0,len(path)-6)]]
    near=nd.distance_transform_edt(~sk,return_distances=False,return_indices=True)
    grid=np.zeros(sk.shape,np.int32);grid[tuple(coords.T)]=np.arange(len(coords))
    nearest=grid[tuple(near)]
    labels=cv2.resize(assignment[nearest],(w,h),interpolation=cv2.INTER_NEAREST)*mask
    direction=cv2.resize(tangent[nearest],(w,h),interpolation=cv2.INTER_NEAREST)
    def xy(i):return [int(coords[i,1]*2+1),int(coords[i,0]*2+1)]
    roots=[dict(id=c["root"],xy=xy(c["root"]),tip=xy(c["tip"]),neck_score=c["score"],
                rank=c["rank"],confidence=float(1/(1+math.exp(-c["score"]))),selected=c in selected) for c in candidates]
    return labels,direction,roots,dict(crown=crown,nodes=[xy(i) for i in range(len(coords))],edges=list(graph.edges),
        bridges=bridges,tree_parent={i:path[-2] for i,path in paths.items() if len(path)>1},
        node_owner=assignment.tolist()),{side:dict(root_xy=xy(c["root"]),points=[xy(i) for i in c["path"]])
        for side,c in zip(("hair-left","hair-right"),selected)}
