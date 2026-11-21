import {projects,runs,overview} from '../api/attribution.js';
export const store={projects:[],runs:[],projectId:0,events:[],current:null};
export async function load(){
  const o=await overview();
  store.projects=o.projects;store.runs=o.runs;
  if(!store.projectId||!store.projects.some(p=>p.id===store.projectId))store.projectId=store.projects[0]?.id||0;
}
export async function loadEvents(){store.events=store.projectId?await projects.events(store.projectId):[];}
export async function loadCurrent(){store.current=store.projectId?await projects.current(store.projectId):null;}
export const pending=()=>store.runs.some(r=>['queued','running'].includes(r.status));
