import json,pathlib,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image,ImageDraw
O=pathlib.Path('results/005-spatiotemporal-constraints');d=json.load(open(O/'diagnostics.json'));m=json.load(open(O/'metrics.json'))
fig,axes=plt.subplots(4,2,figsize=(15,13),sharex=True)
for p,name in enumerate(['hair','skirt']):
 for key,color in [('004','tomato'),('005','royalblue')]:
  s=d[key][p]['series'];t=[v['t'] for v in s]
  for row,fields in enumerate([['minEdge','maxEdge'],['minArea','maxArea'],['hemCurvature'],['maxSpeed']]):
   for fld in fields:axes[row,p].plot(t,[v[fld] for v in s],color=color,alpha=.8,label=key+' '+fld,lw=1)
 for row in range(4):axes[row,p].set_title(name+' '+['all edge length ratio','signed triangle area ratio','hem curvature rad/px','max vertex speed px/s'][row]);axes[row,p].legend(fontsize=7);axes[row,p].grid(alpha=.2)
 axes[0,p].axhline(.9,color='gray',ls='--');axes[0,p].axhline(1.1,color='gray',ls='--');axes[3,p].set_xlabel('seconds (unchanged drive phase)')
fig.tight_layout();fig.savefig(O/'timeseries.png',dpi=140);plt.close(fig)
fig,axes=plt.subplots(4,2,figsize=(15,13),sharex=True)
for p,name in enumerate(['hair','skirt']):
 for key,color in [('004','tomato'),('005','royalblue')]:
  s=d[key][p]['series'];t=[v['t'] for v in s]
  for row,fld in enumerate(['curvatureDerivative','maxAcceleration','maxJerk','shear']):axes[row,p].plot(t,[v[fld] for v in s],color=color,label=key,lw=1)
 for row in range(4):axes[row,p].set_title(name+' '+['horizontal curvature time derivative','max acceleration px/s2','max jerk px/s3','absolute grid shear cosine'][row]);axes[row,p].legend();axes[row,p].grid(alpha=.2)
 axes[-1,p].set_xlabel('seconds')
fig.tight_layout();fig.savefig(O/'monitoring-timeseries.png',dpi=140);plt.close(fig)
# Equal camera, equal instant contact sheet and enlarged hem review evidence.
canvas=Image.new('RGB',(1200,4*290),'#f3f1eb');draw=ImageDraw.Draw(canvas)
for row,f in enumerate([0,18,90,180]):
 for col,(key,folder) in enumerate([('004',pathlib.Path('results/004-deformation-constraints')),('005',O)]):
  im=Image.open(folder/'frames'/f'frame-{f:03}.png').convert('RGB').crop((270,185,570,315)).resize((600,260))
  canvas.paste(im,(col*600,row*290+30));draw.text((col*600+10,row*290+8),f'{key}  t={f/30:.3f}s   hem 2x',fill='black')
canvas.save(O/'hem-contact-sheet.png')
# Actual maximum strain (may be inside acceptance), and max curvature-change event.
worst=[]
for key,folder in [('004',pathlib.Path('results/004-deformation-constraints')),('005',O)]:
 for p,part in enumerate(['hair','skirt']):
  for event in ['worstEdge','worstCurvatureChange']:
   v=d[key][p][event];f=round(v['time']*60);frame=json.load(open(folder/('geometry-trace.json')))[f][p]
   if key=='004': rig=json.load(open(O/'source-fixture.srig.json'))
   else:rig=json.load(open(O/'source-fixture.srig.json'))
   # Render source is closest exported sample (<=1/60s); geometry overlay exact time.
   n=min(239,round(f/2));im=Image.open(folder/'frames'/f'frame-{n:03}.png').convert('RGB');dr=ImageDraw.Draw(im);tx=rig['parts'][p]['transform']['x'];ty=rig['parts'][p]['transform']['y']
   if event=='worstEdge':
    ids=v['vertices'];pts=[(frame[i]['x']+tx,frame[i]['y']+ty) for i in ids];dr.line(pts,fill='red',width=4)
   else:
    i=v['row']*9+v['column'];pt=(frame[i]['x']+tx,frame[i]['y']+ty);dr.ellipse((pt[0]-6,pt[1]-6,pt[0]+6,pt[1]+6),outline='red',width=3)
   dr.text((10,10),f'{key} {part} {event} exact t={v["time"]:.6f}s',fill='black');name=f'worst-{key}-{part}-{event}.png';im.save(O/name);worst.append({'file':name,'experiment':key,'part':part,'event':event,'exactGeometryTime':v['time'],'backgroundFrameTime':n/30,'details':v})
(O/'worst-events.json').write_text(json.dumps(worst,indent=2)+'\n')
print('Saved time series, hem comparison, and exact event overlays')
