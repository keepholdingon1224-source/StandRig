"""D2 chooses a root-to-tip route and propagates identity to connected branches."""
import networkx as nx
import numpy as np
from features import unit

def trace(method,pair,g,xy,parent,crown,color,normal,vis,bridges):
    graph=g.copy()
    for u,v,edge in graph.edges(data=True):
        d=xy[v]-xy[u]; orient=abs(unit(d)@((normal[u]+normal[v])/2))
        cost=1+2*np.abs(color[u]-color[v]).mean()/255+orient+1-(float(vis[u])+float(vis[v]))/2
        cost+=int(tuple(sorted((u,v))) in bridges)
        edge.update(cost=float(np.linalg.norm(d)*cost),weight=float(np.linalg.norm(d)*cost))
    if method=="A":father=dict(parent)
    else:
        paths=nx.single_source_dijkstra_path(graph,crown,weight="cost")
        father={i:p[-2] for i,p in paths.items() if len(p)>1}
    anchors={};reports=[]
    for side,row in enumerate(sorted(pair,key=lambda c:c["xy"][0]),1):
        root=row["id"];tip=row["tip_id"]
        local=graph.copy()
        if root in parent:local.remove_node(parent[root])
        candidates=[row["path"]]
        if method!="A":
            candidates.append(nx.shortest_path(local,root,tip,weight="cost"))
        if method=="C":
            for _ in range(2):
                for u,v in zip(candidates[-1],candidates[-1][1:]):local[u][v]["weight"]*=3
                candidates.append(nx.shortest_path(local,root,tip,weight="weight"))
        candidates=list(dict.fromkeys(map(tuple,candidates)))
        def score(p):
            vectors=np.diff(xy[list(p)],axis=0)
            lens=np.linalg.norm(vectors,axis=1);dirs=vectors/lens[:,None]
            bend=(1-(dirs[1:]*dirs[:-1]).sum(axis=1)).mean() if len(dirs)>1 else 0
            cost=sum(graph[u][v]["cost"] for u,v in zip(p,p[1:]))
            return float(cost/lens.sum()+bend+0.2*lens.sum()/max(1,np.linalg.norm(xy[tip]-xy[root])))
        best=min(candidates,key=score) if method=="C" else candidates[-1]
        reports.append(dict(side=side,root=root,tip=tip,candidates=[dict(nodes=p,cost=score(p)) for p in candidates],selected=best))
        for i in best:anchors.setdefault(i,side)
        anchors[root]=side
    owners=np.zeros(len(xy),dtype=np.uint8)
    for i in g:
        j=i
        while j not in anchors and j in father:j=father[j]
        owners[i]=anchors.get(j,0)
    return owners,reports
