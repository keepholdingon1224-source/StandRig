"""D3 competitive geodesic propagation on completed hair, clamped to frozen visible hair."""
import numpy as np
import cv2
from scipy import ndimage as nd
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

def graph_cost(mask,rgb,normal,edge,visible):
    ids=np.full(mask.shape,-1,int);ids[mask]=np.arange(mask.sum())
    yy,xx=np.nonzero(mask);h,w=mask.shape
    rows=[];cols=[];costs=[]
    for dy,dx in [(1,0),(0,1),(1,1),(1,-1)]:
        y=yy+dy;x=xx+dx
        keep=(y>=0)&(x>=0)&(y<h)&(x<w)
        a,b,c,d=yy[keep],xx[keep],y[keep],x[keep]
        keep=mask[c,d];a,b,c,d=(v[keep] for v in (a,b,c,d))
        length=np.hypot(dx,dy)
        drift=np.abs(normal[a,b,0]*dx+normal[a,b,1]*dy)/length
        weight=1+3*np.abs(rgb[a,b]-rgb[c,d]).mean(axis=1)/255+2*np.minimum(1,(edge[a,b]+edge[c,d])/128)+drift+(visible[a,b]!=visible[c,d])
        rows.extend([ids[a,b],ids[c,d]]);cols.extend([ids[c,d],ids[a,b]]);costs.extend([weight*length,weight*length])
    return ids,coo_matrix((np.concatenate(costs),(np.concatenate(rows),np.concatenate(cols))),shape=(mask.sum(),)*2).tocsr()

def assign(method,owners,xy,visible,small,ids,graph,radius):
    points=xy//2;x,y=points.T;grid=np.zeros(small.shape,np.uint8);grid[y,x]=owners
    sk=np.zeros_like(small);sk[y,x]=True
    distance,nearest=nd.distance_transform_edt(~sk,return_indices=True)
    seed=tuple(nearest)
    if method=="nearest":out=grid[seed]
    else:
        costs=[]
        for k in range(3):
            starts=ids[y[owners==k],x[owners==k]];starts=starts[starts>=0]
            costs.append(dijkstra(graph,indices=starts,min_only=True) if len(starts) else np.full(small.sum(),np.inf))
        fixed,left,right=costs
        labels=np.where(left<right,1,2)
        moving=(np.minimum(left,right)*1.05<fixed)&(distance[small]<=2*radius[seed][small]+2)
        out=np.zeros_like(grid);out[small]=labels*moving
    return cv2.resize(out,(visible.shape[1],visible.shape[0]),interpolation=cv2.INTER_NEAREST)*visible
