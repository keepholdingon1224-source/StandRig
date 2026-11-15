import {readFile,writeFile,mkdir} from 'node:fs/promises';
import assert from 'node:assert/strict';
import path from 'node:path';
import {Client} from '@modelcontextprotocol/client';
import {StdioClientTransport} from '@modelcontextprotocol/client/stdio';
import {createLocalService} from '../apps/service/dist/service.js';
import {decodePng,encodePng} from '@standrig/core/png';
const out=path.resolve('validation/artifacts');
await mkdir(out,{recursive:true});
const service=await createLocalService({dataDir:path.resolve('validation/local-data'),port:5186});
const transport=new StdioClientTransport({command:process.execPath,args:[path.resolve('packages/mcp/src/cli.mjs')],env:{...process.env,STANDRIG_URL:service.url},stderr:'pipe'});
const client=new Client({name:'standrig-validation',version:'1.0.0'});
const evidence={url:service.url};
const save=async(name,data)=>writeFile(path.join(out,name+'.json'),JSON.stringify(data,null,2));
const http=async(route,body)=>{const r=await fetch(service.url+route,{method:body?'POST':'GET',headers:body?{'content-type':'application/json'}:undefined,body:body?JSON.stringify(body):undefined});const data=await r.json();assert.equal(r.status,200,JSON.stringify(data));return data;};
const qa={poseSamples:[{poseId:'neutral',values:{ParamAngleX:0}},{poseId:'half',values:{ParamAngleX:15}},{poseId:'full',values:{ParamAngleX:30}}],regions:['full'],width:240,height:240,physics:false,checkTriangleDistortion:true};
async function invoke(name,args={}) {const r=await client.callTool({name,arguments:args});assert.ok(!r.isError,JSON.stringify(r));return r;}
async function image(name,values={}) {const r=await invoke('standrig_render',{kind:'snapshot',values});const block=r.content.find(c=>c.type==='image');assert.ok(block);await writeFile(path.join(out,name+'.png'),Buffer.from(block.data,'base64'));}
try {
 await client.connect(transport);
 for(const name of ['contract','guide']) await client.readResource({uri:'standrig://docs/'+name});
 evidence.tools=(await client.listTools()).tools.map(t=>t.name);
 let context=(await invoke('standrig_context')).structuredContent.context;
 const sample=await http('/api/sample');
 await save('sample-response-shape',{keys:Object.keys(sample)});
 const rig=sample.rig??sample;
 const request={kind:'import',rig,expectedRevision:context.revision,commit:false,qa};
 const trial=await http('/api/modeling/transaction',request);await save('import-trial',trial);assert.equal(trial.ok,true);
 const imported=await http('/api/modeling/transaction',{...request,commit:true});assert.equal(imported.committed,true);
 context=(await invoke('standrig_context')).structuredContent.context;
 await save('context',context);
 await save('parts',(await invoke('standrig_inspect',{kind:'parts'})).structuredContent);
 const body=(await invoke('standrig_inspect',{kind:'parts',id:'body'})).structuredContent;await save('body-before',body);
 await save('qa-before',(await invoke('standrig_qa_check',qa)).structuredContent);
 await image('before');
 const input={expectedRevision:context.revision,commit:false,qa,operations:[
 {id:'mesh',name:'Synthetic body mesh',target:{partIds:['body']},action:{type:'artmesh-generate',preset:'face-feature',columns:8,rows:8}},
 {id:'bend',name:'Bounded bend',target:{partIds:['body']},action:{type:'deform-brush',brush:{surface:{kind:'artmesh',space:'mesh-local'},center:[60,90],radius:200,effect:{mode:'bend',angle:30,axis:[0,1]},iterations:2,maxDisplacement:15,falloff:'smooth',destination:{kind:'blend-shape',shape:{id:'validation-bend',parameter:'ParamAngleX',neutralInput:0,targetInput:30}}}}}
 ]};
 await save('bend-request',input);
 const dry=(await invoke('standrig_modeling_transaction',input)).structuredContent;await save('bend-trial',dry);assert.equal(dry.ok,true);assert.equal(dry.committed,false);
 assert.equal((await invoke('standrig_context')).structuredContent.context.revision,context.revision);
 const commit=(await invoke('standrig_modeling_transaction',{...input,commit:true})).structuredContent;await save('bend-commit',commit);assert.equal(commit.committed,true);assert.ok(commit.rollbackCheckpoint.id);
 await save('qa-after',(await invoke('standrig_qa_check',qa)).structuredContent);
 for(const [name,x] of [['neutral-after',0],['half',15],['bent',30]]) await image(name,{ParamAngleX:x});
 const imgs=await Promise.all(['before','neutral-after','half','bent'].map(async n=>decodePng(await readFile(path.join(out,n+'.png')))));
 assert.deepEqual(imgs[0].data,imgs[1].data);
 let changed=0;for(let i=0;i<imgs[0].data.length;i+=4)if(imgs[0].data.slice(i,i+4).some((v,j)=>v!==imgs[3].data[i+j]))changed++;
 assert.ok(changed>0);evidence.changedPixels=changed;
 const sheet={width:960,height:240,data:new Uint8ClampedArray(960*240*4)};
 imgs.forEach((im,k)=>{for(let y=0;y<240;y++)sheet.data.set(im.data.subarray(y*240*4,(y+1)*240*4),(y*960+k*240)*4);});
 await writeFile(path.join(out,'comparison.png'),encodePng(sheet));
 await invoke('standrig_playback_parameters',{values:{ParamAngleZ:25,ParamMouthOpen:0.8,ParamAngleX:30}});
 await save('playback',(await invoke('standrig_playback_state')).structuredContent);
 await image('sample-posed',{ParamAngleZ:25,ParamMouthOpen:0.8,ParamAngleX:30});
 await save('evidence',evidence);
 console.log('PROBE PASS',JSON.stringify(evidence));
 if(process.env.KEEP_SERVICE==='1') {console.log('Service retained for browser check');await new Promise(resolve=>process.once('SIGTERM',resolve));}
 await invoke('standrig_restore',{id:commit.rollbackCheckpoint.id,expectedRevision:commit.revisionAfter});
 assert.equal((await invoke('standrig_context')).structuredContent.context.revision,context.revision);
 await save('restore',{ok:true,revision:context.revision});
} finally {await client.close();await transport.close();await service.close();}
