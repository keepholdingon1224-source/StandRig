import {chromium} from '../work/browser/node_modules/playwright/index.mjs';
import {writeFile,mkdir,readFile} from 'node:fs/promises';
const out=process.cwd()+'/results/006-gui-playback';
const geometryRuns={};
const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
async function capture(label,model,motion){
 const ctx=await browser.newContext({viewport:{width:1280,height:1000},deviceScaleFactor:1});const page=await ctx.newPage();await page.goto('http://127.0.0.1:5180');
 await page.locator('#model-file').setInputFiles(out+'/'+model);await page.locator('#model-import').click();await page.waitForFunction(()=>!document.querySelector('#model-import').disabled);await page.waitForTimeout(300);await page.locator('#motion-file').setInputFiles(out+'/'+motion);await page.waitForTimeout(1000);
 // Camera normalization only: native renderer's existing 18px fit padding,
 // 676x396 CSS canvas -> 640x360 stage at scale 1. Crop padding and composite
 // transparency over the fixed 005 software-renderer background (#eef0f3). No vertex/render override.
 await page.addStyleTag({content:'.stage-panel{position:static!important}.canvas-wrap{width:676px!important;height:396px!important}canvas{width:676px!important;height:396px!important;max-width:none!important}'});
 await page.evaluate(()=>scrollTo(0,0));await page.waitForTimeout(200);await page.screenshot({path:out+'/gui-screenshots/'+label+'-normalized.png'});
 await mkdir(out+'/gui-screenshots/'+label,{recursive:true});
 await page.evaluate(()=>{const proto=CanvasRenderingContext2D.prototype,orig=proto.drawImage,clear=proto.clearRect;window.__triangles=[];proto.clearRect=function(...a){if(this.canvas===document.querySelector('canvas'))window.__triangles=[];return clear.apply(this,a)};proto.drawImage=function(...a){if(this.canvas===document.querySelector('canvas')){const m=this.getTransform();window.__triangles.push([m.a,m.b,m.c,m.d,m.e,m.f]);}return orig.apply(this,a)};});
 const geometry=process.argv.includes('--extra-only')?JSON.parse(await readFile(out+'/gui-'+label+'-draw-matrices.json','utf8')):[];
 for(let i=process.argv.includes('--extra-only')?481:0;i<482;i++){
  const time=i/60;
  if(i<=480)await page.locator('#motion-time').evaluate((e,t)=>{e.step='any';e.value=String(t);e.dispatchEvent(new Event('change',{bubbles:true}));},time);
  if(i<=480)await page.waitForFunction(t=>Math.abs(Number(document.querySelector('#motion-time').value)-t)<.001,time);
  if(i===481)await page.locator('input[aria-label="BakedPhase"]').evaluate((e,t)=>{e.step='any';e.value=String(t);e.dispatchEvent(new Event('input',{bubbles:true}));},time-1e-12);
  await page.waitForTimeout(250);
  geometry[i]=await page.evaluate(()=>window.__triangles);
  if(i>=480||i%2)continue;
  const png=await page.locator('canvas').evaluate(c=>{const n=document.createElement('canvas');n.width=640;n.height=360;const x=n.getContext('2d');x.fillStyle='#eef0f3';x.fillRect(0,0,640,360);x.drawImage(c,18,18,640,360,0,0,640,360);return n.toDataURL('image/png').split(',')[1];});
  await writeFile(out+'/gui-screenshots/'+label+'/frame-'+String(i/2).padStart(3,'0')+'.png',Buffer.from(png,'base64'));
  if(i%60===0)console.log(label,i);
 }
 geometryRuns[label]=geometry;await writeFile(out+'/gui-'+label+'-draw-matrices.json',JSON.stringify(geometry));await ctx.close();
}
await capture('before','005-baked-model.srig','005-baked-motion.json');await capture('reloaded','gui-exported-model.srig','gui-exported-motion.json');await browser.close();
