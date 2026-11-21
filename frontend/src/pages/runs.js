import {DOMAIN} from '../constants/domain.js';
import {store,load,pending} from '../stores/attribution.js';
import {projects} from '../api/attribution.js';
import {projectSelect,bindProjectSelect} from '../components/common/project-select.js';
import {runList} from '../components/common/run-list.js';
import {esc} from '../utils/format.js';
export function render(){
  const writable=localStorage.getItem('research-role')!=='viewer';
  const p=store.projects.find(x=>x.id===store.projectId);
  const rows=store.runs.filter(r=>!p||r.project_id===p.id);
  return `<div class="eyebrow">02 / MATCHING WORKSHEET</div><h1>${DOMAIN.field_label}</h1>
  <p class="lead">${DOMAIN.algorithm}</p>
  <div class="method-note">${DOMAIN.note}</div>
  <div class="toolbar">${projectSelect()}</div>
  ${writable&&p?`<form id="recalc-form" class="worksheet"><p>基于当前事件版本 <b>v${p.event_version}</b> 重新配对。同版本已有在途计算时自动去重;计算完成时若事件版本已前进,按约定不得发布为当前结果。</p><button type="submit" ${p.event_version?'':'disabled'}>发起重算 →</button></form>`:'<p class="method-note">观察员可阅读计算记录,分析师与负责人可以发起重算。</p>'}
  ${pending()?'<p class="method-note">有计算在途,本页每2秒自动刷新。</p>':''}
  <h2>计算记录 <small>含过期未发布与历史版本</small></h2>${runList(rows)}`;
}
export function bind(refresh){
  bindProjectSelect(refresh);
  const form=document.getElementById('recalc-form');
  if(form)form.onsubmit=async e=>{
    e.preventDefault();
    try{await projects.recalc(store.projectId);await load();refresh();}
    catch(err){document.getElementById('notice').textContent=err.message;}
  };
}
