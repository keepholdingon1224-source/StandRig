import {readFile,writeFile,mkdir,copyFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {load,save,hash,measure,render,edges,dist} from './004-deformation-constraints.mjs';
import {decodePng,encodePng} from '@standrig/core/png';
export const OUT='results/005-spatiotemporal-constraints';
export function attach(rig,frames){return frames.map(f=>f.map((p,i)=>p.map((v,j)=>({...rig.parts[i].artMesh.vertices[j],...v}))));}
export async function regenerate(out='work/005-reproduced'){
 execFileSync('python',['experiments/005-solve.py',out],{env:{...process.env,OPENBLAS_NUM_THREADS:'1'},stdio:'pipe'});
 return load(out+'/geometry-trace.json');
}
const run=(name,args)=>{const r=execFileSync('ffmpeg',['-hide_banner','-loglevel','warning','-y',...args],{stdio:['ignore','pipe','pipe']});return writeFile(OUT+'/logs/'+name+'.log',r);};
export async function main(){
 const rig=await load(OUT+'/source-fixture.srig.json'),raw=await load(OUT+'/geometry-trace.json'),old=await load(OUT+'/baseline-geometry.json'),d=attach(rig,raw),a=attach(rig,old),b=a.map((f,i)=>[d[i][0],f[1]]),c=a.map((f,i)=>[f[0],d[i][1]]);
 const prior=await load(OUT+'/baseline-metrics.json');const metrics={definitions:(await load('results/004-deformation-constraints/metrics.json')).definitions,original:prior.original,baseline:measure(rig,a),hairOnly:measure(rig,b),skirtOnly:measure(rig,c),candidate:measure(rig,d),status:{numeric:'pending independent verification',visual:'ユーザー視覚評価待ち',overall:'未合格（視覚評価待ち）'},baselineVisualApproval:{date:'2026-11-17',rating:'いいよ',requested:'スカートの波打ちを柔らかくしてくれてもいいかも',scope:'004 visual quality provisional approval only',numeric:'004 remains numerically failed; not changed'}};
 await save(OUT+'/metrics.json',metrics);console.log('NUMERIC',JSON.stringify(metrics.candidate.checks));
 const framesets={A:a,B:b,C:c,D:d};
 for(const [id,fs]of Object.entries(framesets)){
  const dir=id==='D'?OUT+'/frames':`work/005-${id}-frames`;await mkdir(dir,{recursive:true});
  for(let i=0;i<240;i++){
   const png=await render(rig,fs[i*2]);await writeFile(`${dir}/frame-${String(i).padStart(3,'0')}.png`,png);
   if(id==='A'&&hash(png)!==hash(await readFile(`results/004-deformation-constraints/frames/frame-${String(i).padStart(3,'0')}.png`)))throw Error('004 image reproduction mismatch '+i);
   if(i%60===0)console.log('render',id,i);
  }
  await run(id+'-encode',['-framerate','30','-i',dir+'/frame-%03d.png','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',OUT+'/'+(id==='D'?'hair-skirt-loop.mp4':id+'-loop.mp4')]);
 }
 await writeFile(OUT+'/loop-endpoint.png',await render(rig,d[480]));
 const mp=OUT+'/hair-skirt-loop.mp4';
 await run('comparison-003-004-005',['-i','results/003-secondary-loop/hair-skirt-loop.mp4','-i',OUT+'/A-loop.mp4','-i',mp,'-filter_complex',"[0:v]drawtext=text='003':x=12:y=12[a];[1:v]drawtext=text='004 A':x=12:y=12[b];[2:v]drawtext=text='005 D':x=12:y=12[c];[a][b][c]hstack=inputs=3",'-c:v','libx264','-crf','18','-pix_fmt','yuv420p',OUT+'/comparison-003-004-005.mp4']);
 await run('ablation',['-i',OUT+'/A-loop.mp4','-i',OUT+'/B-loop.mp4','-i',OUT+'/C-loop.mp4','-i',mp,'-filter_complex',"[0:v]drawtext=text='A 004':x=12:y=12[a];[1:v]drawtext=text='B hair':x=12:y=12[b];[2:v]drawtext=text='C skirt':x=12:y=12[c];[3:v]drawtext=text='D both':x=12:y=12[d];[a][b][c][d]xstack=inputs=4:layout=0_0|640_0|0_360|640_360",'-c:v','libx264','-crf','18','-pix_fmt','yuv420p',OUT+'/comparison-A-B-C-D.mp4']);
 await run('hem-closeup',['-i',OUT+'/A-loop.mp4','-i',mp,'-filter_complex',"[0:v]crop=300:130:270:185,scale=600:260:flags=neighbor,drawtext=text='004 hem 2x':x=10:y=10[a];[1:v]crop=300:130:270:185,scale=600:260:flags=neighbor,drawtext=text='005 hem 2x':x=10:y=10[b];[a][b]hstack=inputs=2",'-c:v','libx264','-crf','18','-pix_fmt','yuv420p',OUT+'/hem-closeup-004-005.mp4']);
 await run('gif',['-i',mp,'-filter_complex','[0:v]split[a][b];[a]palettegen[p];[b][p]paletteuse','-loop','0',OUT+'/preview.gif']);
 await run('three-loops',['-stream_loop','2','-i',mp,'-c','copy',OUT+'/three-loops.mp4']);
 const diagnostic=await load(OUT+'/diagnostics.json');
 const selected=new Set([0,120,240,360,...diagnostic['005'].flatMap(p=>[Math.round(p.worstEdge.time*60),Math.round(p.worstCurvatureChange.time*60)])]);
 for(const f of selected){
  const im=decodePng(await render(rig,d[f]));const pixel=(x,y)=>{x=Math.round(x);y=Math.round(y);if(x>=0&&x<640&&y>=0&&y<360)im.data.set([235,40,60,255],(y*640+x)*4);};
  for(let p=0;p<2;p++)for(const[i,j]of edges(rig.parts[p].artMesh)){
   const u=d[f][p][i],v=d[f][p][j],n=Math.ceil(dist(u,v)*2);for(let k=0;k<=n;k++)pixel(u.x+(v.x-u.x)*k/n+rig.parts[p].transform.x,u.y+(v.y-u.y)*k/n+rig.parts[p].transform.y);
  }
  await writeFile(`${OUT}/wireframe-${f}.png`,encodePng(im));
 }
 for(const file of ['005-prepare.mjs','005-solve.py','005-spatiotemporal-constraints.mjs'])await copyFile('experiments/'+file,OUT+'/code/'+file);
 await save(OUT+'/manifest.json',{date:new Date().toISOString(),sourceCommit:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),branch:execFileSync('git',['branch','--show-current'],{encoding:'utf8'}).trim(),node:process.version,platform:process.platform,python:execFileSync('python',['--version'],{encoding:'utf8'}).trim(),libraries:execFileSync('python',['-c','import scipy,numpy;print("scipy",scipy.__version__,"numpy",numpy.__version__)'],{encoding:'utf8'}).trim(),inputHashes:{fixture:hash(await readFile(OUT+'/source-fixture.srig.json')),physics:hash(await readFile(OUT+'/physics-trace-60fps.json')),baselineGeometry:hash(await readFile('results/004-deformation-constraints/geometry-trace.json'))},condition:'Same original assets/UV/153 vertices per part/256 triangles per part/driving trace/camera640x360/supersample1/video8s30fps240 frames, same phase. No input amplitude or time scale change.',solver:'Offline hair coupled elastic row coefficients; skirt full-cycle periodic temporal/spatial Gaussian displacement regularization of exact 004 distance-projected targets. Not XPBD; not online time integration. Python solver and StandRig native software renderer.',changes:'005 deformation response differs; optimized hair travel ~148px vs004 ~210.5px, explicitly permitted tip mismatch, minimum147 preserved. Skirt time smoothing sigma0.1s and spatial0.65 column; full 8s cycle unchanged; no phase shift, no seam-specific edits, no crossfade or duplicated video endpoint.',variants:{A:'004 reproduction',B:'005 hair,004 skirt',C:'004 hair,005 skirt',D:'both005'},rights:'Original Apache-2.0 synthetic assets from003. No SONY materials/services/credentials, paid APIs, purchases or new engine.',notImplemented:['native GUI integration of005 solver','body collision','full character','Windows hardware validation'],reproduce:'node experiments/005-prepare.mjs && OPENBLAS_NUM_THREADS=1 python experiments/005-solve.py && node experiments/005-spatiotemporal-constraints.mjs && MPLCONFIGDIR=$PWD/work/mpl python experiments/005-plot.py && npm test && node experiments/005-verify.mjs'});
 console.log('Saved all media',metrics.candidate.pass);
}
if(process.argv[1]===fileURLToPath(import.meta.url))await main();
