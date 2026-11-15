import {readFile,writeFile,copyFile,readdir} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import assert from 'node:assert/strict';
import {parseMotion,validateMotionParameters,sampleMotion} from '@standrig/core/motion';
import {renderRigScreenshot,screenshotOptionsFromUrl} from '@standrig/core/serverRenderer';
import {decodePng} from '@standrig/core/png';
import {resolveArtMesh} from '@standrig/core/artMesh';
const out='results/003-secondary-loop';
const load=async name=>JSON.parse(await readFile(`${out}/${name}.json`,'utf8'));
const metrics=await load('metrics'),rig=await load('baked-fixture.srig'),motion=parseMotion(await load('baked-motion'));
const tests=[];
function check(name,fn){fn();tests.push({name,pass:true});}
check('numeric-acceptance',()=>assert.deepEqual(metrics.failed,[]));
check('baked-physics-disabled',()=>assert.equal(rig.physics.enabled,false));
check('motion-parameter-validation',()=>validateMotionParameters(motion,rig.parameters));
const trace=await load('physics-trace-60fps');
let bakedSeamVelocityJump=0,maxOrdinaryVelocityJump=0;
for(const part of rig.parts){const asset=rig.assets.find(a=>a.id===part.assetId);
 const mesh=i=>resolveArtMesh(part,asset.width,asset.height,trace[i]).vertices;
 const points=Array.from({length:241},(_,i)=>mesh(i*2));
 for(let j=0;j<points[0].length;j++){
  const velocity=(a,b)=>({x:(b.x-a.x)*30,y:(b.y-a.y)*30});
  const first=velocity(points[0][j],points[1][j]),last=velocity(points[239][j],points[240][j]);
  bakedSeamVelocityJump=Math.max(bakedSeamVelocityJump,Math.hypot(first.x-last.x,first.y-last.y));
  for(let i=1;i<240;i++){const a=velocity(points[i-1][j],points[i][j]),b=velocity(points[i][j],points[i+1][j]);maxOrdinaryVelocityJump=Math.max(maxOrdinaryVelocityJump,Math.hypot(a.x-b.x,a.y-b.y));}
 }
}
check('baked-seam-velocity-jump-within-normal-frame-curvature',()=>assert.ok(bakedSeamVelocityJump<=maxOrdinaryVelocityJump+1e-8));
const frames=(await readdir(out+'/frames')).filter(n=>/^frame-\d{3}\.png$/.test(n)).sort();
check('240-png-frames',()=>assert.equal(frames.length,240));
let clippedFrames=0,blankFrames=0;const backgrounds=[];
for(const name of frames){const image=decodePng(await readFile(out+'/frames/'+name));
 const bg=Array.from(image.data.slice(0,4));backgrounds.push(bg);
 const changed=(x,y)=>{const i=(y*image.width+x)*4;return bg.some((v,c)=>image.data[i+c]!==v);};
 let clipped=false,nonbg=0;
 for(let y=0;y<image.height;y++)for(let x=0;x<image.width;x++)if(changed(x,y)){nonbg++;if(x===0||y===0||x===image.width-1||y===image.height-1)clipped=true;}
 if(clipped)clippedFrames++;if(nonbg===0)blankFrames++;
}
check('no-frame-edge-clipping',()=>assert.equal(clippedFrames,0));
check('no-blank-frames',()=>assert.equal(blankFrames,0));
const options=screenshotOptionsFromUrl(rig,new URL('http://localhost/?width=640&height=360&padding=0&transparent=0&physics=0'));
for(const index of [0,60,120,180]){
 const actual=await renderRigScreenshot(rig,'.',{...options,values:sampleMotion(motion,index/30)});
 const expected=decodePng(await readFile(`${out}/frames/frame-${String(index).padStart(3,'0')}.png`));
 check(`serialized-motion-render-frame-${index}`,()=>assert.deepEqual(decodePng(actual.png).data,expected.data));
}
const video=JSON.parse(execFileSync('ffprobe',['-v','error','-show_entries','stream=codec_name,width,height,nb_frames,r_frame_rate','-show_entries','format=duration','-of','json',out+'/hair-skirt-loop.mp4'],{encoding:'utf8'}));
check('mp4-duration-8-seconds',()=>assert.equal(Number(video.format.duration),8));
check('mp4-240-frames-30fps',()=>{assert.equal(Number(video.streams[0].nb_frames),240);assert.equal(video.streams[0].r_frame_rate,'30/1');});
execFileSync('ffmpeg',['-v','error','-i',out+'/hair-skirt-loop.mp4','-f','null','-'],{stdio:'pipe'});
tests.push({name:'decode-entire-mp4',pass:true});
await writeFile(out+'/video-probe.json',JSON.stringify(video,null,2));
await writeFile(out+'/verification.json',JSON.stringify({time:new Date().toISOString(),tests,clippedFrames,blankFrames,bakedSeamVelocityJump,maxOrdinaryVelocityJump,notTested:['body collisions','character anatomy and attachment','WebGL/browser parity','human-perceived naturalness']},null,2));
await copyFile(import.meta.filename,out+'/code/003-verify.mjs');
console.log(JSON.stringify({pass:true,tests:tests.length,clippedFrames,blankFrames}));
