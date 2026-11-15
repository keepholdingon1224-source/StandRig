// Original synthetic fixture. No external artwork, model API, or paid service.
import {mkdir,writeFile,readFile,copyFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {execFileSync,spawnSync} from 'node:child_process';
import assert from 'node:assert/strict';
import {createRectArtMesh,resolveArtMesh} from '@standrig/core/artMesh';
import {DEFAULT_TRANSFORM} from '@standrig/core/types';
import {validateRig} from '@standrig/core/inspect';
import {evaluatePendulumPhysics} from '@standrig/core/pendulumPhysics';
import {renderRigScreenshot,screenshotOptionsFromUrl} from '@standrig/core/serverRenderer';
import {decodePng,encodePng} from '@standrig/core/png';
import {parseMotion,validateMotionParameters,sampleMotion} from '@standrig/core/motion';

const out='results/003-secondary-loop', fps=30, simFps=60, seconds=8, steps=seconds*simFps;
await mkdir(out+'/frames',{recursive:true});await mkdir(out+'/code',{recursive:true});await mkdir(out+'/assets',{recursive:true});
const json=async(name,value)=>writeFile(`${out}/${name}.json`,JSON.stringify(value,null,2));
const started=new Date().toISOString();
const source=await readFile(import.meta.filename);
await copyFile(import.meta.filename,out+'/code/003-secondary-loop.mjs');
const sha=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();
const definitions=[{id:'hair',w:120,h:240,x:100,y:60,role:'hair-front',color:[92,57,139]},
 {id:'skirt',w:240,h:200,x:295,y:80,role:'clothing',color:[34,115,153]}];
function texture(d){
 const data=new Uint8ClampedArray(d.w*d.h*4);
 for(let y=0;y<d.h;y++)for(let x=0;x<d.w;x++){
  const u=x/d.w,v=y/d.h;
  const half=d.id==='hair'?0.28*Math.pow(1-v,0.38)+0.035:0.24+0.23*v;
  const center=0.5+(d.id==='hair'?0.04*Math.sin(v*5):0);
  const bottom=d.id==='hair'?1:0.95+0.025*Math.cos(u*8*Math.PI);
  if(Math.abs(u-center)>half||v>bottom)continue;
  const pleat=d.id==='hair'?Math.cos((u-center)*35+v*1.5):Math.cos(u*8*Math.PI);
  const edge=Math.abs(u-center)/half,shade=0.85+0.16*pleat-0.22*edge;
  const i=(y*d.w+x)*4;
  const trim=d.id==='skirt'&&v>bottom-0.045;
  for(let c=0;c<3;c++)data[i+c]=trim?[224,186,97][c]:Math.round(d.color[c]*shade);
  data[i+3]=255;
 }
 return encodePng({width:d.w,height:d.h,data});
}
const parameters=[{id:'Drive',label:'Periodic breeze / gravity tilt',min:-1,max:1,default:0}];
for(const d of definitions)for(let k=0;k<3;k++)parameters.push({id:`${d.id}${k}`,label:`${d.id} segment ${k}`,min:-1,max:1,default:0});
const rig={schemaVersion:'0.1.0',name:'Original hair and hem laboratory',stage:{width:640,height:360,background:'#f3f1eb'},parameters,assets:[],parts:[],deformers:[],physics:{enabled:true,chains:[],pendulum:{fps:simFps,settings:[]}}};
for(const d of definitions){
 const png=texture(d);await writeFile(`${out}/assets/${d.id}.png`,png);
 rig.assets.push({id:d.id,name:d.id,type:'image',width:d.w,height:d.h,src:'data:image/png;base64,'+Buffer.from(png).toString('base64')});
 const artMesh=createRectArtMesh(d.w,d.h,{preset:'face-feature',columns:8,rows:16});
 artMesh.blendShapes=[];
 // Automatically derive three relative bending channels from normalized height.
 // Positive and negative shapes retain a fixed top edge, including UVs/topology.
 for(let k=0;k<3;k++)for(const sign of [-1,1]){
  const angle=sign*(d.id==='hair'?0.55:0.30);
  artMesh.blendShapes.push({id:`bend-${k}-${sign}`,parameter:`${d.id}${k}`,neutralInput:0,targetInput:sign,
   offsets:artMesh.vertices.map(v=>{const lever=Math.max(0,v.y-k*d.h/3);return {vertexId:v.id,x:Math.sin(angle)*lever,y:(Math.cos(angle)-1)*lever};})});
 }
 rig.parts.push({id:d.id,name:d.id,kind:'image',parentId:null,assetId:d.id,visible:true,drawOrder:1,role:d.role,roleStatus:'confirmed',transform:{...DEFAULT_TRANSFORM,x:d.x,y:d.y,pivotX:0,pivotY:0},artMesh});
 rig.physics.pendulum.settings.push({id:d.id,name:d.id+' automatic three-segment pendulum',inputs:[{parameter:'Drive',type:'angle',weight:100,reflect:true}],
  outputs:[0,1,2].map(k=>({parameter:`${d.id}${k}`,vertexIndex:k+1,type:'angle',scale:d.id==='hair'?2.5:2,weight:100})),
  particles:[{mobility:1,delay:1,acceleration:1,radius:0},...[0,1,2].map(k=>({mobility:d.id==='hair'?0.90:0.84,delay:0.7-k*0.08,acceleration:d.id==='hair'?1.2:1.8,radius:d.id==='hair'?18:24}))],
  normalization:{position:{minimum:-10,default:0,maximum:10},angle:{minimum:-22,default:0,maximum:22}}});
}
const validation=validateRig(rig);await json('validation',validation);assert.equal(validation.ok,true,JSON.stringify(validation));
await json('fixture.srig',rig);
await json('manifest',{started,sourceCommit:sha,codeSha256:createHash('sha256').update(source).digest('hex'),node:process.version,platform:process.platform,
 rights:'Original procedural geometric artwork and code created for this experiment; Apache-2.0, no third-party character or SONY material.',
 fps,simFps,seconds,render:'StandRig core software serverRenderer, fixed camera, physics evaluated sequentially then baked, no interpolation at seam',
 manual:'No vertex/keyframe edits or painting. Algorithm, dimensions, 3 segments, grid density, amplitudes and physics constants selected by Codex; no image-based rig inference.',
 command:'node experiments/003-secondary-loop.mjs',acceptance:{invertedTriangles:0,maxRootDisplacement:1e-8,maxLoopVertexDelta:0.05,maxLoopVelocityDelta:0.5,minTipTravel:5}});

const drive=t=>0.72*Math.sin(2*Math.PI*t/8)+0.22*Math.sin(4*Math.PI*t/8+0.7);
const ranges=new Map(parameters.map(p=>[p.id,p]));
let state;
function tick(i){const Drive=drive(i/simFps);const r=evaluatePendulumPhysics(rig.physics.pendulum,ranges,{Drive},1/simFps,state);state=r.state;return {Drive,...r.outputs};}
// Pre-roll complete cycles until consecutive cycles converge, without endpoint edits.
let previous,trace,cycleDelta=Infinity,cycles=0;
for(let cycle=0;cycle<30;cycle++){
 const current=[];for(let i=0;i<steps;i++)current.push(tick(i));
 if(previous)cycleDelta=Math.max(...current.flatMap((v,i)=>Object.keys(v).map(k=>Math.abs(v[k]-previous[i][k]))));
 previous=current;trace=current;cycles=cycle+1;
 if(cycle>=2&&cycleDelta<1e-8)break;
}
assert.ok(cycleDelta<1e-6,`periodic state did not converge: ${cycleDelta}`);
// Additional cycle with a real t=8 endpoint for seam measurement.
trace=[];for(let i=0;i<=steps+1;i++)trace.push(tick(i));
await json('physics-trace-60fps',trace);
const area=(a,b,c)=>(b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x);
let inversions=0,minAreaRatio=Infinity,maxRoot=0,maxStretch=0,minStretch=Infinity,maxLoopVertexDelta=0,maxLoopVelocityDelta=0,saturated=0;
const resolved=trace.map(values=>definitions.map(d=>{const p=rig.parts.find(p=>p.id===d.id);return resolveArtMesh(p,d.w,d.h,values);}));
const partMetrics=[];
for(let p=0;p<definitions.length;p++){
 const d=definitions[p],base=rig.parts[p].artMesh;
 const tips=[];
 for(let f=0;f<resolved.length;f++){
  const mesh=resolved[f][p];
  for(let j=0;j<mesh.vertices.length;j++)if(base.vertices[j].v===0)maxRoot=Math.max(maxRoot,Math.hypot(mesh.vertices[j].x-base.vertices[j].x,mesh.vertices[j].y-base.vertices[j].y));
  for(let k=0;k<mesh.triangles.length;k+=3){const ids=mesh.triangles.slice(k,k+3);const ratio=area(...ids.map(i=>mesh.vertices[i]))/area(...ids.map(i=>base.vertices[i]));minAreaRatio=Math.min(minAreaRatio,ratio);if(ratio<=0)inversions++;
   for(let edge=0;edge<3;edge++){const a=ids[edge],b=ids[(edge+1)%3];const dist=(verts)=>Math.hypot(verts[a].x-verts[b].x,verts[a].y-verts[b].y);const stretch=dist(mesh.vertices)/dist(base.vertices);maxStretch=Math.max(maxStretch,stretch);minStretch=Math.min(minStretch,stretch);}}
  const tip=mesh.vertices.find(v=>v.u===0.5&&v.v===1);tips.push(tip.x);
 }
 for(let j=0;j<base.vertices.length;j++){
  const point=f=>resolved[f][p].vertices[j];const a=point(0),b=point(steps),nextEndpoint=point(steps+1),next=point(1);
  maxLoopVertexDelta=Math.max(maxLoopVertexDelta,Math.hypot(a.x-b.x,a.y-b.y));
  // Compare the same forward difference at t=0 and t=8. Backward vs forward
  // differences at one instant include ordinary acceleration and are not a seam.
  maxLoopVelocityDelta=Math.max(maxLoopVelocityDelta,Math.hypot((next.x-a.x)-(nextEndpoint.x-b.x),(next.y-a.y)-(nextEndpoint.y-b.y))*simFps);
 }
 partMetrics.push({id:d.id,tipTravel:Math.max(...tips)-Math.min(...tips),vertices:base.vertices.length,triangles:base.triangles.length/3});
}
for(const v of trace)for(const [k,n] of Object.entries(v))if(k!=='Drive'&&Math.abs(n)>=0.9999)saturated++;
const tests=[['rig-validation',validation.ok],['no-inverted-or-degenerate-triangles',inversions===0],['root-fixed',maxRoot<1e-8],['periodic-state-convergence',cycleDelta<1e-6],['loop-position',maxLoopVertexDelta<0.05],['loop-velocity',maxLoopVelocityDelta<0.5],['visible-motion-both-parts',partMetrics.every(p=>p.tipTravel>5)],['no-parameter-clipping',saturated===0]];
const metrics={started,ended:new Date().toISOString(),cycles,preRollSeconds:cycles*8,cycleDelta,inversions,minAreaRatio,minStretch,maxStretch,maxRoot,maxLoopVertexDelta,maxLoopVelocityDelta,saturated,partMetrics,tests:tests.map(([name,pass])=>({name,pass})),failed:tests.filter(t=>!t[1]).map(t=>t[0])};
await json('metrics',metrics);console.log('NUMERIC',JSON.stringify(metrics));
// Always preserve diagnostics, even if a numeric acceptance check failed.
const options=screenshotOptionsFromUrl(rig,new URL('http://localhost/?width=640&height=360&padding=0&transparent=0&physics=0&supersample=1'));
for(let i=0;i<fps*seconds;i++){
 const result=await renderRigScreenshot(rig,'.',{...options,values:trace[i*2]});
 await writeFile(`${out}/frames/frame-${String(i).padStart(3,'0')}.png`,result.png);
 if(i%30===0)console.log(`Rendered ${i}/${fps*seconds}`);
}
const endpoint=await renderRigScreenshot(rig,'.',{...options,values:trace[steps]});await writeFile(out+'/loop-endpoint.png',endpoint.png);
const first=decodePng(await readFile(out+'/frames/frame-000.png')),last=decodePng(endpoint.png);
let endpointChangedPixels=0;for(let i=0;i<first.data.length;i+=4)if(first.data.slice(i,i+4).some((n,k)=>n!==last.data[i+k]))endpointChangedPixels++;
const still=await renderRigScreenshot(rig,'.',{...options,values:Object.fromEntries(parameters.map(p=>[p.id,0]))});await writeFile(out+'/neutral.png',still.png);
const sheet={width:640*4,height:360*2,data:new Uint8ClampedArray(640*4*360*2*4)};
for(let k=0;k<8;k++){const im=decodePng(await readFile(`${out}/frames/frame-${String(k*30).padStart(3,'0')}.png`));for(let y=0;y<360;y++)sheet.data.set(im.data.subarray(y*640*4,(y+1)*640*4),(((k>>2)*360+y)*sheet.width+(k%4)*640)*4);}
await writeFile(out+'/contact-sheet.png',encodePng(sheet));
// Bake the simulated parameter samples into the native StandRig motion format.
const motion={format:'standrig-motion',version:1,name:'8 second physics-baked hair and hem',duration:8,tracks:parameters.map(p=>({parameter:p.id,keys:Array.from({length:241},(_,i)=>({time:i/30,value:trace[i*2][p.id]??0}))}))};
validateMotionParameters(parseMotion(motion),parameters);
for(let i=0;i<=240;i++){const values=sampleMotion(motion,i/30);for(const p of parameters)assert.ok(Math.abs(values[p.id]-trace[i*2][p.id])<1e-10);}
metrics.tests.push({name:'native-motion-parse-range-and-241-samples',pass:true});
await json('baked-motion',motion);
// Playback of a baked clip must not apply the pendulum a second time.
await json('baked-fixture.srig',{...rig,name:rig.name+' (baked playback)',physics:{enabled:false,chains:[]}});
const ffmpegArgs=['-y','-framerate','30','-i',out+'/frames/frame-%03d.png','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',out+'/hair-skirt-loop.mp4'];
const encode=spawnSync('ffmpeg',ffmpegArgs,{encoding:'utf8'});
await writeFile(out+'/ffmpeg.log',(encode.stdout??'')+(encode.stderr??'')+String(encode.error??''));
await json('video-command',{command:'ffmpeg',args:ffmpegArgs,exitCode:encode.status});
metrics.mp4=encode.status===0;
metrics.endpointChangedPixels=endpointChangedPixels;metrics.ended=new Date().toISOString();
await json('metrics',metrics);
await writeFile(out+'/LICENSE-ASSETS.txt','Original procedural synthetic hair and skirt artwork created for this experiment. Licensed under Apache-2.0, as the repository LICENSE. No external character artwork, paid API, or SONY project material used.\n');
assert.deepEqual(metrics.failed,[],JSON.stringify(metrics));
console.log('EXPERIMENT PASS',JSON.stringify(metrics));
