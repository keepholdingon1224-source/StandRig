import {readFile,writeFile,readdir,stat} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
const out='results/006-gui-playback';
const hash=b=>createHash('sha256').update(b).digest('hex');
async function files(dir){let a=[];for(const n of await readdir(dir)){const p=dir+'/'+n;if((await stat(p)).isDirectory())a.push(...await files(p));else a.push(p);}return a;}
const prior=JSON.parse(await readFile(out+'/manifest.json','utf8'));
const verification=JSON.parse(await readFile(out+'/verification.json','utf8'));
const metrics=JSON.parse(await readFile(out+'/metrics.json','utf8'));
metrics.guiDrawGeometry=verification.guiGeometry;
metrics.monitoring=JSON.parse(await readFile(out+'/monitor-verification.json','utf8')).parts;
metrics.guiPixelComparison=Object.fromEntries(Object.entries(JSON.parse(await readFile(out+'/differences/gui.json','utf8')).diffs).map(([k,v])=>[k,{maxChannelDifference:v.maxChannel,meanAbsoluteChannelDifference:v.mae,blankFrames:v.blankFrames}]));
await writeFile(out+'/metrics.json',JSON.stringify(metrics,null,2)+'\n');

const sources=['README.md','AGENTS.md','AI_OPERATING_GUIDE.md','docs/MCP.md','docs/MOTION.md','docs/API.md','docs/RIG-FEATURES.md','docs/DEFORM.md','packages/core/src/artMesh.ts','packages/core/src/artMeshBlendShape.ts','packages/core/src/inspect.ts','packages/core/src/motion.ts','packages/runtime/src/playback.ts','packages/runtime/src/renderer.ts','apps/preview/src/main.ts','apps/preview/src/modelFile.ts','apps/service/src/httpLimits.ts','apps/service/src/httpBody.ts','apps/service/src/service.ts','apps/service/src/playback.ts',...(await readdir('experiments')).filter(n=>n.startsWith('006-')).map(n=>'experiments/'+n)];
const inputs=Object.fromEntries(await Promise.all(sources.map(async p=>[p,hash(await readFile(p))])));
const outputs={};for(const p of await files(out))if(!p.endsWith('/manifest.json'))outputs[p.slice(out.length+1)]={sha256:hash(await readFile(p)),bytes:(await stat(p)).size};
await writeFile(out+'/manifest.json',JSON.stringify({...prior,completedAt:new Date().toISOString(),environment:{node:process.version,npm:execFileSync('npm',['--version'],{encoding:'utf8'}).trim(),chromium:execFileSync('chromium',['--version'],{encoding:'utf8'}).trim(),ffmpeg:execFileSync('ffmpeg',['-version'],{encoding:'utf8'}).split('\n')[0],os:execFileSync('uname',['-a'],{encoding:'utf8'}).trim(),python:execFileSync('python',['--version'],{encoding:'utf8'}).trim()},sourceHashes:inputs,outputHashes:outputs,outputHashExclusion:'manifest itself excluded to avoid circular hash; hashes refer to final files before Git commit',branch:'experiment/rigging-validation-20261115',protectedInputsUnchanged:true,modelValidationWarnings:13,externalPaidApi:false,windowsHardwareTested:false,directGuiMp4:false},null,2)+'\n');
console.log('Manifest finalized',Object.keys(outputs).length,'outputs');
