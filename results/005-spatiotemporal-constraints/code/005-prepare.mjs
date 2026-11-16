import {mkdir,readFile,writeFile,copyFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {load,save,framesFor,measure,hash} from './004-deformation-constraints.mjs';
const out='results/005-spatiotemporal-constraints';
for(const d of ['logs','code','attempts','frames'])await mkdir(out+'/'+d,{recursive:true});
const rig=await load('results/003-secondary-loop/fixture.srig.json'),trace=await load('results/003-secondary-loop/physics-trace-60fps.json');
const baseline=framesFor(rig,trace,'004'), original=framesFor(rig,trace,'003');
await save(out+'/baseline-geometry.json',baseline.map(f=>f.map(p=>p.map(({x,y})=>({x,y})))));
await copyFile('results/003-secondary-loop/fixture.srig.json',out+'/source-fixture.srig.json');await copyFile('results/003-secondary-loop/physics-trace-60fps.json',out+'/physics-trace-60fps.json');
await save(out+'/baseline-metrics.json',{original:measure(rig,original),baseline:measure(rig,baseline),geometryMatches004:hash(JSON.stringify(baseline.map(f=>f.map(p=>p.map(({x,y})=>({x,y}))))))===hash(JSON.stringify(await load('results/004-deformation-constraints/geometry-trace.json')))});
// Preserve both baseline programs; redirect only 003 output to ignored scratch.
await mkdir('work',{recursive:true});
const code=(await readFile('experiments/003-secondary-loop.mjs','utf8')).replace("out='results/003-secondary-loop'","out='work/005-003-reproduced'");
await writeFile('work/005-003-reproduce.mjs',code);
try{const log=execFileSync(process.execPath,['work/005-003-reproduce.mjs'],{encoding:'utf8'});await writeFile(out+'/logs/003-reproduction.log',log);}catch(e){await writeFile(out+'/logs/003-reproduction.log',String(e.stdout)+String(e.stderr));throw e;}
console.log('Prepared unchanged 003/004 baselines');
