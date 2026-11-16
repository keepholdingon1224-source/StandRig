// Independent checks on saved geometry/media; acceptance failures are preserved
// and produce exit 1. Integrity failures are separate from research targets.
import {readFile,writeFile,readdir,copyFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import assert from 'node:assert/strict';
import {decodePng} from '@standrig/core/png';
import {load,save,hash,render,framesFor} from './004-deformation-constraints.mjs';
import {OUT,attach,regenerate} from './005-spatiotemporal-constraints.mjs';
const tests=[];
async function check(name,fn){try{await fn();tests.push({name,pass:true});}catch(e){tests.push({name,pass:false,error:e.message});}}
const rig=await load(OUT+'/source-fixture.srig.json'),trace=await load(OUT+'/physics-trace-60fps.json'),frames=await load(OUT+'/geometry-trace.json'),metrics=await load(OUT+'/metrics.json');
await check('identical-003-inputs',async()=>{
 for(const [a,b] of [['source-fixture.srig','fixture.srig'],['physics-trace-60fps','physics-trace-60fps']])assert.equal(hash(await readFile(`${OUT}/${a}.json`)),hash(await readFile(`results/003-secondary-loop/${b}.json`)));
});
await check('003-actual-reproduction',async()=>{

 const original=await load('results/003-secondary-loop/metrics.json'),actual=await load('work/005-003-reproduced/metrics.json');
 for(const k of ['cycles','cycleDelta','minAreaRatio','minStretch','maxStretch','maxRoot','maxLoopVertexDelta','maxLoopVelocityDelta','inversions'])assert.equal(actual[k],original[k]);
 assert.deepEqual(actual.partMetrics,original.partMetrics);
 const names=(await readdir('results/003-secondary-loop/frames')).filter(n=>/^frame-\d{3}\.png$/.test(n));let equal=0;
 for(const n of names){assert.equal(hash(await readFile('results/003-secondary-loop/frames/'+n)),hash(await readFile('work/005-003-reproduced/frames/'+n)));equal++;}
 await save(OUT+'/baseline-reproduction.json',{pass:true,framesByteIdentical:equal,metrics:actual,command:'node work/005-003-reproduce.mjs; exact 003 code with output path redirected only',originalCodeHash:hash(await readFile('experiments/003-secondary-loop.mjs')),redirectedCodeHash:hash(await readFile('work/005-003-reproduce.mjs'))});
});
const inspected=[];
await check('independent-all-element-geometry-measurement',()=>{
 assert.equal(frames.length,482);
 for(let p=0;p<rig.parts.length;p++){
  const part=rig.parts[p],base=part.artMesh.vertices,reported=metrics.candidate.parts[p],edgeSet=new Set();
  for(let k=0;k<part.artMesh.triangles.length;k+=3)for(let j=0;j<3;j++){const a=part.artMesh.triangles[k+j],b=part.artMesh.triangles[k+(j+1)%3];edgeSet.add([a,b].sort((x,y)=>x-y).join(','));}
  const edgeList=[...edgeSet].map(e=>e.split(',').map(Number));
  const distance=(a,b)=>Math.sqrt((a.x-b.x)**2+(a.y-b.y)**2),cross=(a,b,c)=>(b.x-a.x)*(c.y-a.y)-(c.x-a.x)*(b.y-a.y);
  const center=base.map((v,i)=>({v,i})).filter(o=>o.v.u===.5).sort((a,b)=>a.v.v-b.v.v).map(o=>o.i);
  const length=vs=>center.slice(1).reduce((s,j,i)=>s+distance(vs[center[i]],vs[j]),0),restLength=length(base);
  let minEdge=Infinity,maxEdge=0,minArea=Infinity,maxArea=-Infinity,minLength=Infinity,maxLength=0,root=0,inverted=0,degenerate=0,clipped=0,minTip=Infinity,maxTip=-Infinity;
  for(let f=0;f<frames.length;f++){
   const v=frames[f][p];assert.equal(v.length,base.length);
   for(let j=0;j<v.length;j++){assert.ok(Number.isFinite(v[j].x)&&Number.isFinite(v[j].y));if(base[j].v===0)root=Math.max(root,distance(v[j],base[j]));const x=v[j].x+part.transform.x,y=v[j].y+part.transform.y;if(x<0||x>640||y<0||y>360)clipped++;}
   for(const [a,b]of edgeList){const ratio=distance(v[a],v[b])/distance(base[a],base[b]);minEdge=Math.min(minEdge,ratio);maxEdge=Math.max(maxEdge,ratio);}
   for(let k=0;k<part.artMesh.triangles.length;k+=3){const [a,b,c]=part.artMesh.triangles.slice(k,k+3),ratio=cross(v[a],v[b],v[c])/cross(base[a],base[b],base[c]);minArea=Math.min(minArea,ratio);maxArea=Math.max(maxArea,ratio);if(ratio<0)inverted++;if(Math.abs(ratio)<=1e-8)degenerate++;}
   const l=length(v)/restLength;minLength=Math.min(minLength,l);maxLength=Math.max(maxLength,l);
   if(f<=480){minTip=Math.min(minTip,v[center.at(-1)].x);maxTip=Math.max(maxTip,v[center.at(-1)].x);}
  }
  const m={minEdgeRatio:minEdge,maxEdgeRatio:maxEdge,minAreaRatio:minArea,maxAreaRatio:maxArea,minCenterlineRatio:minLength,maxCenterlineRatio:maxLength,maxRootDisplacement:root,inverted,degenerate,screenClippedElements:clipped,tipHorizontalRange:maxTip-minTip};
  let pos=0,phase=0,seam=0,ordinary=0,speed=0;
  for(let j=0;j<base.length;j++){
   const v=f=>frames[f][p][j],diff=(a,b,c,d,fps)=>Math.hypot((v(b).x-v(a).x)-(v(d).x-v(c).x),(v(b).y-v(a).y)-(v(d).y-v(c).y))*fps;
   pos=Math.max(pos,distance(v(0),v(480)));phase=Math.max(phase,diff(0,1,480,481,60));seam=Math.max(seam,diff(478,480,0,2,30));
   for(let f=1;f<482;f++)speed=Math.max(speed,60*distance(v(f-1),v(f)));
   for(let f=2;f<480;f+=2)ordinary=Math.max(ordinary,diff(f-2,f,f,f+2,30));
  }
  Object.assign(m,{maxLoopPositionDelta:pos,samePhaseVelocityDelta60Hz:phase,seamVelocityJump30fps:seam,maxOrdinaryVelocityJump30fps:ordinary,maxSpeed60Hz:speed});
  for(const [k,v] of Object.entries(m))assert.ok(Math.abs(v-reported[k])<1e-9,`${part.id}:${k} ${v} != ${reported[k]}`);
  inspected.push({id:part.id,samples:frames.length,edgeObservations:frames.length*edgeList.length,triangleObservations:frames.length*part.artMesh.triangles.length/3,metrics:m});
 }
});
await check('reproducibility-full-482-sample-geometry',async()=>{
 const rerun=await regenerate();assert.equal(hash(JSON.stringify(rerun)),hash(JSON.stringify(frames)));
});
await check('saved-geometry-render-and-no-endpoint-substitution',async()=>{
 // Every image, including genuine last time 239/30, is checked against saved
 // geometry rendered through the same StandRig UV-preserving adapter.
 for(let f=0;f<240;f++){
  const vertices=frames[f*2].map((vs,p)=>vs.map((v,j)=>({...rig.parts[p].artMesh.vertices[j],...v})));
  assert.equal(hash(await render(rig,vertices)),hash(await readFile(`${OUT}/frames/frame-${String(f).padStart(3,'0')}.png`)),`frame ${f}`);
 }
 assert.notEqual(hash(await readFile(OUT+'/frames/frame-239.png')),hash(await readFile(OUT+'/frames/frame-000.png')));
});
let blankFrames=0,clippedFrames=0;
await check('all-240-PNG-decode-dimensions-and-pixel-bounds',async()=>{
 const names=(await readdir(OUT+'/frames')).filter(n=>/^frame-\d{3}\.png$/.test(n));assert.equal(names.length,240);
 for(const n of names){const im=decodePng(await readFile(OUT+'/frames/'+n));assert.equal(im.width,640);assert.equal(im.height,360);const bg=Array.from(im.data.slice(0,4));let count=0,edge=false;
  for(let y=0;y<360;y++)for(let x=0;x<640;x++){const i=(y*640+x)*4;if(bg.some((c,k)=>c!==im.data[i+k])){count++;if(x===0||x===639||y===0||y===359)edge=true;}}
  if(!count)blankFrames++;if(edge)clippedFrames++;
 }
 assert.equal(blankFrames,0);assert.equal(clippedFrames,0);
});
for(const [file,width]of [['hair-skirt-loop.mp4',640],['A-loop.mp4',640],['B-loop.mp4',640],['C-loop.mp4',640],['comparison-003-004-005.mp4',1920],['comparison-A-B-C-D.mp4',1280],['hem-closeup-004-005.mp4',1200]])await check(file+':full-decode-and-specification',async()=>{
 const probe=JSON.parse(execFileSync('ffprobe',['-v','error','-count_frames','-show_streams','-show_format','-of','json',OUT+'/'+file],{encoding:'utf8'}));const s=probe.streams[0];assert.equal(s.width,width);assert.equal(s.height,file==='comparison-A-B-C-D.mp4'?720:file==='hem-closeup-004-005.mp4'?260:360);assert.equal(s.r_frame_rate,'30/1');assert.equal(Number(s.nb_read_frames),240);assert.equal(Number(probe.format.duration),8);
 execFileSync('ffmpeg',['-v','error','-xerror','-i',OUT+'/'+file,'-f','null','-'],{stdio:'pipe'});
 await writeFile(OUT+'/'+file+'.probe.json',JSON.stringify(probe,null,2));
});
await check('GIF-full-decode-loop-and-duration',async()=>{
 const bytes=await readFile(OUT+'/preview.gif');assert.ok(bytes.includes(Buffer.from('NETSCAPE2.0')));
 const p=JSON.parse(execFileSync('ffprobe',['-v','error','-count_frames','-show_streams','-show_format','-of','json',OUT+'/preview.gif'],{encoding:'utf8'}));assert.equal(Number(p.streams[0].nb_read_frames),240);assert.ok(Math.abs(Number(p.format.duration)-8)<0.03);
 execFileSync('ffmpeg',['-v','error','-xerror','-i',OUT+'/preview.gif','-f','null','-'],{stdio:'pipe'});
});
await check('official-npm-test',async()=>{const log=await readFile(OUT+'/logs/npm-test-final.log','utf8');assert.match(log,/tests 183/);assert.match(log,/pass 183/);assert.match(log,/fail 0/);assert.match(log,/"passed":true,"checks":16/);});
await check('004-reproduction-all-geometry-and-images',async()=>{
 assert.equal(hash(JSON.stringify(await load(OUT+'/baseline-geometry.json'))),hash(JSON.stringify(await load('results/004-deformation-constraints/geometry-trace.json'))));
 for(let f=0;f<240;f++){const n=`frame-${String(f).padStart(3,'0')}.png`;assert.equal(hash(await readFile('work/005-A-frames/'+n)),hash(await readFile('results/004-deformation-constraints/frames/'+n)));}
});
await check('ablation-isolation-and-003-004-common-definitions',async()=>{
 assert.deepEqual(metrics.hairOnly.parts[0],metrics.candidate.parts[0]);assert.deepEqual(metrics.hairOnly.parts[1],metrics.baseline.parts[1]);assert.deepEqual(metrics.skirtOnly.parts[0],metrics.baseline.parts[0]);assert.deepEqual(metrics.skirtOnly.parts[1],metrics.candidate.parts[1]);
 const old=await load('results/004-deformation-constraints/metrics.json');assert.deepEqual(metrics.baseline,old.candidate);assert.deepEqual(metrics.original,old.baseline);assert.deepEqual(metrics.definitions,old.definitions);
});
await check('protected-baseline-and-product-files-unchanged',()=>{
 const paths=execFileSync('git',['diff','15020757c16e8652cc356ccbab057719b2259b0c','--name-only','--','results/003-secondary-loop','results/004-deformation-constraints','experiments/003-secondary-loop.mjs','experiments/003-verify.mjs','experiments/004-deformation-constraints.mjs','experiments/004-verify.mjs','experiments/004-plot.py','packages','apps'],{encoding:'utf8'});assert.equal(paths,'');
});
await check('three-loops-720-frames-full-decode',()=>{
 const p=JSON.parse(execFileSync('ffprobe',['-v','error','-count_frames','-show_streams','-show_format','-of','json',OUT+'/three-loops.mp4'],{encoding:'utf8'}));assert.equal(Number(p.streams[0].nb_read_frames),720);assert.equal(Number(p.format.duration),24);execFileSync('ffmpeg',['-v','error','-xerror','-i',OUT+'/three-loops.mp4','-f','null','-'],{stdio:'pipe'});
});
await check('independent-monitoring-and-native-physical-state',async()=>{
 for(const [script,log] of [['005-monitor-verify.py','monitor-verification'],['005-physics-verify.mjs','physics-verification']]){
  const result=execFileSync(script.endsWith('.py')?'python':process.execPath,['experiments/'+script],{encoding:'utf8'});await writeFile(OUT+'/logs/'+log+'.log',result);
 }
 assert.equal((await load(OUT+'/monitor-verification.json')).pass,true);assert.equal((await load(OUT+'/physics-state-verification.json')).pass,true);
});
const acceptance=inspected.flatMap(({id,metrics:m})=>Object.entries({edgeRange:m.minEdgeRatio>=.90&&m.maxEdgeRatio<=1.10,centerline:id!=='hair'||m.minCenterlineRatio>=.97&&m.maxCenterlineRatio<=1.03,tipRange:m.tipHorizontalRange>=(id==='hair'?147:48),root:m.maxRootDisplacement<=.01,triangles:m.inverted===0&&m.degenerate===0,loopPosition:m.maxLoopPositionDelta<=.05,samePhaseVelocity:m.samePhaseVelocityDelta60Hz<=.5,seamVelocity:m.seamVelocityJump30fps<=2,screen:m.screenClippedElements===0}).map(([name,pass])=>({name:id+':'+name,pass})));
const result={date:new Date().toISOString(),integrityPass:tests.every(t=>t.pass),numericalAcceptancePass:acceptance.length===18&&acceptance.every(t=>t.pass),tests,acceptance,inspected,blankFrames,clippedFrames,visualQuality:'005ユーザー視覚評価待ち。004視覚品質は2026-11-17暫定承認、004数値不合格は維持。' ,notTested:['Windows physical machine','body collision','cloth back artwork','full 3D depth','native interactive playback of new solver','human visual review']};
await save(OUT+'/verification.json',result);await copyFile(import.meta.filename,OUT+'/code/005-verify.mjs');console.log(JSON.stringify(result,null,2));
if(!result.integrityPass||!result.numericalAcceptancePass)process.exitCode=1;
