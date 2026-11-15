import {writeFile,readFile,readdir} from 'node:fs/promises';
import assert from 'node:assert/strict';
const base='validation/artifacts/';
const tabs=await (await fetch('http://127.0.0.1:9227/json')).json();
const ws=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);
await new Promise(r=>ws.addEventListener('open',r,{once:true}));
let id=0;const pending=new Map(),errors=[];
ws.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(m.error):p.resolve(m.result);}if(m.method==='Runtime.exceptionThrown')errors.push(m.params);});
const call=(method,params={})=>new Promise((resolve,reject)=>{const n=++id;pending.set(n,{resolve,reject});ws.send(JSON.stringify({id:n,method,params}));});
const evaluate=async expression=>(await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true})).result.value;
const delay=ms=>new Promise(r=>setTimeout(r,ms));
await call('Runtime.enable');await call('Page.enable');
await call('Emulation.setDeviceMetricsOverride',{width:800,height:800,deviceScaleFactor:1,mobile:false});
const results=[];
const shared=(await readdir('apps/preview/dist/assets')).find(n=>n.startsWith('dist-')&&n.endsWith('.js'));
try {
for(const renderer of ['canvas','webgl']){
 await call('Page.navigate',{url:'http://127.0.0.1:5186/player?renderer='+renderer});
 let state;
 for(let i=0;i<100;i++){state=await evaluate('({ready:!!document.querySelector("canvas")?.dataset.modelVersion,error:document.querySelector("#error")?.textContent})');if(state?.ready)break;await delay(100);}
 assert.ok(state?.ready,JSON.stringify(state));assert.equal(state.error,'');
 const snap=await call('Page.captureScreenshot',{format:'png'});await writeFile(base+'browser-'+renderer+'.png',Buffer.from(snap.data,'base64'));
 const pixel=await evaluate('(()=>{const c=document.querySelector("canvas"),d=c.getContext("2d").getImageData(0,0,c.width,c.height).data;let n=0;for(let i=3;i<d.length;i+=4)if(d[i])n++;return {width:c.width,height:c.height,opaque:n,revision:c.dataset.playbackRevision};})()');assert.ok(pixel.opaque>0);
 const resp=await fetch('http://127.0.0.1:5186/api/playback/parameters',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({source:'browser-validation',sequence:Date.now(),values:{ParamAngleZ:renderer==='canvas'?-25:25,ParamMouthOpen:0.2}})});assert.equal(resp.status,200,await resp.text());
 for(let i=0;i<50;i++){if(await evaluate('document.querySelector("canvas").dataset.playbackRevision')!==pixel.revision)break;await delay(100);}
 const after=await call('Page.captureScreenshot',{format:'png'});assert.notDeepEqual(Buffer.from(snap.data,'base64'),Buffer.from(after.data,'base64'));
 await writeFile(base+'browser-'+renderer+'-updated.png',Buffer.from(after.data,'base64'));
 results.push({renderer,state,pixel,parameterUpdateChangedScreenshot:true});
}
const webglStatus=await evaluate(`(async()=>{const m=await import('/assets/${shared}'),c=document.createElement('canvas');c.width=240;c.height=240;const p=new m.t(c,await m.r());await p.load();p.setRenderer('webgl');p.setParameters({ParamAngleX:30});const status=p.rendererStatus;p.dispose();return status;})()`);
assert.equal(webglStatus.framePath,'webgl-frame',JSON.stringify(webglStatus));
// Test native sample motion advancing through service playback.
const clip=JSON.parse(await readFile('examples/sample.standrig-motion.json','utf8'));
const post=async body=>{const r=await fetch('http://127.0.0.1:5186/api/playback/motion',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(body)});assert.equal(r.status,200,await r.text());};
await post({action:'load',clip});await post({action:'play'});await delay(150);
const a=await (await fetch('http://127.0.0.1:5186/api/playback')).json();await delay(250);
const b=await (await fetch('http://127.0.0.1:5186/api/playback')).json();
await writeFile(base+'motion-states.json',JSON.stringify({a,b},null,2));assert.notDeepEqual(a.playback.values,b.playback.values);
await post({action:'stop'});
assert.equal(errors.length,0,JSON.stringify(errors));
await writeFile(base+'browser-results.json',JSON.stringify({results,webglStatus,errors,motionParametersAdvanced:true},null,2));
console.log('BROWSER PASS',JSON.stringify(results));
}finally{ws.close();}
