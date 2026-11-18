import {mkdir, readFile, writeFile} from 'node:fs/promises';
import {validateRig} from '@standrig/core/inspect';
import {createModelBundle} from '@standrig/core/bundle';
import {parseMotion,validateMotionParameters} from '@standrig/core/motion';

const root='results/007-character-application';
const model=JSON.parse(await readFile(root+'/rigging/mesh-and-phase.json','utf8'));
const template=JSON.parse(await readFile('results/005-spatiotemporal-constraints/source-fixture.srig.json','utf8'));
const name='007 original character';
const rig={...template,name,stage:{width:1152,height:2048,background:'#e5e5e5'},
  parameters:[{id:'BakedPhase',label:'BakedPhase',min:0,max:8.05,default:0}],
  assets:[],parts:[],deformers:[],physics:{enabled:false,chains:[]}};
const fixed={origin:[0,0],textureSize:[1152,2048],rest:[[0,0],[1152,0],[0,2048],[1152,2048]],triangles:[[0,1,2],[1,3,2]]};
for(const [order,id] of ['fixed','skirt','left','right'].entries()){
  const part=id==='fixed'?fixed:model[id];
  const path=id==='fixed'?'reconstruction/completed-base.png':`rigging/${id}-texture.png`;
  const [x,y]=part.origin;
  const [width,height]=part.textureSize;
  rig.assets.push({id,name:id,type:'image',width,height,
    src:'data:image/png;base64,'+(await readFile(root+'/'+path)).toString('base64')});
  const vertices=part.rest.map(([vx,vy],i)=>({id:'v-'+i,x:vx-x,y:vy-y,u:(vx-x)/width,v:(vy-y)/height}));
  const bindings=part.samples?[{parameter:'BakedPhase',interpolation:'linear',keys:[...part.samples,part.rest].map((points,i)=>({
    input:i/60,offsets:points.map(([px,py],j)=>({vertexId:vertices[j].id,x:px-part.rest[j][0],y:py-part.rest[j][1]}))
  }))}]:[];
  rig.parts.push({...template.parts[order===1?1:0],id,name:id,assetId:id,drawOrder:order,
    transform:{...template.parts[0].transform,x,y},
    artMesh:{...template.parts[0].artMesh,vertices,triangles:part.triangles.flat(),bindings,blendShapes:[]}});
}
await mkdir(root+'/model',{recursive:true});
const validation=validateRig(rig);
await writeFile(root+'/logs/model-validation.json',JSON.stringify(validation,null,2)+'\n');
if(validation.issues.some(issue=>issue.severity==='error')) throw Error('Rig validation failed');
const motion=parseMotion({format:'standrig-motion',version:1,name,duration:8,
  tracks:[{parameter:'BakedPhase',keys:[{time:0,value:0},{time:8,value:8}]}]});
validateMotionParameters(motion,rig.parameters);
await writeFile(root+'/model/character.srig',JSON.stringify(createModelBundle(rig))+'\n');
await writeFile(root+'/model/character-motion.json',JSON.stringify(motion,null,2)+'\n');
