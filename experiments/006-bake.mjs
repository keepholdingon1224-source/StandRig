import {readFile,writeFile,mkdir,readdir} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {load,save,hash} from './004-deformation-constraints.mjs';
import {validateRig} from '@standrig/core/inspect';
import {createModelBundle} from '@standrig/core/bundle';
import {parseMotion,validateMotionParameters} from '@standrig/core/motion';
const out='results/006-gui-playback',base='results/005-spatiotemporal-constraints';
for(const d of ['logs','frames','differences','gui-screenshots'])await mkdir(out+'/'+d,{recursive:true});
const files=['source-fixture.srig.json','geometry-trace.json','physics-trace-60fps.json','metrics.json','verification.json','FINAL-ACCEPTANCE.md','hair-skirt-loop.mp4','three-loops.mp4',...(await readdir(base+'/frames')).filter(n=>n.endsWith('.png')).sort().map(n=>'frames/'+n)];
const hashes=Object.fromEntries(await Promise.all(files.map(async n=>[n,hash(await readFile(base+'/'+n))])));
await save(out+'/baseline-hashes.json',{commit:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),directory:base,sha256:hashes});
const rig=await load(base+'/source-fixture.srig.json'),frames=await load(base+'/geometry-trace.json');
rig.name='005 baked native playback';rig.parameters=[{id:'BakedPhase',label:'005 phase (seconds)',min:0,max:481/60,default:0}];rig.physics={enabled:false,chains:[]};
for(let p=0;p<rig.parts.length;p++){
 const m=rig.parts[p].artMesh;
 m.blendShapes=[];m.multiBindings=[];
 m.bindings=[{parameter:'BakedPhase',interpolation:'linear',keys:frames.map((f,i)=>({input:i/60,offsets:f[p].map((v,j)=>({vertexId:m.vertices[j].id,x:v.x-m.vertices[j].x,y:v.y-m.vertices[j].y}))}))}];
}
const validation=validateRig(rig);await save(out+'/model-validation.json',validation);
if(validation.issues.some(i=>i.severity==='error'))throw Error('invalid model');
const motion=parseMotion({format:'standrig-motion',version:1,name:'005 baked 8-second cycle',duration:8,tracks:[{parameter:'BakedPhase',keys:[{time:0,value:0},{time:8,value:8}]}]});validateMotionParameters(motion,rig.parameters);
await writeFile(out+'/005-baked-model.srig',JSON.stringify(createModelBundle(rig))+'\n');await save(out+'/005-baked-motion.json',motion);
await save(out+'/manifest.json',{date:new Date().toISOString(),baselineCommit:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),node:process.version,platform:process.platform,method:'Existing native ArtMesh single-parameter linear offset keys; 482 samples; one motion track/two keys; no solver rerun; disabled physics',inputs:hashes});
console.log('Native bake complete',validation);
