"""Independent array-based spatial/temporal diagnostics, no solver imports."""
import json,pathlib,numpy as np
O=pathlib.Path('results/006-gui-playback');B=pathlib.Path('results/005-spatiotemporal-constraints');rig=json.load(open(B/'source-fixture.srig.json'));reported=json.load(open(B/'diagnostics.json'));records={};checks=[]
for key,path in [('003',pathlib.Path('results/003-secondary-loop')),('004',pathlib.Path('results/004-deformation-constraints')),('005',O)]:
 if key=='003':continue # 003 geometry is independently covered by JS common-definition checks
 g=np.array([[[[v['x'],v['y']] for v in p] for p in f] for f in json.load(open(path/('evaluated-geometry.json' if key=='005' else 'geometry-trace.json')))])[:480];records[key]=[]
 for p in range(2):
  a=g[:,p].reshape(480,17,9,2);dx=a[:,:,1:]-a[:,:,:-1];dy=a[:,1:]-a[:,:-1]
  def curve(edges):
   x=edges[...,:-1,:];y=edges[...,1:,:];turn=np.arctan2(x[...,0]*y[...,1]-x[...,1]*y[...,0],np.einsum('...i,...i->...',x,y));return turn/((np.sqrt((x*x).sum(-1))+np.sqrt((y*y).sum(-1)))/2)
  h=curve(dx);v=curve(dy.transpose(0,2,1,3));dt=lambda x:np.concatenate([np.diff(x,axis=0),x[:1]-x[-1:]],axis=0)*60
  vel=dt(a);acc=dt(vel);jerk=dt(acc);width=np.linalg.norm(a[:,:,-1]-a[:,:,0],axis=-1)/120 if p==0 else np.linalg.norm(a[:,:,-1]-a[:,:,0],axis=-1)/240
  monitor={'maxHemCurvature':float(np.max(np.abs(h[:,-1]))),'maxHorizontalCurvature':float(np.max(np.abs(h))),'maxVerticalCurvature':float(np.max(np.abs(v))),'maxCurvatureTimeDerivative':float(np.max(np.abs(dt(h)))),'maxAcceleration':float(np.max(np.linalg.norm(acc,axis=-1))),'maxJerk':float(np.max(np.linalg.norm(jerk,axis=-1)))}
  for name,value in monitor.items():
   expected=reported[key][p][name];assert abs(value-expected)<1e-7,(key,p,name,value,expected)
  # Quarter/half/hem lag at dominant frequency from the unchanged cycle.
  signal=a[:,:,:,0].mean(axis=2);harmonic=np.fft.rfft(signal-signal.mean(axis=0),axis=0)[1];ph=np.angle(harmonic);lag=((ph[4]-ph[16]+np.pi)%(2*np.pi)-np.pi)/(2*np.pi)*8
  hphase=np.angle(np.fft.rfft(a[:,-1,:,0]-a[:,-1,:,0].mean(axis=0),axis=0)[1]);hlag=((hphase[-1]-hphase[0]+np.pi)%(2*np.pi)-np.pi)/(2*np.pi)*8
  records[key].append({**monitor,'widthRatio':[float(width.min()),float(width.max())],'maxVerticalCurvatureTimeDerivative':float(np.max(np.abs(dt(v)))),'quarterToHemFundamentalLagSeconds':float(lag),'leftToRightHemFundamentalLagSeconds':float(hlag),'dominantTipFrequencyHz':float(np.argmax(np.abs(np.fft.rfft(a[:,-1,4,0]-a[:,-1,4,0].mean()))[1:])+1)/8})
  checks.append({'name':key+':'+rig['parts'][p]['id']+':independent-monitoring','pass':True})
(O/'monitor-verification.json').write_text(json.dumps({'pass':True,'checks':checks,'parts':records,'evaluation':'005 label denotes 006 evaluated geometry, compared with fixed 005 diagnostics','limits':'Curvature is mesh centerline curvature, not the painted scalloped texture silhouette. Phase lag describes response, not proof of material propagation. No added numeric softness acceptance.'},indent=2)+'\n');print('PASS independent curvature/acceleration/jerk checks; width and lag measured')
