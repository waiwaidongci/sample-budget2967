import {store,loadCurrent,pending} from '../stores/attribution.js';
import {projectSelect,bindProjectSelect} from '../components/common/project-select.js';
import {resultView} from '../components/common/result-view.js';
import {status} from '../components/common/status.js';
import {esc} from '../utils/format.js';
export async function render(){
  await loadCurrent();
  const p=store.projects.find(x=>x.id===store.projectId);
  const run=store.current?.run;
  return `<div class="eyebrow">03 / CURRENT PUBLICATION</div><h1>当前发布结果</h1>
  <p>本页只展示当前发布指针指向的版本;配对明细与分渠道首点率来自同一版事件、同一事务一次性切换,不会出现两边版本不一致。</p>
  <div class="toolbar">${projectSelect()}</div>
  ${run?`<h2>${esc(run.project_name)} ${status(run.status)}</h2>
    <div class="checksum">事件版本 v${run.base_version} · 事件快照 SHA256 ${run.checksum} · 发布于 ${esc((run.finished_at||'').replace('T',' ').slice(0,19))}</div>
    ${p&&p.event_version>run.base_version?`<div class="method-note">事件已前进到 v${p.event_version},${pending()?'新计算在途,完成后本页一次性切换到新版本':'请到"归因计算"发起重算'}。</div>`:''}
    ${resultView(run)}`
  :`<div class="method-note">项目「${esc(p?.name||'')}」尚未发布归因结果。录入事件后系统会自动排队计算,也可到"归因计算"手动发起。</div>`}`;
}
export function bind(refresh){bindProjectSelect(refresh);}
