"""Build periodic specimen meshes, validate their geometry, and render evidence."""
import json
import subprocess
import sys
from pathlib import Path

import cv2 as cv
import numpy as np
from scipy.ndimage import gaussian_filter1d

OUT = Path('results/007-character-application')
cv.setNumThreads(2)
N = 480

def write(path, value):
    (OUT/path).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')

def save(path, image):
    assert cv.imwrite(str(OUT/path), image, [cv.IMWRITE_PNG_COMPRESSION, 4])

def read(path):
    image = cv.imread(str(OUT/path), cv.IMREAD_UNCHANGED)
    if image is None:
        raise FileNotFoundError(path)
    return image

def smoothstep(s):
    return s*s*(3-2*s)

def build(name):
    texture = read(f'segmentation/assisted/{name}.png')
    yy, xx = np.where(texture[:,:,3])
    top, bottom = int(yy.min()), int(yy.max())
    left, right = int(xx.min()), int(xx.max())
    hair = name != 'skirt'
    rows = np.linspace(top, bottom+1, 19)
    cols = np.linspace(0, 1, 3 if hair else 9)
    centers = np.array([np.median(np.where((texture[:,:,3]>0)[r])[0])
                        for r in range(top,bottom+1)])
    good = np.isfinite(centers)
    cx = gaussian_filter1d(np.interp(np.arange(len(centers)), np.flatnonzero(good), centers[good]), 5)
    cx = np.interp(rows, np.arange(top,bottom+1), cx)
    # Ensure the mesh covers the entire matte, including outlying silhouette
    # pixels between adjacent centerline samples.
    half_width = 2+np.max(np.abs(xx-np.interp(yy, rows, cx)))
    row_x = cx[:,None] + (cols-.5)*2*half_width if hair else np.broadcast_to(np.linspace(left-1,right+2,len(cols)),(len(rows),len(cols)))
    rest = np.stack((row_x,np.broadcast_to(rows[:,None], row_x.shape)),axis=-1)
    center = np.column_stack((cx, rows))
    extent = float(np.linalg.norm(np.diff(center, axis=0),axis=1).sum()) if hair else float(bottom+1-top)
    if hair:
        measured = [center[-1].tolist()]
    else:
        hem_x = np.rint(np.quantile(xx,[.20,.80])).astype(int)
        measured = [[int(col),int(yy[xx==col].max())] for col in hem_x]
    return texture, rest, center, extent, measured

