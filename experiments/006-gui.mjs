import {chromium} from '../work/browser/node_modules/playwright/index.mjs';
import {writeFile,mkdir} from 'node:fs/promises';
const out='results/006-gui-playback',base=process.cwd()+'/'+out;
const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
const ctx=await browser.newContext({viewport:{width:1280,height:1000},acceptDownloads:true});const page=await ctx.newPage();
page.on('console',m=>console.log('browser',m.type(),m.text()));page.on('pageerror',e=>console.log('PAGEERROR',e.message));
const checks=[],loopSamples=[];const shot=async n=>{await page.evaluate(()=>scrollTo(0,0));return page.screenshot({path:base+'/gui-screenshots/'+n+'.png',fullPage:true});};
await page.goto('http://127.0.0.1:5182');await page.waitForTimeout(1000);
await page.locator('#model-file').setInputFiles(base+'/005-baked-model.srig');await page.locator('#model-import').click();await page.waitForFunction(()=>!document.querySelector('#model-import').disabled);await page.waitForTimeout(300);
await page.waitForFunction(()=>document.querySelector('#model-name')?.textContent==='005 baked native playback',{},{timeout:120000});checks.push({name:'model import',pass:true});await shot('01-model');
await page.locator('#motion-file').setInputFiles(base+'/005-baked-motion.json');await page.locator('#motion-play').waitFor({state:'visible'});await page.waitForFunction(()=>!document.querySelector('#motion-play').disabled);checks.push({name:'motion import',pass:true});
async function state(){return page.evaluate(()=>fetch('/api/playback/motion').then(r=>r.json()));}
async function click(id){await page.locator(id).click();await page.waitForTimeout(250);}
await click('#motion-play');await page.waitForTimeout(1000);checks.push({name:'play',pass:(await state()).playback.motion.running});await shot('02-playing');
await click('#motion-pause');const a=(await state()).playback.motion.time;await page.waitForTimeout(500);checks.push({name:'pause',pass:(await state()).playback.motion.time===a});await shot('03-paused');
await click('#motion-play');checks.push({name:'resume',pass:(await state()).playback.motion.running});await click('#motion-stop');checks.push({name:'stop',pass:(await state()).playback.motion.time===0});
async function seek(t){await page.locator('#motion-time').evaluate((e,t)=>{e.value=String(t);e.dispatchEvent(new Event('change',{bubbles:true}));},t);await page.waitForFunction(t=>Math.abs(Number(document.querySelector('#motion-time').value)-t)<.001,t);await page.waitForTimeout(70);}
await seek(3);checks.push({name:'seek',pass:Math.abs((await state()).playback.motion.time-3)<1e-8});await shot('04-seek');
await page.locator('#motion-loop').check();await page.waitForTimeout(200);checks.push({name:'loop on',pass:(await state()).playback.motion.loop});await click('#motion-stop');await click('#motion-play');
for(let i=0;i<26;i++){await page.waitForTimeout(1000);loopSamples.push((await state()).playback.motion);await shot('loop-'+String(i).padStart(2,'0'));}
const wraps=loopSamples.slice(1).filter((s,i)=>s.time<loopSamples[i].time).length;checks.push({name:'over 3 continuous cycles',pass:(await state()).playback.motion.running&&wraps>=3,wraps});await writeFile(base+'/continuous-loop-samples.json',JSON.stringify(loopSamples,null,2));await click('#motion-pause');await page.locator('#motion-loop').uncheck();await page.waitForTimeout(200);checks.push({name:'loop off',pass:!(await state()).playback.motion.loop});
for(const [id,name]of [['#export-portable','gui-exported-model.srig'],['#motion-export','gui-exported-motion.json']]){const d=page.waitForEvent('download');await click(id);await(await d).saveAs(base+'/'+name);checks.push({name,pass:true});}
await writeFile(base+'/gui-verification.json',JSON.stringify({checks,status:'in progress'},null,2));
await ctx.close();
const fresh=await browser.newContext({viewport:{width:1280,height:1000}});const p=await fresh.newPage();await p.goto('http://127.0.0.1:5182');await p.locator('#model-file').setInputFiles(base+'/gui-exported-model.srig');await p.locator('#model-import').click();await p.waitForFunction(()=>!document.querySelector('#model-import').disabled);await p.waitForTimeout(300);await p.locator('#motion-file').setInputFiles(base+'/gui-exported-motion.json');await p.waitForTimeout(1000);await p.locator('#motion-play').click();await p.waitForTimeout(500);await p.locator('#motion-pause').click();checks.push({name:'fresh browser session exported files reload',pass:await p.locator('#model-name').textContent()==='005 baked native playback'});await p.screenshot({path:base+'/gui-screenshots/05-reloaded.png',fullPage:true});
await writeFile(base+'/gui-verification.json',JSON.stringify({checks,status:checks.every(c=>c.pass)?'pass':'fail',directGuiMp4:false,environment:'Linux Chromium headless'},null,2));await browser.close();
