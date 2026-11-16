"""Batch periodic spatiotemporal solver on unchanged synthetic StandRig inputs.
No endpoint substitution: periodic convolution is applied to all samples, not a seam patch.
Hair elastic cross-section coefficients fitted once over motion envelope, not per frame.
"""
import json,sys,pathlib,numpy as np
from scipy.optimize import least_squares
from scipy.ndimage import gaussian_filter1d
OUT=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else 'results/005-spatiotemporal-constraints');OUT.mkdir(parents=True,exist_ok=True)
SRC=pathlib.Path('results/005-spatiotemporal-constraints')
r=json.load(open(SRC/'source-fixture.srig.json')); old=np.array([[[[v['x'],v['y']] for v in p] for p in f] for f in json.load(open(SRC/'baseline-geometry.json'))]); b=np.array([[[v['x'],v['y']] for v in p['artMesh']['vertices']] for p in r['parts']])
def save(n,obj): (OUT/n).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
def edges(p):
 tri=np.array(r['parts'][p]['artMesh']['triangles']).reshape(-1,3)
 return np.unique(np.sort(tri[:,[[0,1],[1,2],[2,0]]].reshape(-1,2),axis=1),axis=0)
E=edges(0);rest=np.linalg.norm(b[0,E[:,1]]-b[0,E[:,0]],axis=-1);off=b[0,:,0].reshape(17,9)-60
s=(old[:480,0,148,0]-60)/np.max(np.abs(old[:480,0,148,0]-60)); samples=np.linspace(s.min(),s.max(),9)
def geom(z,signals):
 al,rot,le,wi=z.reshape(4,16); ss=np.asarray(signals)[:,None]; lengths=15*(1+le*ss**2)
 center=np.stack([np.c_[np.zeros(len(ss)),np.cumsum(np.sin(al*ss)*lengths,axis=1)]+60,np.c_[np.zeros(len(ss)),np.cumsum(np.cos(al*ss)*lengths,axis=1)]],axis=-1)
 an=np.c_[np.zeros(len(ss)),rot*ss];width=np.c_[np.ones(len(ss)),1+wi*ss**2]
 return np.stack([center[:,:,None,0]+np.cos(an[:,:,None])*off*width[:,:,None],center[:,:,None,1]-np.sin(an[:,:,None])*off*width[:,:,None]],axis=-1).reshape(-1,153,2)
def fit(target):
 def fun(z):
  a=geom(z,samples);ra=np.linalg.norm(a[:,E[:,1]]-a[:,E[:,0]],axis=-1)/rest
  al,ro,le,wi=z.reshape(4,16);cl=np.sum(1+le[:,None]*samples**2,axis=0)/16;travel=np.ptp(a[:,148,0])
  return np.r_[np.maximum(.902-ra,0).ravel()*100,np.maximum(ra-1.098,0).ravel()*100,np.maximum(.972-cl,0)*100,np.maximum(cl-1.028,0)*100,max(0,target-travel)*2,np.diff(al,2)*.05,np.diff(ro,2)*.05,le*.005,wi*.005]
 z=np.r_[.4*(np.arange(16)+.5)/16+.16,.4*np.arange(1,17)/16,np.zeros(32)]
 result=least_squares(fun,z,max_nfev=250,ftol=1e-9,xtol=1e-9,gtol=1e-9)
 return result,geom(result.x,s)
