import {DOMAIN} from '../constants/domain.js';
import {store} from '../stores/attribution.js';
import {esc} from '../utils/format.js';
import {table} from '../components/common/table.js';
import {status} from '../components/common/status.js';
import {runList} from '../components/common/run-list.js';
export function render(){
  const events=store.projects.reduce((n,p)=>n+p.active_touches+p.active_clicks,0);
  return `<div class="eyebrow">ATTRIBUTION LEDGER / ${DOMAIN.direction}</div>
  <section class="hero"><div><h1>${DOMAIN.title}</h1><p class="lead">${DOMAIN.scenario}。</p><a class="button" href="#events">录入触达与点击 →</a></div>
  <aside><span class="folio">${DOMAIN.id.slice(-2)}</span><p>${DOMAIN.algorithm}</p><small>版本化事件 · 守卫式发布 · 明细与首点率同源切换</small></aside></section>
  <section class="strip"><span>${store.projects.length} 个归因项目</span><span>${events} 条在版事件</span><span>${store.runs.length} 次计算记录</span><span>${store.projects.filter(p=>p.current).length} 个项目已发布</span></section>
  <h2>归因项目 <small>约定时窗内一对一配对</small></h2>
  ${table(['项目','约定时窗','渠道','在版触达','在版点击','已撤回','事件版本','当前发布'],store.projects.map(p=>[
    {html:`<a href="#results">${esc(p.name)}</a>`},(p.window_seconds/3600)+' 小时',p.channels.join(' / '),p.active_touches,p.active_clicks,p.withdrawn,'v'+p.event_version,
    p.current?{html:status(p.current.status)+` 运行#${p.current.id} · 配对${p.current.summary?p.current.summary.pairs:'—'}`}:'尚未发布']))}
  <h2>最近计算</h2>${runList(store.runs.slice(0,10),true)}`;
}
export function bind(){}
