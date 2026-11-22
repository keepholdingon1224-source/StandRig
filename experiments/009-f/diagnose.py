"""Isolated oracle intervention on asset 02. Never imported by inference."""
from predict import Asset,R,P,D,parts,read,save,binary,np,nx,Image,sha
a=Asset('02')
ref=R/'results/008-segmentation-accuracy/reference/asset-02'
land=read(ref/'landmarks.json')
truth=[binary(ref/(n+'.png')) for n in parts[:2]]
points=[np.array([land[n+'-root'][k] for k in ['x','y']]) for n in parts[:2]]
roots=[min((n for n,r in a.rows.items() if r['valid']),key=lambda n:np.linalg.norm(a.xy[n]-pt)) for pt in points]
def measure(ms):
    return [dict(pixels=int(m.sum()),iou=float((m&t).sum()/(m|t).sum())) for m,t in zip(ms,truth)]
name='-'.join(map(str,roots))
f=P/f'009-E/candidate-masks/02/{name}.png'
if f.exists():
    labels=np.asarray(Image.open(f));selected=[labels==1,labels==2]
else:
    l,r=map(a.region,roots);selected=[l&~r,r]
base=[]
for n in parts[:2]:base.append(binary(P/f'009-E/predictions/02/auto/{n}.png'))
linked,paths=a.connect(roots,a.baseline,base)
pair=a.e_pairs.get(name)
report=dict(asset='02',scope='oracle only; same nearest valid E candidate per GT landmark in all three conditions',
 roots=roots,xy=a.xy[roots].tolist(),errors=[float(np.linalg.norm(a.xy[n]-pt)) for n,pt in zip(roots,points)],
 recorded_E_pair=pair is not None,eligible=pair['eligible'] if pair else False,
 condition1_descendants=measure(selected),condition2_keep_region=measure(base),condition3_connect=measure(linked),paths=paths,
 predictor_sha_before_oracle=sha(R/'experiments/009-f/predict.py'))
save(D/'root-vs-region-diagnostic.json',report)
print({k:v for k,v in report.items() if k!='paths'})
ranks=read(P/'009-E/selection-stability.json')['02']['combined']['rankings'][0]
report.update(E_rank=next(j for j,(key,_) in enumerate(ranks,1) if key==name),E_pairs_ranked=len(ranks),
 conclusion='Combined ranking and descendant ownership. The near pair was eligible but lower-ranked. Moving just the landmarks leaves the mask unchanged; reassigning descendants reduces both IoUs, especially right. Connecting against a preserved region improves left and slightly reduces right against the E baseline.')
save(D/'root-vs-region-diagnostic.json',report)
