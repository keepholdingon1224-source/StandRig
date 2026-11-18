"""Check persisted mesh, frame, model, GUI and video artifacts independently."""
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops

OUT=Path('results/007-character-application')

def load(path):
    return json.loads((OUT/path).read_text())

def image(path):
    with Image.open(path) as source:
        return source.copy()

def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout

checks={}
raw_mesh=load('rigging/mesh-and-phase.json')
metrics=load('metrics.json')
duration=load('model/character-motion.json')['duration']
rig=load('model/character.srig')['rig']
saved_rig=json.loads(run('node','--input-type=module','-e', '''
import {readFileSync} from 'node:fs';
import {parseModelBundle} from '@standrig/core/bundle';
console.log(JSON.stringify(parseModelBundle(JSON.parse(readFileSync(process.argv[1],'utf8'))).rig))
''',str(OUT/'model/gui-exported-model.srig')))
checks['physicalSolverDisabled']=rig['physics']=={'enabled':False,'chains':[]}
checks['nativeBakeRoundTrip']=all(
    a['artMesh']==b['artMesh'] and a['transform']==b['transform']
    for a,b in zip(rig['parts'],saved_rig['parts'],strict=True)
) and load('model/character-motion.json')['tracks']==load('model/gui-exported-motion.json')['tracks']
checks['eightSecondMotion']=duration==8
measure=load('rigging/measurement-definitions.json')
height,width=2048,1152
for name,data in raw_mesh.items():
    rest=np.array(data['rest'])
    pose=np.array(data['samples'])
    tri=np.array(data['triangles'])
    a,b,c=tri.T
    lengths=[]
    for i,j in [(a,b),(b,c),(c,a)]:
        lengths.append(np.linalg.norm(pose[:,i]-pose[:,j],axis=-1)/np.linalg.norm(rest[i]-rest[j],axis=-1))
    check={
        'edgeRatios':[float(np.min(lengths)),float(np.max(lengths))],
        'flippedOrDegenerateTriangleSamples':int((np.linalg.det(np.stack((pose[:,b]-pose[:,a],pose[:,c]-pose[:,a]),axis=-1))<=0).sum())
    }
    roots=data['rootVertices']
    maximum=lambda v:float(np.linalg.norm(v,axis=-1).max())
    root=maximum(pose[:,roots]-rest[roots])
    seam=maximum(pose[480]-pose[0])
    velocity=60*maximum((pose[481]-pose[480])-(pose[1]-pose[0]))
    step30=30*maximum((pose[2]-pose[0])-(pose[480]-pose[478]))
    scale=metrics[name]['normalizationScale']
    assert [probe['restXY'] for probe in data['probes']]==measure['restProbePointsXY'][name]
    tracks=[]
    for probe in data['probes']:
        weights=np.array(probe['weights'])
        ids=probe['triangleVertexIndices']
        assert abs(weights.sum()-1)<1e-9 and np.min(weights)>=-1e-9
        assert np.allclose(weights@rest[ids],probe['restXY'],atol=1e-9)
        tracks.append(pose[:480,ids,0]@weights)
    fractions=np.ptp(tracks,axis=1)/metrics[name]['restLengthPx']
    binding=next(p for p in rig['parts'] if p['id']==name)['artMesh']['bindings'][0]
    offsets=np.array([[[o['x'],o['y']] for o in key['offsets']] for key in binding['keys']])
    passes={
        'edgeLimits':check['edgeRatios'][0]>=.90 and check['edgeRatios'][1]<=1.10,
        'orientation':check['flippedOrDegenerateTriangleSamples']==0,
        'frameBounds':bool(np.all(pose>=0) and np.all(pose<=[width,height])),
        'rootAndSeam':max(root*scale/.01,seam*scale/.05,velocity*scale/.5,step30*scale/2)<=1,
        'targetTravel':bool(np.all(fractions>=(.10 if name=='skirt' else .20))),
        'nativeBakedKeysMatchMesh':maximum(rest+offsets[:482]-pose)<1e-10 and maximum(offsets[-1])<1e-10
    }
    if name!='skirt':
        vertices=np.arange(1,len(rest),3)
        ratio=np.linalg.norm(np.diff(pose[:,vertices],axis=1),axis=-1).sum(axis=1)/np.linalg.norm(np.diff(rest[vertices],axis=0),axis=-1).sum()
        check['centerlineLengthRatio']=[float(ratio.min()),float(ratio.max())]
        passes['centerlineLength']=bool(np.all((ratio>=.97)&(ratio<=1.03)))
    else:
        # The two controls share one mesh, including the entire middle column.
        adjacency=np.bincount(tri.flatten(),minlength=len(rest)).reshape(-1,9)
        passes['oneConnectedMeshWithSharedCentralVertices']=bool(np.all(adjacency[:,4]>=3))
    check.update({'nativeUnits':{'rootPx':root,'positionSeamPx':seam,'velocity60PxPerSecond':velocity,'boundary30PxPerSecond':step30},
                  'normalizedUnits':{'rootPx':root*scale,'positionSeamPx':seam*scale,'velocity60PxPerSecond':velocity*scale,'boundary30PxPerSecond':step30*scale},
                  'horizontalTravelFraction':fractions.tolist(),'checks':passes})
    checks[name]=check

