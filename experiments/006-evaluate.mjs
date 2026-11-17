import {readFile,writeFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {parseModelBundle} from '@standrig/core/bundle';
import {MotionController} from '@standrig/runtime/motion';
import {resolveArtMesh} from '@standrig/core/artMesh';
import {renderRigScreenshot,screenshotOptionsFromUrl} from '@standrig/core/serverRenderer';
import {decodePng,encodePng} from '@standrig/core/png';
import {load,save,hash,measure} from './004-deformation-constraints.mjs';
const out='results/006-gui-playback',base='results/005-spatiotemporal-constraints';
// Use files actually downloaded using GUI export, not the conversion input.
const rig=parseModelBundle(await load(out+'/gui-exported-model.srig')).rig,motion=await load(out+'/gui-exported-motion.json'),original=await load(base+'/source-fixture.srig.json'),trace=await load(base+'/geometry-trace.json');
const controller=new MotionController(rig.parameters);controller.load(motion);
let maxError=0;const frames=[];
for(let i=0;i<482;i++){
 // The clip ends at 8; the additional boundary-velocity sample is evaluated
 // through the same phase binding at 8+1/60 (preserved in the model).
 const values=i<=480?controller.seek(i/60,{BakedPhase:0},0):{BakedPhase:481/60};
 const vs=rig.parts.map((p,k)=>resolveArtMesh(p,rig.assets[k].width,rig.assets[k].height,values).vertices);frames.push(vs);
 for(let p=0;p<2;p++)for(let j=0;j<153;j++)maxError=Math.max(maxError,Math.hypot(vs[p][j].x-trace[i][p][j].x,vs[p][j].y-trace[i][p][j].y));
}
const measured=measure(original,frames);await save(out+'/metrics.json',{maxVertexErrorPx:maxError,samples:482,evaluation:'GUI-exported files -> MotionController.seek -> resolveArtMesh; extra sample phase 481/60 in same native binding',definitions:(await load(base+'/metrics.json')).definitions,candidate:measured,baseline:(await load(base+'/metrics.json')).candidate});
await save(out+'/evaluated-geometry.json',frames.map(f=>f.map(vs=>vs.map(({x,y})=>({x,y})))));
let identical=0,maxChannel=0,sum=0,pixels=0;const rows=[];
for(let i=0;i<240;i++){
 const values=controller.seek(i/30,{BakedPhase:0},0);
 const png=(await renderRigScreenshot(rig,'.',{...screenshotOptionsFromUrl(rig,new URL('http://localhost/?width=640&height=360&padding=0&transparent=0&physics=0&supersample=1')),values})).png;
 await writeFile(`${out}/frames/frame-${String(i).padStart(3,'0')}.png`,png);
 const old=await readFile(`${base}/frames/frame-${String(i).padStart(3,'0')}.png`);if(hash(old)===hash(png))identical++;
 const a=decodePng(old),b=decodePng(png),diff={width:640,height:360,data:new Uint8ClampedArray(a.data.length)};let changed=0;
 for(let j=0;j<a.data.length;j+=4){let d=0;for(let k=0;k<3;k++){const x=Math.abs(a.data[j+k]-b.data[j+k]);diff.data[j+k]=x;maxChannel=Math.max(maxChannel,x);sum+=x;pixels++;d+=x;}diff.data[j+3]=255;if(d)changed++;}
 rows.push({frame:i,changedPixels:changed});await writeFile(`${out}/differences/frame-${String(i).padStart(3,'0')}.png`,encodePng(diff));if(i%60===0)console.log('render',i);
}
await save(out+'/differences/software.json',{byteIdenticalFrames:identical,maxChannelDifference:maxChannel,meanAbsoluteChannelDifference:sum/pixels,frames:rows});
const ff=(name,args)=>{try{execFileSync('ffmpeg',['-hide_banner','-loglevel','warning','-y',...args],{stdio:'pipe'});console.log(name,'ok');}catch(e){console.log(name,e.stderr?.toString());throw e;}};
ff('exported-loop',['-framerate','30','-i',out+'/frames/frame-%03d.png','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',out+'/exported-loop.mp4']);
ff('comparison',['-i',base+'/hair-skirt-loop.mp4','-i',out+'/exported-loop.mp4','-filter_complex','hstack=inputs=2','-c:v','libx264','-crf','18','-pix_fmt','yuv420p',out+'/comparison-005-006.mp4']);
ff('three-loops',['-stream_loop','2','-i',out+'/exported-loop.mp4','-c','copy',out+'/three-loops.mp4']);
console.log({maxError,identical,quality:measured.pass});
