exec(open('work/explore.py').read().split('for sig')[0])
from scipy.optimize import least_squares
base=b[0].reshape(17,9,2); off=base[:,:,0]-60
E=np.unique(np.sort(np.array(r['parts'][0]['artMesh']['triangles']).reshape(-1,3)[:,[[0,1],[1,2],[2,0]]].reshape(-1,2),axis=1),axis=0); rest=np.linalg.norm(b[0,E[:,1]]-b[0,E[:,0]],axis=-1)
# geometry parametrized by scalar original tip signal; no time-dependent branch
s=(old[:480,0,148,0]-60)/np.max(np.abs(old[:480,0,148,0]-60)); samples=np.linspace(s.min(),s.max(),9)
def geom(z,signals):
 al,rot,le,wi=z.reshape(4,16); ss=np.asarray(signals)[:,None]; lengths=15*(1+le*ss**2)
 center=np.stack([np.c_[np.zeros(len(ss)),np.cumsum(np.sin(al*ss)*lengths,axis=1)]+60,np.c_[np.zeros(len(ss)),np.cumsum(np.cos(al*ss)*lengths,axis=1)]],axis=-1)
 an=np.c_[np.zeros(len(ss)),rot*ss]; width=np.c_[np.ones(len(ss)),1+wi*ss**2]
 return np.stack([center[:,:,None,0]+np.cos(an[:,:,None])*off*width[:,:,None],center[:,:,None,1]-np.sin(an[:,:,None])*off*width[:,:,None]],axis=-1).reshape(-1,153,2)
def fun(z):
 a=geom(z,samples); ra=np.linalg.norm(a[:,E[:,1]]-a[:,E[:,0]],axis=-1)/rest
 al,ro,le,wi=z.reshape(4,16); cl=np.sum(1+le[:,None]*samples**2,axis=0)/16
 travel=np.ptp(a[:,148,0]);
 return np.r_[np.maximum(.902-ra,0).ravel()*100,np.maximum(ra-1.098,0).ravel()*100,np.maximum(.972-cl,0)*100,np.maximum(cl-1.028,0)*100,max(0,151-travel)*2,np.diff(al,2)*.05,np.diff(ro,2)*.05,le*.005,wi*.005]
z=np.r_[.4*(np.arange(16)+.5)/16+.16,.4*np.arange(1,17)/16,np.zeros(32)]
res=least_squares(fun,z,max_nfev=250,ftol=1e-9,xtol=1e-9,gtol=1e-9)
a=geom(res.x,s); print(res.cost,res.nfev,stats(a,0));print('center',np.sum(1+res.x.reshape(4,16)[2,:,None]*s**2,axis=0).min()/16,np.sum(1+res.x.reshape(4,16)[2,:,None]*s**2,axis=0).max()/16)
json.dump(res.x.tolist(),open('work/hair-parameters.json','w')); np.save('work/hair.npy',a)