names = ['left','right','skirt']
families = {name:build(name) for name in names}
write('rigging/measurement-definitions.json',{
    'hair': 'Rest centerline polyline length; center vertex at last mesh row, peak-to-peak x.',
    'skirt': 'Rest top-to-bottom height; lowest opaque matte pixel at the x 20th/80th percentiles, transported barycentrically; peak-to-peak x.',
    'restProbePointsXY': {n:families[n][-1] for n in names},
    'normalizedLengths': {'hair':240,'skirt':200}
})
t = 2*np.pi*np.arange(N)/N
model = {}
metrics = {}
guide = read('reconstruction/static.png')
for name, (texture, rest, center, extent, measured) in families.items():
    nr,nc = rest.shape[:2]
    triangles = []
    for row in range(nr-1):
        for col in range(nc-1):
            j = row*nc+col
            triangles.extend(((j,j+1,j+nc),(j+1,j+nc+1,j+nc)))
    tri = np.array(triangles)
    edges = np.unique(np.sort(tri[:,[[0,1],[1,2],[2,0]]].reshape(-1,2),axis=1),axis=0)
    s = np.linspace(0,1,nr)
    if name != 'skirt':
        # Rotate the rest centerline segments as in the 005 inextensible
        # formulation, preserving each segment length and the row width.
        phase = 0 if name=='left' else .5
        signal = gaussian_filter1d(np.sin(t+phase),6,mode='wrap')
        angle = .245 * signal[:,None] * smoothstep(s)
        angle = np.broadcast_to(angle,(N,nr))
        segment = np.diff(center,axis=0)
        a = (angle[:,1:] + angle[:,:-1])/2
        c, d = np.cos(a), np.sin(a)
        displacement = np.stack((c*segment[:,0]+d*segment[:,1], -d*segment[:,0]+c*segment[:,1]),axis=-1)
        curve = np.concatenate((np.broadcast_to(center[0],(N,1,2)),center[0]+np.cumsum(displacement,axis=1)),axis=1)
        width = rest[:,:,0]-center[:,None,0]
        pose = curve[:,:,None,:]+np.stack((np.cos(angle)[:,:,None]*width,-np.sin(angle)[:,:,None]*width),axis=-1)
    else:
        left = np.sin(t-.2)+.1*np.sin(2*t-.4)
        right = np.sin(t+.48)+.1*np.sin(2*t+.96)
        mix = smoothstep(np.linspace(0,1,nc))
        signal = left[:,None]*(1-mix)+right[:,None]*mix
        signal = gaussian_filter1d(gaussian_filter1d(signal,6,axis=0,mode='wrap'),.65,axis=1,mode='nearest')
        pose = np.broadcast_to(rest,(N,*rest.shape)).copy()
        pose[:,:,:,0] += (.054*extent)*smoothstep(s)[None,:,None]*signal[:,None,:]
    flat = rest.reshape(-1,2)
    samples = pose.reshape(N,-1,2)
    length = lambda v: np.linalg.norm(v[...,edges[:,0],:]-v[...,edges[:,1],:],axis=-1)
    ratio = length(samples)/length(flat)
    def area(p):
        a=p[...,tri[:,1],:]-p[...,tri[:,0],:]
        b=p[...,tri[:,2],:]-p[...,tri[:,0],:]
        return a[...,0]*b[...,1]-a[...,1]*b[...,0]
    sample_areas = area(samples)
    root = np.linalg.norm(samples[:,:nc]-flat[:nc],axis=-1).max()
    seam = 30*np.linalg.norm(samples[2]-2*samples[0]+samples[-2],axis=-1).max()
    scale = (240 if name!='skirt' else 200)/extent
    travel_points = []
    probes = []
    for point in measured:
        for ids in tri:
            a,b,c=flat[ids]
            bary=np.linalg.solve(np.column_stack((b-a,c-a)),np.asarray(point)-a)
            weights=np.r_[1-bary.sum(),bary]
            if np.min(weights)>=-1e-9:
                travel_points.append(samples[:,ids,0]@weights)
                probes.append({'restXY':point,'triangleVertexIndices':ids.tolist(),'weights':weights.tolist()})
                break
        else:
            raise ValueError(f'Probe outside {name}: {point}')
    travel = np.ptp(np.stack(travel_points,axis=1),axis=0)
    m = {'restLengthPx':extent,'edgeRatio':[float(ratio.min()),float(ratio.max())],
         'invertedOrDegenerateTriangleSamples':int((sample_areas<=0).sum()),
         'positionSeamPx':0,'samePhaseVelocityDeltaPxPerSecond':0,'rootMaxPx':float(root),
         'seam30PxPerSecond':float(seam),'normalizationScale':scale,
         'positionSeamNormalizedPx':0,'samePhaseVelocityDeltaNormalizedPxPerSecond':0,
         'rootMaxNormalizedPx':float(root*scale),'seam30NormalizedPxPerSecond':float(seam*scale),
         'horizontalTravelPx':travel.tolist(),'horizontalTravelFraction':(travel/extent).tolist(),
         'meshBounds': [samples.min(axis=(0,1)).tolist(),samples.max(axis=(0,1)).tolist()]}
    if name!='skirt':
        length_ratio = np.linalg.norm(np.diff(curve,axis=1),axis=-1).sum(axis=1)/extent
        widths = np.linalg.norm(pose[:,:,-1]-pose[:,:,0],axis=-1)/(rest[:,-1,0]-rest[:,0,0])
        directions = np.diff(pose,axis=1)
        a,b = directions[:,:-1], directions[:,1:]
        curvature = np.arctan2(a[...,0]*b[...,1]-a[...,1]*b[...,0],(a*b).sum(axis=-1))
        curvature /= (.5*(np.linalg.norm(a,axis=-1)+np.linalg.norm(b,axis=-1)))
        m.update(centerlineRatio=[float(length_ratio.min()),float(length_ratio.max())],
                 meshWidthRatio=[float(widths.min()),float(widths.max())],
                 verticalCurvatureMaxRadPerPx=float(np.abs(curvature).max()))
        width_profile = []
        for row in np.linspace(int(flat[0,1]),int(flat[-1,1])-1,19).astype(int):
            positions=np.flatnonzero(texture[row,:,3])
            width_profile.append({'y':int(row),'matteWidthPx':int(np.ptp(positions)+1) if len(positions) else 0})
        write(f'rigging/{name}-local-width.json',width_profile)
        cv.polylines(guide,[center.astype('int32')],False,(0,230,255),3)
        cv.circle(guide,tuple(center[0].astype(int)),8,(0,20,250),-1)
    else:
        cv.line(guide,tuple(flat[0].astype(int)),tuple(flat[nc-1].astype(int)),(0,20,250),3)
        cv.polylines(guide,[rest[:,nc//2].astype('int32')],False,(0,230,255),3)
    metrics[name] = m
    ax,ay = np.floor(flat.min(axis=0)).astype(int)
    bx,by = np.ceil(flat.max(axis=0)).astype(int)+1
    save(f'rigging/{name}-texture.png',texture[ay:by,ax:bx])
    model[name]={'origin':[int(ax),int(ay)],'textureSize':[int(bx-ax),int(by-ay)],
                 'centerline':center.tolist() if name!='skirt' else None,
                 'rootVertices':list(range(nc)), 'continuousControlWeights':mix.tolist() if name=='skirt' else None,
                 'rest': flat.tolist(),'triangles':tri.tolist(),'probes':probes,
                 'samples':np.round(samples[np.arange(482)%N],6).tolist()}
save('rigging/roots-and-controls.png',guide)
write('metrics.json',metrics)
(OUT/'rigging/mesh-and-phase.json').write_text(json.dumps(model,separators=(',',':'))+'\n')
if '--geometry-only' in sys.argv:
    sys.exit()

def warp(base, name, frame):
    item=model[name]
    source=np.asarray(item['rest'])
    target=np.asarray(item['samples'][frame])
    tri=np.asarray(item['triangles'])
    width,height=base.shape[1],base.shape[0]
    xa,ya=np.maximum(0,np.floor(target.min(axis=0)).astype(int))
    xb,yb=np.minimum([width,height],np.ceil(target.max(axis=0)).astype(int)+1)
    mx=np.full((yb-ya,xb-xa),-1,np.float32)
    my=mx.copy()
    for ids in tri:
        dest=target[ids]
        l,u=np.floor(dest.min(axis=0)).astype(int)
        r,d=np.ceil(dest.max(axis=0)).astype(int)+1
        l,u,r,d=max(l,xa),max(u,ya),min(r,xb),min(d,yb)
        if r<=l or d<=u:
            continue
        yy,xx=np.ogrid[u:d,l:r]
        m=np.linalg.inv((dest[1:]-dest[0]).T)
        dx,dy=xx-dest[0,0],yy-dest[0,1]
        i,j=m[0,0]*dx+m[0,1]*dy,m[1,0]*dx+m[1,1]*dy
        valid=(i>=-1e-6)&(j>=-1e-6)&(i+j<=1+1e-6)
        start=source[ids[0]]
        a,b=source[ids[1:]]-start
        mx[u-ya:d-ya,l-xa:r-xa][valid]=(start[0]+i*a[0]+j*b[0])[valid]
        my[u-ya:d-ya,l-xa:r-xa][valid]=(start[1]+i*a[1]+j*b[1])[valid]
    warped=cv.remap(families[name][0],mx,my,cv.INTER_LINEAR)
    # Transparent asset RGB is zero, so linear sampling yields premultiplied RGB.
    tile=base[ya:yb,xa:xb]
    alpha=warped[:,:,3:4].astype(np.uint16)
    tile[:]=np.minimum(255,warped[:,:,:3]+(tile.astype(np.uint16)*(255-alpha)+127)//255).astype(np.uint8)

def encoder(file, width, height):
    return subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pixel_format','bgr24',
                             '-video_size',f'{width}x{height}','-framerate','30','-i','-','-an','-threads','2',
                             '-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p',
                             '-movflags','+faststart',str(OUT/file)],stdin=subprocess.PIPE)

base=read('reconstruction/completed-base.png')
neutral=read('reconstruction/static.png')
(OUT/'frames').mkdir(exist_ok=True)
variants={'character-loop.mp4':(1152,2048),'A-left-hair.mp4':(576,1024),'B-right-hair.mp4':(576,1024),
          'C-skirt.mp4':(576,1024),'comparison.mp4':(1152,1024),
          'hair-closeup.mp4':(420,500),'skirt-closeup.mp4':(800,400)}
enc={name:encoder(name,*size) for name,size in variants.items()}
for i in range(240):
    current=base.copy()
    for name in ('skirt','left','right'):
        warp(current,name,2*i)
    save(f'frames/frame-{i:03}.png',current)
    enc['character-loop.mp4'].stdin.write(current.tobytes())
    for filename, active in [('A-left-hair.mp4','left'),('B-right-hair.mp4','right'),('C-skirt.mp4','skirt')]:
        frame=base.copy()
        for name in ('skirt','left','right'):
            if name==active:
                warp(frame,name,2*i)
            else:
                texture=families[name][0]
                keep=texture[:,:,3]>0
                frame[keep]=texture[:,:,:3][keep]
        enc[filename].stdin.write(cv.resize(frame,(576,1024),interpolation=cv.INTER_AREA).tobytes())
    enc['hair-closeup.mp4'].stdin.write(current[410:910,330:750].tobytes())
    enc['skirt-closeup.mp4'].stdin.write(current[1400:1800,176:976].tobytes())
    enc['comparison.mp4'].stdin.write(np.concatenate((cv.resize(neutral,(576,1024)),cv.resize(neutral if i<60 else current,(576,1024))),axis=1).tobytes())
    if i%30==0:
        print(f'Rendered {i+1}/240',flush=True)
for proc in enc.values():
    proc.stdin.close()
    if proc.wait():
        raise RuntimeError('FFmpeg failed')
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-stream_loop','2','-i',
                str(OUT/'character-loop.mp4'),'-c','copy','-movflags','+faststart',str(OUT/'three-loops.mp4')],check=True)