src=image(Path('source_007/original.png'))
static=image(OUT/'reconstruction/static.png')
checks['staticExact']=ImageChops.difference(src,static).getbbox() is None
gui=image(OUT/'reconstruction/gui-neutral.png')
rgb=np.asarray(gui.convert('RGB')).astype('int16')
orig=np.asarray(src).astype('int16')
delta=np.abs(rgb-orig)
Image.fromarray(np.minimum(delta*6,255).astype('uint8')).save(OUT/'reconstruction/gui-difference-x6.png')
check_gui={'meanAbsoluteChannelError':float(delta.mean()),'pixelsWithAnyDifference':int(np.count_nonzero(np.any(delta,axis=2))),
           'pixelsWithDifferenceAbove8':int(np.count_nonzero(np.max(delta,axis=2)>8)),
           'nonOpaquePixels':int(np.count_nonzero(np.asarray(gui.convert('RGBA'))[:,:,3]<255)),
           'fullyTransparentPixels':int(np.count_nonzero(np.asarray(gui.convert('RGBA'))[:,:,3]==0))}
for label,mask in [('fixed','source-preserved-mask'),('completedFootprint','synthesized-mask')]:
    area=np.asarray(image(OUT/f'reconstruction/{mask}.png'))>0
    check_gui[label]={'pixels':int(area.sum()),'meanAbsoluteChannelError':float(delta[area].mean())}
checks['guiNeutralPixelDifference']=check_gui
frames=sorted((OUT/'frames').glob('*.png'))
checks['frames']={'count':len(frames),'passes':True,'fixedHeadRows':430}
skirt=raw_mesh['skirt']
rest_center=np.array(skirt['rest'])[4::9]
skirt_mask=np.asarray(image(OUT/'segmentation/assisted/skirt-binary.png'))>0
base=np.asarray(image(OUT/'reconstruction/completed-base.png'))
center_rows=np.arange(int(rest_center[0,1])+8,int(rest_center[-1,1])-8)
center_x=int(rest_center[0,0])
interior=np.all(skirt_mask[center_rows[:,None],center_x+np.arange(-5,6)],axis=1)
center_rows=center_rows[interior]
missing=0
for i,path in enumerate(frames):
    fr=image(path)
    crop=(0,0,width,430)
    ok=(path.name==f'frame-{i:03}.png' and fr.size==(width,height) and fr.mode=='RGB'
        and fr.getextrema()[0][0]<fr.getextrema()[0][1]
        and ImageChops.difference(src.crop(crop),fr.crop(crop)).getbbox() is None)
    checks['frames']['passes'] &= ok
    moved=np.array(skirt['samples'][2*i])[4::9]
    xs=np.rint(np.interp(center_rows,moved[:,1],moved[:,0])).astype(int)
    colors=np.asarray(fr)[center_rows,xs]
    missing+=int(np.all(colors==base[center_rows,xs],axis=1).sum())
checks['frames']['passes'] &= len(frames)==240
checks['videos']={}
for file in sorted(OUT.glob('*.mp4')):
    stream=json.loads(run('ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_streams','-of','json',str(file)))['streams'][0]
    run('ffmpeg','-v','error','-xerror','-threads','2','-i',str(file),'-f','null','-')
    long=file.name=='three-loops.mp4'
    passed=int(stream['nb_read_frames'])==(720 if long else 240) and float(stream['duration'])==(24 if long else 8) and stream['avg_frame_rate']=='30/1'
    if file.name in ('character-loop.mp4','three-loops.mp4'):
        passed &= (stream['width'],stream['height'])==(width,height)
    checks['videos'][file.name]={'pass':passed,'decodedFrames':int(stream['nb_read_frames']),
                                 'duration':float(stream['duration']),'fps':stream['avg_frame_rate'],
                                 'dimensions':[stream['width'],stream['height']]}
run('sha256sum','-c','--quiet',str(OUT/'source/007-baseline.sha256'))
checks['fixed005And006']={'verifiedFiles':len((OUT/'source/007-baseline.sha256').read_text().splitlines()),'pass':True}
checks['independentMaskIoU']={'status':'not measured','reason':'No independently reviewed ground truth'}
checks['softwareRendersAndMatteSeams']={'visualApproval':'pending','triangleAdjacency':'verified',
    'centerlinePixelSamples':int(len(frames)*len(center_rows)),'centerlineSamplesShowingBareBase':missing}
checks['guiOperationsPassed']=load('gui-verification.json')['status']=='pass'
passed=all(checks[k] for k in ('physicalSolverDisabled','eightSecondMotion','nativeBakeRoundTrip','staticExact','guiOperationsPassed'))
passed &= checks['frames']['passes'] and missing==0 and len(checks['videos'])==8 and all(v['pass'] for v in checks['videos'].values())
passed &= all(all(checks[n]['checks'].values()) for n in raw_mesh)
(OUT/'verification.json').write_text(json.dumps({'numericAndOperationalChecksPassed':passed,'checks':checks},indent=2)+'\n')
print('Numeric and operational checks:', 'PASS' if passed else 'FAIL')
raise SystemExit(0 if passed else 1)
