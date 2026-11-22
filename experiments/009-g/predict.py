"""009-G, reference-free narrow-band reclassification on two named development assets."""
from pathlib import Path
import hashlib,json,shutil
import cv2
import numpy as np
from PIL import Image
from scipy import ndimage as nd
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import maximum_flow,breadth_first_order
R=Path(__file__).resolve().parents[2]
P=R/'results/009-semantic-hair-segmentation'
D=P/'009-G'
PARTS=('hair-left','hair-right','skirt')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=1,allow_nan=False),encoding='utf8')
def dist(m):return cv2.distanceTransform((~m).astype('uint8'),cv2.DIST_L2,5)
def save_mask(p,m):
    p.parent.mkdir(parents=True,exist_ok=True)
    Image.fromarray(m.astype('uint8')*255).save(p)
def cut(image,band,prior,unary):
    """Integer s-t cut on the free pixels, including Potts terms to fixed neighbours."""
    y,x=np.nonzero(band);n=len(y)
    if not n:return prior.copy()
    ids=np.full(prior.shape,-1,np.int32);ids[y,x]=np.arange(n)
    yes=100*unary[y,x];no=100*(1-unary[y,x])
    starts=[];ends=[];caps=[]
    for dy,dx in ((-1,0),(1,0),(0,-1),(0,1)):
        yy=np.clip(y+dy,0,prior.shape[0]-1);xx=np.clip(x+dx,0,prior.shape[1]-1)
        penalty=48*np.exp(-np.mean(abs(image[y,x]-image[yy,xx]),axis=1)/16)
        nbr=ids[yy,xx];free=nbr>=0
        starts.append(np.flatnonzero(free));ends.append(nbr[free]);caps.append(penalty[free])
        yes+=penalty*(~free)*prior[yy,xx];no+=penalty*(~free)*(~prior[yy,xx])
    starts.extend([np.full(n,n),np.arange(n)]);ends.extend([np.arange(n),np.full(n,n+1)]);caps.extend([yes,no])
    graph=coo_matrix((np.rint(np.concatenate(caps)).astype(np.int32),(np.concatenate(starts),np.concatenate(ends))),shape=(n+2,n+2)).tocsr()
    residual=graph-maximum_flow(graph,n,n+1).flow;residual.eliminate_zeros()
    reached=breadth_first_order(residual,n,return_predecessors=False)
    label=prior.copy();label[y,x]=False
    k=reached[reached<n];label[y[k],x[k]]=True
    return label
class Asset:
    def __init__(self,i):
        self.inputs={}
        def pin(p):
            self.inputs[p.relative_to(R.parent).as_posix()]=sha(p);return p
        def mask(p):return np.array(Image.open(pin(p)))>0
        c=P/f'009-C/predictions/asset-{i}'
        self.base=[mask(c/f'C/{n}.png') for n in PARTS[:2]]
        self.visible=mask(c/'C/visible-hair.png');self.skirt=pin(c/'C/skirt.png')
        self.lines=json.loads(pin(c/'centerlines.json').read_text())
        self.rgb=np.array(Image.open(pin(R/('source_007' if i=='01' else 'source_008')/'original.png')).convert('RGB'))
        comp=Image.new('RGBA',(1152,2048))
        hair=comp.copy();clothing=np.zeros(self.visible.shape,bool)
        for p in sorted((R.parent/f'b009/pred-{i}/completed').glob('*.png')):
            layer=Image.open(pin(p)).convert('RGBA')
            comp=Image.alpha_composite(comp,layer)
            if '-hair.' in p.name:hair=Image.alpha_composite(hair,layer)
            alpha=np.asarray(layer)[:,:,3]>=128
            if 'face.' in p.name:self.face=alpha
            if 'front-hair.' in p.name:self.front=alpha
            if 'wear.' in p.name:clothing |= alpha
        self.comp=np.asarray(comp).astype('float32');self.hair=np.asarray(hair).astype('float32')
        self.other=clothing|(~self.visible)
        self.w=max(3,round(.065*(np.ptp(np.where(self.face)[1])+1)))
    def classify(self,rgb,j):
        prior=self.base[j];visible=self.visible;w=self.w
        allowed=visible&~self.base[1-j]
        outer=dist(prior);inner=dist(~prior)
        band=allowed&(outer<=w)&(inner<=w)
        image=rgb.astype('float32')
        residual=np.mean(abs(self.comp[:,:,:3]-image),axis=2)
        hair_error=np.mean(abs(self.hair[:,:,:3]-image),axis=2)
        match=np.exp(-hair_error/48)*(self.hair[:,:,3]/255)
        residual_support=np.clip((residual-hair_error)/64,-1,1)
        # Flow alignment of the direction to the nearest established tuft spine
        # with the image structure tensor tangent.
        pts=self.lines[PARTS[j]]['points'];spine=np.zeros(prior.shape,np.uint8)
        cv2.polylines(spine,[np.array(pts,np.int32)],False,1,1)
        near=nd.distance_transform_edt(spine==0,return_distances=False,return_indices=True)
        yy,xx=np.indices(prior.shape,dtype=np.float32)
        vx=near[1]-xx;vy=near[0]-yy;length=np.maximum(1,np.hypot(vx,vy));vx/=length;vy/=length
        gray=cv2.cvtColor(image,cv2.COLOR_RGB2GRAY)
        gx=cv2.Sobel(gray,-1,1,0);gy=cv2.Sobel(gray,-1,0,1)
        blur=lambda a:cv2.GaussianBlur(a,(7,7),1.5)
        cross=np.sqrt(np.maximum(0,(blur(gx*gx)*vx*vx+2*blur(gx*gy)*vx*vy+blur(gy*gy)*vy*vy)/(1+blur(gx*gx+gy*gy))))
        conduct=np.exp(-cross)*np.exp(-length/(4*w))
        head=np.exp(-dist(self.face)/(3*w))*(.45+.55*self.front)
        edge=np.clip(np.hypot(gx,gy)/255,0,1)
        # Compare both sides of the interface using independently measured evidence.
        score=np.clip(.25+.28*match+.44*conduct-.28*head+.12*residual_support,0,1)
        local_add=band&(match>.45)&(conduct>.15)&(head<.68)&(edge<.72)&(residual_support>-.3)
        local_del=band&(head>.30)&(conduct<.45)&(edge<.72)&(residual_support<.35)
        growth=nd.binary_propagation(prior,mask=prior|(local_add&(score>.52)))
        plain=cut(image,band,prior,np.clip(.25+.50*match-.23*head+.05*prior,0,1))
        flow=cut(image,band,prior,np.clip(score-.12*residual_support+.05*prior,0,1))
        opt=cut(image,band,prior,np.clip(score+.05*prior,0,1))
        add=opt&growth&~prior;remove=~opt&prior&local_del
        def means(m):
            return {k:(float(np.mean(v[m])) if m.any() else None) for k,v in
                [('image_hair_match',match),('tuft_connectivity',conduct),('composite_error_rgb',residual),('hair_error_rgb',hair_error),('head_fixed_evidence',head),('edge',edge)]}
        signals=dict(boundary=int(band.sum()),likely_movable=int((band&(conduct>.35)&(head<.35)&(match>.5)).sum()),
            likely_fixed=int((band&(head>.45)&(conduct<.35)).sum()),other_interface=int((band&(dist(self.other)<=w)).sum()),
            width=w)
        return dict(growth=growth,cut=plain,flow=flow,residual=opt,B=prior|add,C=prior&~remove,D=(prior|add)&~remove),local_add,local_del,signals,{k:means(m) for k,m in [('added',add),('removed',remove),('band',band)]}
