import {store} from '../stores/attribution.js';
import {projects,runs} from '../api/attribution.js';
import {projectSelect,bindProjectSelect} from '../components/common/project-select.js';
import {runList} from '../components/common/run-list.js';
import {resultView} from '../components/common/result-view.js';
import {status} from '../components/common/status.js';
import {esc} from '../utils/format.js';
export async function render(id){
  if(id){
    const r=await runs.get(id);
    return `<div class="eyebrow">04 / RETROSPECTIVE · RUN ${r.id}</div><h1>版本复盘 #${r.id} ${status(r.status)}</h1>
    <div class="checksum">项目 ${esc(r.project_name)} · 基于事件版本 v${r.base_version} · 快照 SHA256 ${r.checksum||'—'} · ${esc((r.created_at||'').replace('T',' ').slice(0,19))} 排队</div>
    ${r.status==='stale'?'<div class="method-note">补报与计算并发:本计算完成时事件版本已前进,按约定未发布为当前结果,仅留档备查。</div>':''}
    ${r.status==='failed'?`<div class="error">计算失败:${esc(r.error)}</div>`:''}
    ${r.status==='superseded'?'<div class="method-note">本版曾被发布,后被更新版本替换;旧版结果仍可在此查阅。</div>':''}
    ${r.is_current?'<div class="method-note">本版即当前发布版本。</div>':''}
    ${r.result?resultView(r):'<p class="method-note">计算在途,结果尚未产生。</p>'}
    <p><a class="button secondary" href="#review">← 返回版本列表</a></p>`;
  }
  const p=store.projects.find(x=>x.id===store.projectId);
  const rows=p?await projects.runs(p.id):[];
  return `<div class="eyebrow">04 / RETROSPECTIVE</div><h1>复盘与版本档案</h1>
  <p>每次计算的配对与分渠道首点率都按版本留档:当前发布、历史已发布、过期未发布均可查对,迟到补报与撤回引起的改派在版本间可追。</p>
  <div class="toolbar">${projectSelect()}</div>
  <h2>版本记录 <small>${rows.length} 次计算</small></h2>${runList(rows)}`;
}
export function bind(refresh){bindProjectSelect(refresh);}
