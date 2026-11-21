import {audits} from '../api/attribution.js';
import {table} from '../components/common/table.js';
export async function render(){
  const rows=await audits.list();
  return `<div class="eyebrow">05 / TRACE REGISTER</div><h1>操作留痕</h1><p>登录、项目创建、事件录入/补报/撤回、计算排队、发布与过期均留有可查询记录。显示最近100条。</p>${table(['时间 (UTC)','账号','动作','对象 / 说明'],rows.map(x=>[x.created_at,x.actor,x.action,x.detail]))}`;
}
export function bind(){}
