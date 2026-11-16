// Synthetic fixture experiment; no PSD/modeling writes, network, AI or paid API.
import {readFile,writeFile,mkdir,copyFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {resolveArtMesh} from '@standrig/core/artMesh';
import {renderRigScreenshot,screenshotOptionsFromUrl} from '@standrig/core/serverRenderer';
import {decodePng,encodePng} from '@standrig/core/png';
import {fileURLToPath} from 'node:url';

export const OUT='results/004-deformation-constraints';
export const load=async p=>JSON.parse(await readFile(p,'utf8'));
export const save=async (p,x)=>writeFile(p,JSON.stringify(x,null,2)+'\n');
export const hash=b=>createHash('sha256').update(b).digest('hex');
export const dist=(a,b)=>Math.hypot(a.x-b.x,a.y-b.y);
export const area=(a,b,c)=>(b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x);
export function edges(mesh){const set=new Map();for(let i=0;i<mesh.triangles.length;i+=3)for(let k=0;k<3;k++){const a=mesh.triangles[i+k],b=mesh.triangles[i+(k+1)%3];set.set([Math.min(a,b),Math.max(a,b)].join(','),[Math.min(a,b),Math.max(a,b)]);}return [...set.values()];}

export function deform(part,values){
 const base=part.artMesh.vertices, h=Math.max(...base.map(v=>v.y)), w=Math.max(...base.map(v=>v.x));
 if(part.id==='hair'){
  // Segment arc length is exactly rest row spacing. Midpoint tangents give
  // continuous curvature; the root tangent/top row remain the original pose.
  const ys=[...new Set(base.map(v=>v.y))].sort((a,b)=>a-b), center=[{x:w/2,y:0}], angles=[0];
  const theta=t=>[0,1,2].reduce((s,k)=>s+0.55*(values[`hair${k}`]??0)*Math.min(1,Math.max(0,6*t-2*k)),0);
  for(let i=1;i<ys.length;i++){const a=theta((ys[i]+ys[i-1])/(2*h)),len=ys[i]-ys[i-1],p=center[i-1];center.push({x:p.x+Math.sin(a)*len,y:p.y+Math.cos(a)*len});angles.push(theta(ys[i]/h));}
  return base.map(v=>{const i=ys.indexOf(v.y),a=angles[i],offset=v.x-w/2;return {...v,x:center[i].x+Math.cos(a)*offset,y:center[i].y-Math.sin(a)*offset};});
 }
 // Position based cloth projection: all triangle edges constrain vertical,
 // horizontal and shear directions. Two-row/two-column links resist bending.
 // Rest lengths, fixed top edge, deterministic ordering; no state reset seam.
 const target=resolveArtMesh(part,w,h,values).vertices;
 const p=target.map(v=>({...v})), links=edges(part.artMesh);
 const index=new Map(base.map((v,i)=>[`${v.x},${v.y}`,i]));
 const dx=w/8,dy=h/16;
 for(let i=0;i<base.length;i++)for(const [x,y] of [[base[i].x+2*dx,base[i].y],[base[i].x,base[i].y+2*dy]]){const j=index.get(`${x},${y}`);if(j!==undefined)links.push([i,j]);}
 const constraints=links.map(([i,j])=>[i,j,dist(base[i],base[j])]);
 // Soft attraction preserves input motion, distance projection reduces texture strain.
 for(let it=0;it<160;it++){
  for(let i=0;i<p.length;i++)if(base[i].v!==0){p[i].x+=(target[i].x-p[i].x)*0.002;p[i].y+=(target[i].y-p[i].y)*0.002;}
  for(const [i,j,len] of constraints){const a=p[i],b=p[j],d=dist(a,b);if(d<1e-12)continue;const wi=base[i].v===0?0:1,wj=base[j].v===0?0:1;if(!wi&&!wj)continue;const c=(d-len)/d/(wi+wj),x=(b.x-a.x)*c,y=(b.y-a.y)*c;a.x+=wi*x;a.y+=wi*y;b.x-=wj*x;b.y-=wj*y;}
 }
 return p;
}
export function framesFor(rig,trace,method){return trace.map(values=>rig.parts.map(part=>method==='003'?resolveArtMesh(part,rig.assets.find(a=>a.id===part.assetId).width,rig.assets.find(a=>a.id===part.assetId).height,values).vertices:deform(part,values)));}
export function measure(rig,frames){
 const parts=rig.parts.map((part,p)=>{
  const b=part.artMesh.vertices,es=edges(part.artMesh), center=b.map((v,i)=>v.u===0.5?i:-1).filter(i=>i>=0).sort((i,j)=>b[i].v-b[j].v), tip=center.at(-1);
  const length=vs=>center.slice(1).reduce((s,j,i)=>s+dist(vs[center[i]],vs[j]),0),rest=length(b);
  const m={id:part.id,vertices:b.length,triangles:part.artMesh.triangles.length/3,edges:es.length,minEdgeRatio:Infinity,maxEdgeRatio:0,minAreaRatio:Infinity,maxAreaRatio:0,minCenterlineRatio:Infinity,maxCenterlineRatio:0,inverted:0,degenerate:0,maxRootDisplacement:0,maxLoopPositionDelta:0,samePhaseVelocityDelta60Hz:0,seamVelocityJump30fps:0,maxOrdinaryVelocityJump30fps:0,maxSpeed60Hz:0,screenClippedElements:0,timeSeries:[]};
  const tips=[];
  for(let f=0;f<frames.length;f++){
   const v=frames[f][p];let emin=Infinity,emax=0;
   for(const [i,j] of es){const r=dist(v[i],v[j])/dist(b[i],b[j]);emin=Math.min(emin,r);emax=Math.max(emax,r);}
   m.minEdgeRatio=Math.min(m.minEdgeRatio,emin);m.maxEdgeRatio=Math.max(m.maxEdgeRatio,emax);
   for(let k=0;k<part.artMesh.triangles.length;k+=3){const ids=part.artMesh.triangles.slice(k,k+3),r=area(...ids.map(i=>v[i]))/area(...ids.map(i=>b[i]));m.minAreaRatio=Math.min(m.minAreaRatio,r);m.maxAreaRatio=Math.max(m.maxAreaRatio,r);if(r<0)m.inverted++;if(Math.abs(r)<=1e-8)m.degenerate++;}
   const cr=length(v)/rest;m.minCenterlineRatio=Math.min(m.minCenterlineRatio,cr);m.maxCenterlineRatio=Math.max(m.maxCenterlineRatio,cr);
   for(let j=0;j<b.length;j++){if(b[j].v===0)m.maxRootDisplacement=Math.max(m.maxRootDisplacement,dist(v[j],b[j]));const x=v[j].x+part.transform.x,y=v[j].y+part.transform.y;if(x<0||x>640||y<0||y>360)m.screenClippedElements++;if(f)m.maxSpeed60Hz=Math.max(m.maxSpeed60Hz,60*dist(v[j],frames[f-1][p][j]));}
   if(f<=480)tips.push(v[tip].x);
   m.timeSeries.push({t:f/60,minEdgeRatio:emin,maxEdgeRatio:emax,centerlineRatio:cr,tipX:v[tip].x,tipY:v[tip].y});
  }
  for(let j=0;j<b.length;j++){
   const v=f=>frames[f][p][j],vd=(a,b,c,d,h)=>Math.hypot((v(b).x-v(a).x)-(v(d).x-v(c).x),(v(b).y-v(a).y)-(v(d).y-v(c).y))*h;
   m.maxLoopPositionDelta=Math.max(m.maxLoopPositionDelta,dist(v(0),v(480)));
   m.samePhaseVelocityDelta60Hz=Math.max(m.samePhaseVelocityDelta60Hz,vd(0,1,480,481,60));
   m.seamVelocityJump30fps=Math.max(m.seamVelocityJump30fps,vd(478,480,0,2,30));
   for(let f=2;f<480;f+=2)m.maxOrdinaryVelocityJump30fps=Math.max(m.maxOrdinaryVelocityJump30fps,vd(f-2,f,f,f+2,30));
  }
  m.tipHorizontalRange=Math.max(...tips)-Math.min(...tips);return m;
 });
 const aggregate={};for(const k of Object.keys(parts[0]))if(typeof parts[0][k]==='number')aggregate[k]=k.startsWith('min')?Math.min(...parts.map(p=>p[k])):Math.max(...parts.map(p=>p[k]));
 const checks=parts.flatMap(p=>Object.entries({edgeRange:p.minEdgeRatio>=0.9&&p.maxEdgeRatio<=1.1,centerline:p.id!=='hair'||p.minCenterlineRatio>=0.97&&p.maxCenterlineRatio<=1.03,tipRange:p.tipHorizontalRange>=(p.id==='hair'?147:48),root:p.maxRootDisplacement<=0.01,triangles:p.inverted===0&&p.degenerate===0,loopPosition:p.maxLoopPositionDelta<=0.05,samePhaseVelocity:p.samePhaseVelocityDelta60Hz<=0.5,seamVelocity:p.seamVelocityJump30fps<=2,screen:p.screenClippedElements===0}).map(([name,pass])=>({name:p.id+':'+name,pass})));
 return {parts,aggregate,checks,pass:checks.every(c=>c.pass)};
}
export function posedRig(rig,vertices){return {...rig,physics:{enabled:false,chains:[]},parts:rig.parts.map((p,i)=>({...p,artMesh:{...p.artMesh,blendShapes:[],vertices:vertices[i]}}))};}
const opts=rig=>screenshotOptionsFromUrl(rig,new URL('http://localhost/?width=640&height=360&padding=0&transparent=0&physics=0&supersample=1'));
export async function render(rig,vs){const r=posedRig(rig,vs);return (await renderRigScreenshot(r,'.',{...opts(r),values:{}})).png;}
function combine(a,b){const im={width:1280,height:360,data:new Uint8ClampedArray(1280*360*4)};for(let y=0;y<360;y++){im.data.set(a.data.subarray(y*2560,(y+1)*2560),y*5120);im.data.set(b.data.subarray(y*2560,(y+1)*2560),y*5120+2560);}return encodePng(im);}
async function main(){
 await mkdir(OUT+'/frames',{recursive:true});await mkdir(OUT+'/comparisons',{recursive:true});await mkdir(OUT+'/code',{recursive:true});await mkdir(OUT+'/logs',{recursive:true});
 const rig=await load('results/003-secondary-loop/fixture.srig.json'),trace=await load('results/003-secondary-loop/physics-trace-60fps.json');
 const baseline=framesFor(rig,trace,'003'),candidate=framesFor(rig,trace,'004');
 const metrics={definitions:{samples:482,interval:'0..8+1/60 inclusive; video t=0..239/30',edges:'all unique triangle edges, deformed/rest Euclidean length',area:'signed double area / rest signed double area; degenerate abs(ratio)<=1e-8',centerline:'sum of all adjacent u=0.5 mesh vertices sorted by v / rest',tip:'u=0.5 v=1 horizontal max-min over 0..8',root:'all v=0 vertices',velocity:'all vertices; same forward difference at 0 and 8, 60Hz; backward and forward at seam, 30fps',camera:'fixed 640x360, padding 0, supersample 1; same transforms/UV/topology/assets',aggregate:'min of minima; max of per-part maxima/counts; per-part complete counts retained'},baseline:measure(rig,baseline),candidate:measure(rig,candidate)};
 await save(OUT+'/metrics.json',metrics);console.log('NUMERIC',JSON.stringify(metrics.candidate.checks));
 await save(OUT+'/geometry-trace.json',candidate.map(parts=>parts.map(vs=>vs.map(v=>({x:v.x,y:v.y})))));
 await copyFile('results/003-secondary-loop/fixture.srig.json',OUT+'/source-fixture.srig.json');await copyFile('results/003-secondary-loop/physics-trace-60fps.json',OUT+'/physics-trace-60fps.json');
 await save(OUT+'/manifest.json',{date:new Date().toISOString(),sourceCommit:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),node:process.version,rights:'003 original procedural Apache-2.0 synthetic fixture. No external character/SONY material, paid services or API.',inputHashes:{fixture:hash(await readFile(OUT+'/source-fixture.srig.json')),physicsTrace:hash(await readFile(OUT+'/physics-trace-60fps.json'))},algorithm:{hair:'fixed-root, exact discrete arc length centerline, tangent local-frame skinning; original signed 0.55 bending coefficient and physics channels',skirt:'160 deterministic position-based projection sweeps, all triangle edges plus 2-grid bending links, 0.002 target attraction per sweep; same original blend-shape target'},reproduce:'node experiments/004-deformation-constraints.mjs && node experiments/004-verify.mjs',scope:'experiment-only geometry evaluation/render adapter; product runtime support for these algorithms is not implemented',notImplemented:['body collision','cloth back artwork','full 3D depth','Windows physical-machine check','human visual-quality approval']});
 for(let i=0;i<240;i++){
  const png=await render(rig,candidate[i*2]);await writeFile(`${OUT}/frames/frame-${String(i).padStart(3,'0')}.png`,png);
  const old=await readFile(`results/003-secondary-loop/frames/frame-${String(i).padStart(3,'0')}.png`);
  await writeFile(`${OUT}/comparisons/frame-${String(i).padStart(3,'0')}.png`,combine(decodePng(old),decodePng(png)));
  if(i%30===0){console.log('render',i);await copyFile(`${OUT}/comparisons/frame-${String(i).padStart(3,'0')}.png`,`${OUT}/comparison-${i/30}s.png`);}
 }
 await writeFile(OUT+'/loop-endpoint.png',await render(rig,candidate[480]));
 for(const f of [0,120,240,360]){
  const image=decodePng(await readFile(`${OUT}/frames/frame-${String(f/2).padStart(3,'0')}.png`));
  const pixel=(x,y)=>{x=Math.round(x);y=Math.round(y);if(x>=0&&x<640&&y>=0&&y<360)image.data.set([235,40,60,255],(y*640+x)*4);};
  for(let p=0;p<rig.parts.length;p++)for(const [i,j] of edges(rig.parts[p].artMesh)){const a=candidate[f][p][i],b=candidate[f][p][j],n=Math.ceil(dist(a,b)*2);for(let k=0;k<=n;k++)pixel(a.x+(b.x-a.x)*k/n+rig.parts[p].transform.x,a.y+(b.y-a.y)*k/n+rig.parts[p].transform.y);}
  await writeFile(`${OUT}/wireframe-${f/60}s.png`,encodePng(image));
 }
 const commands=[['mp4',['-y','-framerate','30','-i',OUT+'/frames/frame-%03d.png','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',OUT+'/hair-skirt-loop.mp4']],['comparison',['-y','-framerate','30','-i',OUT+'/comparisons/frame-%03d.png','-c:v','libx264','-crf','18','-pix_fmt','yuv420p',OUT+'/comparison.mp4']],['gif',['-y','-i',OUT+'/hair-skirt-loop.mp4','-filter_complex','[0:v]split[a][b];[a]palettegen[p];[b][p]paletteuse',OUT+'/preview.gif']]];
 await save(OUT+'/video-commands.json',commands);
 for(const [name,args] of commands){const log=execFileSync('ffmpeg',args,{stdio:['ignore','pipe','pipe']});await writeFile(`${OUT}/logs/${name}-encode.log`,log);}
 await copyFile(import.meta.filename,OUT+'/code/004-deformation-constraints.mjs');
 console.log('SAVED',OUT,'numeric pass:',metrics.candidate.pass);
}
if(process.argv[1]===fileURLToPath(import.meta.url))await main();