def monitor(a,p):
 es=edges(p);tri=np.array(r['parts'][p]['artMesh']['triangles']).reshape(-1,3)
 ra=np.linalg.norm(a[:,es[:,1]]-a[:,es[:,0]],axis=-1)/np.linalg.norm(b[p,es[:,1]]-b[p,es[:,0]],axis=-1)
 def cross(v):
  q=v[...,tri,:];u=q[...,1,:]-q[...,0,:];w=q[...,2,:]-q[...,0,:];return u[...,0]*w[...,1]-u[...,1]*w[...,0]
 ar=cross(a)/cross(b[p]);g=a.reshape(-1,17,9,2);dx=np.diff(g,axis=2);dy=np.diff(g,axis=1)
 # signed discrete turning angle / average adjacent segment length (rad/px)
 def curvature(d):
  u=d[...,:-1,:];v=d[...,1:,:];return np.arctan2(u[...,0]*v[...,1]-u[...,1]*v[...,0],np.sum(u*v,axis=-1))/(.5*(np.linalg.norm(u,axis=-1)+np.linalg.norm(v,axis=-1)))
 cur=curvature(dx);vert=curvature(np.swapaxes(dy,1,2));vel=(np.roll(a,-1,axis=0)-a)*60;acc=(np.roll(vel,-1,axis=0)-vel)*60;jerk=(np.roll(acc,-1,axis=0)-acc)*60
 u=dx[:,:16];v=dy[:,:,:8];shear=np.sum(u*v,axis=-1)/(np.linalg.norm(u,axis=-1)*np.linalg.norm(v,axis=-1));res=np.maximum(np.maximum(.9-ra,ra-1.1),0)
 active=(ra<.96)|(ra>1.04);switch=np.any(active!=np.roll(active,1,axis=0),axis=1);speedjump=np.max(np.linalg.norm(np.roll(vel,-1,axis=0)-vel,axis=-1),axis=1)
 worst=np.unravel_index(np.argmax(np.abs(ra-1)),ra.shape);ci=np.unravel_index(np.argmax(np.abs(np.roll(cur,-1,axis=0)-cur)),cur.shape)
 out={'edgeRatio':[float(ra.min()),float(ra.max())],'areaRatio':[float(ar.min()),float(ar.max())],'tipRange':float(np.ptp(a[:,148,0])),'seam30':float(np.max(np.linalg.norm((a[2]-a[0])-(a[0]-a[478]),axis=-1))*30),'maxHemCurvature':float(np.abs(cur[:,-1]).max()),'maxHorizontalCurvature':float(np.abs(cur).max()),'maxVerticalCurvature':float(np.abs(vert).max()),'maxCurvatureTimeDerivative':float(np.abs(np.roll(cur,-1,axis=0)-cur).max()*60),'maxAcceleration':float(np.linalg.norm(acc,axis=-1).max()),'maxJerk':float(np.linalg.norm(jerk,axis=-1).max()),'maxShearCosine':float(np.abs(shear).max()),'maxEdgeAcceptanceResidual':float(res.max()),'edgeBandActiveSwitchFrames':int(switch.sum()),'meanVelocityChangeOnSwitch':float(speedjump[switch].mean()) if switch.any() else 0,'meanVelocityChangeOffSwitch':float(speedjump[~switch].mean()) if (~switch).any() else 0,'worstEdge':{'time':worst[0]/60,'vertices':es[worst[1]].tolist(),'ratio':float(ra[worst])},'worstCurvatureChange':{'time':ci[0]/60,'row':int(ci[1]),'column':int(ci[2])+1},'series':[]}
 for f in range(480):out['series'].append({'t':f/60,'minEdge':float(ra[f].min()),'maxEdge':float(ra[f].max()),'minArea':float(ar[f].min()),'maxArea':float(ar[f].max()),'hemCurvature':float(np.abs(cur[f,-1]).max()),'curvatureDerivative':float(np.abs(cur[(f+1)%480]-cur[f]).max()*60),'maxSpeed':float(np.linalg.norm(vel[f],axis=-1).max()),'maxAcceleration':float(np.linalg.norm(acc[f],axis=-1).max()),'maxJerk':float(np.linalg.norm(jerk[f],axis=-1).max()),'shear':float(np.abs(shear[f]).max()),'residual':float(res[f].max())})
 return out
attempts=[]
for target in [151,148]:
 res,a=fit(target);m=monitor(a,0);attempts.append({'hairTarget':target,'cost':float(res.cost),'nfev':res.nfev,'metrics':{k:v for k,v in m.items() if k!='series'},'parameters':res.x.tolist()})
print('Hair fitted',m['edgeRatio'],m['tipRange'],flush=True)
hair=a;params=res.x
candidates=[]
for sigma,spatial in [(0,0),(2,0),(4,0),(6,0),(6,.65),(8,.65),(12,.65)]:
 a=old[:480,1].copy()
 if sigma:a=gaussian_filter1d(a,sigma,axis=0,mode='wrap',truncate=4)
 if spatial:
  displacement=(a-b[1]).reshape(480,17,9,2);displacement=gaussian_filter1d(displacement,spatial,axis=2,mode='nearest');a=b[1]+displacement.reshape(480,153,2)
 a[:,:9]=b[1,:9];m=monitor(a,1)
 candidates.append({'temporalSigmaFrames':sigma,'spatialSigmaColumns':spatial,'metrics':{k:v for k,v in m.items() if k!='series'}})
 if sigma==6 and spatial==.65:skirt=a.copy()
# Evaluate the periodic operator at t=0..8+1/60. Video samples remain 0..239/30.
final=np.stack([hair,skirt],axis=1);extended=final[np.arange(482)%480]
save('geometry-trace.json',[[[{'x':float(x),'y':float(y)} for x,y in p] for p in f] for f in extended])
save('solver-parameters.json',{'hairCoefficients':params.tolist(),'signal':'004 exact center-tip displacement normalized by max absolute over the converged cycle','hairEnvelopeSamples':samples.tolist(),'skirtTemporalSigmaFrames':6,'skirtSpatialSigmaColumns':.65,'convolution':'normalized Gaussian periodic full-cycle, truncate=4, spatial nearest extension on displacement; fixed top row','physicalInputUnchanged':True,'batchOffline':True})
save('attempts.json',{'hair':attempts,'skirt':candidates})
save('diagnostics.json',{'definitions':{'curvature':'signed adjacent horizontal edge turning angle / mean length, rad/px; hem row v=1','timeDifferences':'periodic central-cycle forward finite differences at 60Hz; acceleration=delta velocity*60, jerk=delta acceleration*60','shear':'absolute cosine between grid horizontal and vertical edges','residual':'positive distance of edge ratio outside acceptance 0.90..1.10','activeSwitch':'monitor only: ratio crosses 004 distance band .96..1.04; correlations do not establish causation','hairWidth':'distance between each row endpoints /120','curvatureLimits':'monitor only, no numeric softness acceptance'},'004':[monitor(old[:480,p],p) for p in range(2)],'005':[monitor(final[:,p],p) for p in range(2)]})
print('Skirt selected',monitor(skirt,1)['edgeRatio'],monitor(skirt,1)['tipRange'],flush=True)