def main():
    inputs={};evidence={};counts={};safety={};changes={};selections={}
    for i in ['01','02']:
        a=Asset(i);inputs.update(a.inputs)
        modes={'A':a.base};local=[];pert=[];evidence[i]=[];counts[i]=[];changes[i]=[]
        for j,b in enumerate(a.base):
            ms,allow,drop,signals,stats=a.classify(a.rgb,j)
            pm,*_=a.classify(cv2.GaussianBlur(a.rgb,(3,3),.65),j)
            pert.append(pm['D']);local.append((allow,drop))
            for mode,m in ms.items():modes.setdefault(mode,[]).append(m)
            for name,m in [('allow-add',allow),('allow-remove',drop),('perturbed',pm['D'])]:
                save_mask(D/f'evidence/{i}/{PARTS[j]}-{name}.png',m)
            evidence[i].append(stats);counts[i].append(signals)
            changes[i].append({k:dict(add=int((m&~b).sum()),remove=int((b&~m).sum())) for k,m in ms.items()})
        # Conflicting additions are ambiguous and remain fixed in every variant.
        for mode,(l,r) in list(modes.items()):
            overlap=l&r
            modes[mode]=[l&~overlap,r&~overlap]
        raw=modes['D'];reasons=[];detail=[]
        for j,(b,m,q) in enumerate(zip(a.base,raw,pert)):
            add=m&~b;rem=b&~m;al,dl=local[j]
            unsupported=int((add&~al).sum()+(rem&~dl).sum())
            ratio=m.sum()/max(1,b.sum());change=add|rem
            diff=int((m^q).sum());stable=diff/max(1,int((change|(b^q)).sum()))
            if unsupported:reasons.append(f'{j}: unsupported local edit')
            if not .75<=ratio<=1.25 or not m.any():reasons.append(f'{j}: area or disappearance')
            if diff>max(8,.002*b.sum()) and stable>.25:reasons.append(f'{j}: perturbation')
            detail.append(dict(area_ratio=float(ratio),unsupported=unsupported,perturbation_pixels=diff,edit_instability=stable))
        touch=lambda l,r:int((cv2.dilate(l.astype('uint8'),np.ones((3,3),np.uint8)).astype(bool)&r).sum())
        if touch(*raw)>touch(*a.base)+a.w:reasons.append('new inter-tuft contact')
        modes['auto']=a.base if reasons else raw
        safety[i]=dict(fallback=bool(reasons),reasons=reasons,sides=detail)
        selections[i]={k:[a.lines[n]['root_xy'] for n in PARTS[:2]] for k in modes}
        for mode,ms in modes.items():
            dest=D/f'predictions/{i}/{mode}'
            for n,m in zip(PARTS,ms):
                assert not (m&~a.visible).any()
                save_mask(dest/(n+'.png'),m)
            shutil.copyfile(a.skirt,dest/'skirt.png')
    logs={'boundary-candidates':counts,'pixel-evidence':evidence,'add-remove-analysis':changes,'safety-decisions':safety,'selections':selections}
    for name,v in logs.items():dump(D/(name+'.json'),v)
    dump(D/'prediction-lock.json',dict(code=sha(Path(__file__)),inputs=inputs,
        masks={p.relative_to(D).as_posix():sha(p) for folder in ['predictions','evidence'] for p in (D/folder).rglob('*.png')},
        records={f'{k}.json':sha(D/f'{k}.json') for k in logs},rules=sha(D/'rules.md')))
if __name__=='__main__':main()
