import {pathToFileURL} from 'node:url';
const {chromium}=await import(pathToFileURL(process.env.PLAYWRIGHT_ENTRY).href);
import {writeFile,mkdir} from 'node:fs/promises';
const out='results/007-character-application',base=process.cwd()+'/'+out;
const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
const ctx=await browser.newContext({viewport:{width:1280,height:1000},acceptDownloads:true});const page=await ctx.newPage();
page.on('console',m=>console.log('browser',m.type(),m.text()));page.on('pageerror',e=>console.log('PAGEERROR',e.message));
const checks=[],loopSamples=[];const shot=async n=>{await page.evaluate(()=>scrollTo(0,0));return page.screenshot({path:base+'/gui-screenshots/'+n+'.png',fullPage:false});};
await page.goto('http://127.0.0.1:5187');await page.waitForTimeout(1000);
await page.locator('#model-file').setInputFiles(base+'/model/character.srig');await page.locator('#model-import').click();await page.waitForFunction(()=>!document.querySelector('#model-import').disabled);await page.waitForTimeout(300);
await page.waitForFunction(()=>document.querySelector('#model-name')?.textContent==='007 original character',{},{timeout:120000});checks.push({name:'model import',pass:true});await shot('01-model');
// Neutral comparison key sits outside the motion interval.
const normalizedStyle=await page.addStyleTag({content:'.stage-panel{position:static!important}.canvas-wrap{width:1188px!important;height:2084px!important}canvas{width:1188px!important;height:2084px!important;max-width:none!important;max-height:none!important}'});
await page.locator('input[aria-label="BakedPhase"]').evaluate(e=>{
  e.step='any';e.value='8.049999999999';e.dispatchEvent(new Event('input',{bubbles:true}));
});
await page.waitForTimeout(1200);
const neutral=await page.locator('canvas').evaluate(canvas=>{
  const crop=document.createElement('canvas');crop.width=1152;crop.height=2048;
  const ctx=crop.getContext('2d');
  ctx.drawImage(canvas,18,18,1152,2048,0,0,1152,2048);
  return {size:[canvas.width,canvas.height],png:crop.toDataURL().split(',')[1]};
});
if(neutral.size[0]!==1188||neutral.size[1]!==2084) throw new Error('Unexpected native canvas size '+neutral.size);
await writeFile(base+'/reconstruction/gui-neutral.png',Buffer.from(neutral.png,'base64'));
await normalizedStyle.evaluate(element=>element.remove());

await page.locator('#motion-file').setInputFiles(base+'/model/character-motion.json');await page.locator('#motion-play').waitFor({state:'visible'});await page.waitForFunction(()=>!document.querySelector('#motion-play').disabled);checks.push({name:'motion import',pass:true});
async function state(){return page.evaluate(()=>fetch('/api/playback/motion').then(r=>r.json()));}
async function click(id){await page.locator(id).click();await page.waitForTimeout(250);}
await click('#motion-play');await page.waitForTimeout(1000);checks.push({name:'play',pass:(await state()).playback.motion.running});await shot('02-playing');
await click('#motion-pause');const a=(await state()).playback.motion.time;await page.waitForTimeout(500);checks.push({name:'pause',pass:(await state()).playback.motion.time===a});await shot('03-paused');
await click('#motion-play');checks.push({name:'resume',pass:(await state()).playback.motion.running});await click('#motion-stop');checks.push({name:'stop',pass:(await state()).playback.motion.time===0});
async function seek(t){await page.locator('#motion-time').evaluate((e,t)=>{e.value=String(t);e.dispatchEvent(new Event('change',{bubbles:true}));},t);await page.waitForFunction(t=>Math.abs(Number(document.querySelector('#motion-time').value)-t)<.001,t);await page.waitForTimeout(70);}
await seek(3);checks.push({name:'seek',pass:Math.abs((await state()).playback.motion.time-3)<1e-8});await shot('04-seek');
await page.locator('#motion-loop').check();await page.waitForTimeout(200);checks.push({name:'loop on',pass:(await state()).playback.motion.loop});await click('#motion-stop');await click('#motion-play');
for(let i=0;i<26;i++){await page.waitForTimeout(1000);loopSamples.push((await state()).playback.motion);if(i%4===0) await shot('loop-'+String(i).padStart(2,'0'));}
const wraps=loopSamples.slice(1).filter((s,i)=>s.time<loopSamples[i].time).length;checks.push({name:'over 3 continuous cycles',pass:(await state()).playback.motion.running&&wraps>=3,wraps});await writeFile(base+'/continuous-loop-samples.json',JSON.stringify(loopSamples,null,2));await click('#motion-pause');await page.locator('#motion-loop').uncheck();await page.waitForTimeout(200);checks.push({name:'loop off',pass:!(await state()).playback.motion.loop});
for(const [id,name]of [['#export-portable','model/gui-exported-model.srig'],['#motion-export','model/gui-exported-motion.json']]){const d=page.waitForEvent('download');await click(id);await(await d).saveAs(base+'/'+name);checks.push({name,pass:true});}
await writeFile(base+'/gui-verification.json',JSON.stringify({checks,status:'in progress'},null,2));
await ctx.close();
const fresh=await browser.newContext({viewport:{width:1280,height:1000}});const p=await fresh.newPage();await p.goto('http://127.0.0.1:5188');await p.locator('#model-file').setInputFiles(base+'/model/gui-exported-model.srig');await p.locator('#model-import').click();await p.waitForFunction(()=>!document.querySelector('#model-import').disabled);await p.waitForTimeout(300);await p.locator('#motion-file').setInputFiles(base+'/model/gui-exported-motion.json');await p.waitForTimeout(1000);await p.locator('#motion-play').click();await p.waitForTimeout(500);await p.locator('#motion-pause').click();const playback=await p.evaluate(()=>fetch('/api/playback/motion').then(r=>r.json()));checks.push({name:'fresh browser and service reload model and playable motion',pass:(await p.locator('#model-name').textContent()==='007 original character')&&playback.playback.motion.time>0&&!playback.playback.motion.running});await p.screenshot({path:base+'/gui-screenshots/05-reloaded.png',fullPage:false});
await writeFile(base+'/gui-verification.json',JSON.stringify({checks,status:checks.every(c=>c.pass)?'pass':'fail',directGuiMp4:false,environment:'Linux Chromium headless'},null,2));await browser.close();
