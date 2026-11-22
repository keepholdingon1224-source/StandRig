"""Structural inference. Only explicit training-free asset 01 and 02 inputs."""
from pathlib import Path
import hashlib,json,itertools,shutil
import numpy as np
import networkx as nx
import cv2
from PIL import Image
from scipy import ndimage as nd
R=Path(__file__).resolve().parents[2]
P=R/'results/009-semantic-hair-segmentation'
D=P/'009-F'
parts=['hair-left','hair-right','skirt']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.write_text(json.dumps(x,indent=1,allow_nan=False),encoding='utf8')
def binary(p):return np.asarray(Image.open(p))>0
class Asset:
    def __init__(self,i):
        self.inputs={}
        def pin(p):
            self.inputs[p.relative_to(R.parent).as_posix()]=sha(p)
            return p
        c=P/f'009-C/predictions/asset-{i}'
        local=R.parent/f'b009/pred-{i}'
        self.rgb=np.array(Image.open(pin(R/('source_007' if i=='01' else 'source_008')/'original.png')).convert('RGB'))
        gray=cv2.cvtColor(self.rgb,cv2.COLOR_RGB2GRAY)
        self.grad=np.clip(np.hypot(cv2.Sobel(gray,cv2.CV_32F,1,0),cv2.Sobel(gray,cv2.CV_32F,0,1))/255,0,1)
        g=read(pin(c/'hair-graph.json'))
        self.xy=xy=np.array(g['nodes'])
        self.parent={int(k):v for k,v in g['tree_parent'].items()}
        self.crown=g['crown']
        self.tree=nx.DiGraph((v,k) for k,v in self.parent.items())
        self.graph=nx.Graph()
        self.graph.add_edges_from(g['edges'])
        self.visible=binary(pin(c/'C/visible-hair.png'))
        self.base=[binary(pin(c/f'C/{n}.png')) for n in parts[:2]]
        self.skirt=pin(c/'C/skirt.png')
        self.full=np.zeros_like(self.visible)
        for p in sorted((local/'completed').glob('*-hair.png')):
            self.full |= np.array(Image.open(pin(p)).getchannel('A'))>=128
        self.face=binary(pin(next((local/'semantic-visible').glob('*-face.png'))))
        y,x=np.nonzero(self.face)
        self.center=np.array([(x.min()+x.max())/2,(y.min()+y.max())/2])
        self.scale=float(np.ptp(x)+1)
        self.axes=np.array([self.scale,float(np.ptp(y)+1)])
        x,y=(xy//2).T
        grid=np.full((1024,576),-1,np.int32);grid[y,x]=np.arange(len(xy))
        near=nd.distance_transform_edt(grid<0,return_distances=False,return_indices=True)
        self.near=cv2.resize(grid[tuple(near)],(1152,2048),interpolation=cv2.INTER_NEAREST)
        width=cv2.distanceTransform(self.full.astype('uint8'),cv2.DIST_L2,5)
        self.width=width[xy[:,1],xy[:,0]]
        self.rows={v['root']:v for v in read(pin(P/'009-E/root-validity.json'))[i]}
        self.e_pairs=read(pin(P/'009-E/pair-evaluation.json'))[i]
        self.e_dec=read(pin(P/'009-E/fallback-decisions.json'))[i]
        self.baseline=list(map(int,self.e_dec['baseline'].split('-')))
        for a,b in self.graph.edges:
            samples=np.linspace(xy[a],xy[b],9).round().astype(int)
            xx,yy=samples.T
            length=np.linalg.norm(xy[a]-xy[b])
            self.graph[a][b]['cost']=length*(1+self.grad[yy,xx].mean()+2*(1-self.full[yy,xx].mean())+abs(self.width[a]-self.width[b])/(1+length))
    def region(self,n):
        nodes=nx.descendants(self.tree,n)|{n}
        lut=np.zeros(len(self.xy),bool);lut[list(nodes)]=True
        return lut[self.near]&self.full&self.visible
    def distal(self):
        candidates=[]
        for tip in self.tree:
            if self.tree.out_degree(tip):continue
            route=nx.shortest_path(self.tree,self.crown,tip)
            ellipse=np.linalg.norm((self.xy[route]-self.center)/self.axes,axis=1)
            # Distal core begins after the last exit from the head envelope.
            inside=np.flatnonzero(ellipse<=.85)
            start=int(inside[-1]+1) if inside.size else 0
            tail=route[start:]
            if len(tail)<2:continue
            coords=self.xy[tail];segments=np.diff(coords,axis=0)
            length=np.linalg.norm(segments,axis=1).sum()
            straight=np.linalg.norm(coords[-1]-coords[0])/max(length,1)
            vis=self.visible[coords[:,1],coords[:,0]].mean()
            score=np.log1p(length/self.scale)*(.5+.25*straight+.25*vis)*np.log1p(1+np.median(self.width[tail]))
            candidates.append(dict(anchor=tail[0],tip=tip,score=float(score),length=float(length),path=tail))
        options=[]
        for a,b in itertools.combinations(candidates,2):
            if set(a['path'])&set(b['path']):continue
            separation=np.linalg.norm(self.xy[a['anchor']]-self.xy[b['anchor']])/self.scale
            options.append((min(a['score'],b['score'])+.3*max(a['score'],b['score'])+min(1,separation),a,b))
        if not options:return candidates,None
        _,a,b=max(options,key=lambda x:x[0])
        return candidates,sorted([a,b],key=lambda v:self.xy[v['anchor'],0])
    def attachments(self):
        # Use E's structural exclusions and independent clusters. Score local geometry only.
        rows={}
        for n,r in self.rows.items():
            p=self.xy[n];direction=(p-self.center)/self.axes
            collar=1/(1+abs(np.linalg.norm(direction)-.65))
            neck=max(t['neck'] for t in r['paths'])
            convergence=max(t['continuity'] for t in r['paths'])
            rows[n]=dict(xy=p.tolist(),valid=r['valid'],collar=float(collar),neck=float(neck),flow=convergence,
                         score=float((collar+np.clip(neck,0,1)+convergence+1-r['crown_fraction_min'])/4))
        orders=[]
        for image in (self.rgb,cv2.GaussianBlur(self.rgb,(3,3),.8),cv2.convertScaleAbs(self.rgb,alpha=.97,beta=3)):
            gray=cv2.cvtColor(image,cv2.COLOR_RGB2GRAY)
            grad=np.clip(np.hypot(cv2.Sobel(gray,cv2.CV_32F,1,0),cv2.Sobel(gray,cv2.CV_32F,0,1))/255,0,1)
            grouped={}
            for a,b in itertools.combinations(rows,2):
                ra,rb=self.rows[a],self.rows[b]
                if not (ra['valid'] and rb['valid']) or ra['cluster']==rb['cluster']:continue
                left,right=sorted([a,b],key=lambda n:self.xy[n,0])
                if not self.xy[left,0]<self.center[0]<self.xy[right,0]:continue
                support=[]
                for n in [left,right]:
                    x,y=self.xy[n];k=max(1,round(.04*self.scale))
                    support.append(float(grad[max(0,y-k):y+k+1,max(0,x-k):x+k+1].mean()))
                score=(rows[a]['score']+rows[b]['score'])/2+.1*np.mean(support)
                key=tuple(sorted([ra['cluster'],rb['cluster']]))
                if key not in grouped or score>grouped[key][0]:grouped[key]=(float(score),[left,right])
            orders.append(sorted(grouped.values(),key=lambda t:-t[0]))
        return rows,orders
    def connect(self,roots,anchors,masks):
        paths=[];added=[]
        for j,(root,target) in enumerate(zip(roots,anchors)):
            route=nx.shortest_path(self.graph,root,target,weight='cost')
            paths.append(route)
            # Add a bounded medial corridor; truncate at a strong original-image edge.
            corridor=np.zeros(self.full.shape,np.uint8)
            for n in route:
                x,y=self.xy[n];radius=max(1,round(float(self.width[n])))
                cv2.circle(corridor,(int(x),int(y)),radius,1,-1)
            support=corridor.astype(bool)&self.full&self.visible&~self.face
            passable=support&(self.grad<.8)
            seeds=np.zeros_like(passable)
            px,py=self.xy[route].T;seeds[py,px]=True
            component=nd.binary_propagation(seeds&passable,mask=passable)
            added.append(component&~masks[1-j])
        overlap=added[0]&added[1]
        return [m|(a&~overlap) for m,a in zip(masks,added)],paths
def run():
    logs={k:{} for k in ['distal-hair-candidates','attachment-candidates','connection-paths','boundary-analysis','selections']}
    inputs={};locks={}
    for i in ['01','02']:
        a=Asset(i);inputs.update(a.inputs)
        candidates,selected=a.distal()
        rows,orders=a.attachments()
        baseline=a.baseline
        roots=orders[0][0][1] if orders[0] else baseline
        reasons=list(a.e_dec['reasons'])
        if not orders[0]:reasons.append('no eligible attachments')
        if any(len(o)>1 and o[0][0]-o[1][0]<.025 for o in orders):reasons.append('attachment margin')
        if any(o and o[0][1]!=roots for o in orders):reasons.append('unstable pair')
        if selected:
            anchors=[v['anchor'] for v in selected]
            distal=[a.region(n) for n in anchors]
            # Association by minimum total graph cost; keep left/right root labels.
            perm=min(itertools.permutations(range(2)),key=lambda p:sum(nx.shortest_path_length(a.graph,r,anchors[k],weight='cost') for r,k in zip(roots,p)))
            anchors=[anchors[k] for k in perm];distal=[distal[k] for k in perm]
            raw,paths=a.connect(roots,anchors,distal)
        else:
            anchors=[];distal=[np.zeros_like(a.visible) for _ in range(2)];raw=distal;paths=[];reasons.append('no distal pair')
        for m,c in zip(raw,a.base):
            if m.sum()<.2*c.sum() and not (m[0].any() or m[-1].any() or m[:,0].any() or m[:,-1].any()):reasons.append('side collapse')
        # Distal-only attribution is ordered independently, by the distal anchors.
        original_order=[a.region(v['anchor']) for v in selected] if selected else distal
        modes={'baseline':(a.base,baseline),'F1':(original_order,baseline),'F2':(a.base,roots),'F1_F2':(original_order,roots),
               'F1_F2_F3':(raw,roots),'auto':(a.base,baseline) if reasons else (raw,roots)}
        logs['selections'][i]={}
        for mode,(ms,ids) in modes.items():
            assert not (ms[0]&ms[1]).any() and all(not (m&~a.visible).any() for m in ms)
            dest=D/'predictions'/i/mode;dest.mkdir(parents=True,exist_ok=True)
            for n,m in zip(parts,ms):Image.fromarray(m.astype('uint8')*255).save(dest/(n+'.png'))
            shutil.copyfile(a.skirt,dest/'skirt.png')
            logs['selections'][i][mode]=[a.xy[n].tolist() for n in ids]
            for n in parts:
                p=dest/(n+'.png');locks[p.relative_to(D).as_posix()]=sha(p)
        logs['distal-hair-candidates'][i]=dict(candidates=candidates,selected=selected)
        logs['attachment-candidates'][i]=dict(candidates=rows,rankings=orders)
        logs['connection-paths'][i]=dict(roots=roots,anchors=anchors,paths=paths)
        logs['boundary-analysis'][i]=dict(fallback=bool(reasons),reasons=reasons,raw_pixels=[int(m.sum()) for m in raw],
            added=[int((m&~x).sum()) for m,x in zip(raw,distal)],visible_violations=0,overlap=0)
    for k,v in logs.items():save(D/(k+'.json'),v)
    save(D/'prediction-lock.json',dict(code=sha(Path(__file__)),inputs=inputs,masks=locks,
        records={k+'.json':sha(D/(k+'.json')) for k in logs}))
if __name__=='__main__':run()

