import {DOMAIN} from '../constants/domain.js';
import {store,load,loadEvents,pending} from '../stores/attribution.js';
import {projects} from '../api/attribution.js';
import {projectSelect,bindProjectSelect} from '../components/common/project-select.js';
import {table} from '../components/common/table.js';
import {esc} from '../utils/format.js';
import {bindForm} from '../hooks/forms.js';
import {KIND_LABELS,EVENT_STATE_LABELS} from '../types/enums.js';
function nextNo(kind){const ns=store.events.filter(e=>e.kind===kind).map(e=>e.event_no);return ns.length?Math.max(...ns)+1:1;}
function banner(){
  const p=store.projects.find(x=>x.id===store.projectId);if(!p)return '';
  const cur=p.current?`当前发布 v${p.current.base_version}(运行#${p.current.id})`:'尚未发布结果';
  const tail=p.current&&p.current.base_version===p.event_version?'结果与事件一致':(pending()?'新版本计算在途,完成后自动发布':'有事件未纳入发布,请到"归因计算"发起重算');
  return `<div class="method-note">事件版本 <b>v${p.event_version}</b> · ${cur} · ${tail}。迟到补报与撤回会自动排队重算并改派原配对。</div>`;
}
export async function render(){
  await loadEvents();
  const writable=localStorage.getItem('research-role')!=='viewer';
  const p=store.projects.find(x=>x.id===store.projectId);
  return `<div class="eyebrow">01 / EVENT REGISTER</div><h1>事件录入与补报</h1>
  <p>录入带编号和时间的触达与点击;编号在同项目同类事件内唯一,撤回后不释放。迟到记录按实际发生时间参与配对。</p>
  <div class="toolbar">${projectSelect()}</div>
  ${writable?`<details><summary>新增归因项目</summary><form id="project-form" class="inline-form">
    <label>项目名称<input name="name" required minlength="2" placeholder="如 榆灯·春节全渠道归因"></label>
    <label>约定时窗(小时)<input name="window_hours" type="number" step="0.5" min="0.5" max="720" value="${DOMAIN.defaults.window_hours}" required></label>
    <label>渠道名单(顿号、逗号或空格分隔)<input name="channels" value="${DOMAIN.channels.join('、')}" required></label>
    <label>说明<input name="description" placeholder="业务背景与口径备注"></label>
    <button type="submit">创建项目</button></form></details>`:''}
  ${p?banner():''}
  ${writable&&p?`<h2>录入单条事件</h2><form id="event-form" class="inline-form">
    <label>类型<select name="kind" id="kind-select"><option value="touch">触达</option><option value="click">点击</option></select></label>
    <label>事件编号<input name="event_no" id="event-no" type="number" min="1" value="${nextNo('touch')}" required></label>
    <label>同一人标识<input name="person" placeholder="如 U101" required maxlength="60"></label>
    <label id="channel-field">渠道<select name="channel">${p.channels.map(c=>`<option>${esc(c)}</option>`).join('')}</select></label>
    <label>发生时间<input name="occurred_at" type="datetime-local" step="60" required></label>
    <button type="submit">保存并触发重算</button></form>
  <details><summary>批量补报(JSON 数组,整批校验,任一非法整批拒绝)</summary>
    <form id="batch-form"><label>事件数组<textarea name="payload" placeholder='[{"kind":"touch","event_no":21,"person":"U109","channel":"短信","occurred_at":"2026-11-12T09:00:00Z"}]'></textarea></label>
    <button type="submit">校验并补报</button></form></details>`:''}
  <h2>事件明细 <small>${store.events.length} 条 · 撤回即触发重算改派</small></h2>
  ${table(['类型','编号','同一人','渠道','发生时间 (UTC)','录入时间 (UTC)','录入版本','状态',...(writable?['操作']:[])],
    store.events.map(e=>[KIND_LABELS[e.kind],(e.kind==='touch'?'T':'C')+e.event_no,e.person,e.channel||'—',
      esc(e.occurred_at.replace('T',' ').slice(0,16)),esc(e.received_at.replace('T',' ').slice(0,16)),'v'+e.version_added,
      EVENT_STATE_LABELS[e.status]+(e.version_withdrawn?` (v${e.version_withdrawn}撤回)`:''),
      ...(writable?[{html:e.status==='active'?`<button class="text" data-withdraw="${e.kind}:${e.event_no}">撤回</button>`:''}]:[])]))}`;
}
export function bind(refresh){
  bindProjectSelect(refresh);
  bindForm('project-form',async data=>{
    const channels=data.channels.split(/[、,,\s]+/).filter(Boolean);
    const p=await projects.create({name:data.name,window_hours:+data.window_hours,channels,description:data.description||''});
    store.projectId=p.id;await load();refresh();
  });
  const kindSel=document.getElementById('kind-select');
  if(kindSel)kindSel.onchange=()=>{
    document.getElementById('event-no').value=nextNo(kindSel.value);
    document.getElementById('channel-field').style.visibility=kindSel.value==='touch'?'visible':'hidden';
  };
  bindForm('event-form',async data=>{
    const body={kind:data.kind,event_no:+data.event_no,person:data.person,
      channel:data.kind==='touch'?data.channel:'',occurred_at:new Date(data.occurred_at).toISOString()};
    await projects.addEvent(store.projectId,body);await load();refresh();
  });
  bindForm('batch-form',async data=>{
    let arr;try{arr=JSON.parse(data.payload);}catch{throw new Error('JSON 解析失败,请检查格式');}
    if(!Array.isArray(arr)||!arr.length)throw new Error('须为非空 JSON 数组');
    await projects.batch(store.projectId,arr);await load();refresh();
  });
  document.querySelectorAll('[data-withdraw]').forEach(el=>el.onclick=async()=>{
    try{
      const [kind,no]=el.dataset.withdraw.split(':');
      await projects.withdraw(store.projectId,{kind,event_no:+no});await load();refresh();
    }catch(e){document.getElementById('notice').textContent=e.message;}
  });
}
