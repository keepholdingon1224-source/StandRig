import assert from 'node:assert/strict';
import {evaluatePendulumPhysics} from '@standrig/core/pendulumPhysics';
import {load,save} from './004-deformation-constraints.mjs';
const O='results/005-spatiotemporal-constraints';const rig=await load(O+'/source-fixture.srig.json'),trace=await load(O+'/physics-trace-60fps.json'),ranges=new Map(rig.parameters.map(p=>[p.id,p]));
let state;const tick=i=>{const t=i/60,Drive=.72*Math.sin(2*Math.PI*t/8)+.22*Math.sin(4*Math.PI*t/8+.7);const r=evaluatePendulumPhysics(rig.physics.pendulum,ranges,{Drive},1/60,state);state=r.state;return {Drive,...r.outputs};};
let prior,delta=Infinity,cycles=0;
for(let c=0;c<30;c++){const current=Array.from({length:480},(_,i)=>tick(i));if(prior)delta=Math.max(...current.flatMap((v,i)=>Object.keys(v).map(k=>Math.abs(v[k]-prior[i][k]))));prior=current;cycles=c+1;if(c>=2&&delta<1e-8)break;}
let start,end,maxOutputError=0;for(let i=0;i<482;i++){const v=tick(i);for(const k of Object.keys(v))maxOutputError=Math.max(maxOutputError,Math.abs(v[k]-trace[i][k]));if(i===0)start=structuredClone(state);if(i===480)end=structuredClone(state);}
const differences=[];function walk(a,b,path='state'){if(typeof a==='number'){differences.push({path,delta:Math.abs(a-b)});return;}if(a&&typeof a==='object')for(const k of Object.keys(a))walk(a[k],b[k],path+'.'+k);}walk(start,end);
const position= Math.max(...differences.filter(x=>/\.position\./.test(x.path)).map(x=>x.delta)),velocity=Math.max(...differences.filter(x=>/\.velocity\./.test(x.path)).map(x=>x.delta));assert.equal(maxOutputError,0);assert.ok(position<.05&&velocity<.5);assert.ok(delta<1e-8);
await save(O+'/physics-state-verification.json',{pass:true,cycles,cycleOutputDelta:delta,maxOutputError,maxParticlePositionComponentDelta:position,maxParticleVelocityComponentDelta:velocity,units:'native pendulum state units; these are not mesh pixel/s; mesh60Hz velocity is checked independently',start,end,differences});console.log('PASS actual 60Hz pendulum state/output reproduction',cycles,position,velocity);
