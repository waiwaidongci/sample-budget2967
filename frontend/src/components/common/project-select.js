import {store} from '../../stores/attribution.js';
import {esc} from '../../utils/format.js';
export const projectSelect=()=>store.projects.length
  ?`<label>归因项目<select id="project-select" name="project_id">${store.projects.map(p=>`<option value="${p.id}" ${p.id===store.projectId?'selected':''}>${esc(p.name)} · v${p.event_version}</option>`).join('')}</select></label>`
  :'<p class="method-note">尚无归因项目,请先在事件录入页创建。</p>';
export function bindProjectSelect(refresh){const sel=document.getElementById('project-select');if(sel)sel.onchange=()=>{store.projectId=+sel.value;refresh();};}
