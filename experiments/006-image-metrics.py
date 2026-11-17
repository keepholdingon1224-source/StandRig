import json,pathlib,numpy as np
from PIL import Image
O=pathlib.Path('results/006-gui-playback');B=pathlib.Path('results/005-spatiotemporal-constraints');rows=[]
for i in range(240):
 n=f'frame-{i:03}.png';a=np.asarray(Image.open(B/'frames'/n).convert('RGB')).astype(float);b=np.asarray(Image.open(O/'gui-screenshots/before'/n).convert('RGB')).astype(float)
 ma=np.max(np.abs(a-[238,240,243]),axis=-1)>16;mb=np.max(np.abs(b-[238,240,243]),axis=-1)>16
 def edge(m):
  interior=m.copy();interior[1:]=interior[1:]&m[:-1];interior[:-1]=interior[:-1]&m[1:];interior[:,1:]=interior[:,1:]&m[:,:-1];interior[:,:-1]=interior[:,:-1]&m[:,1:];return m&~interior
 ea,eb=edge(ma),edge(mb);common=ma&mb
 rows.append(dict(frame=i,silhouetteIoU=float((ma&mb).sum()/(ma|mb).sum()),baselineOnlyPixels=int((ma&~mb).sum()),guiOnlyPixels=int((mb&~ma).sum()),edgeXorPixels=int((ea^eb).sum()),foregroundMeanRGBBaseline=a[common].mean(0).tolist(),foregroundMeanRGBGui=b[common].mean(0).tolist(),foregroundMAE=float(np.abs(a[common]-b[common]).mean())))
(O/'differences/contours-colors.json').write_text(json.dumps(dict(definition='Foreground max RGB distance from background >16; 4-neighbor contour; diagnostic threshold only, no acceptance tolerance',minimumSilhouetteIoU=min(r['silhouetteIoU'] for r in rows),maximumMissingPixels=max(r['baselineOnlyPixels'] for r in rows),frames=rows),indent=2)+'\n')
print('diagnostic contours and colors saved')
