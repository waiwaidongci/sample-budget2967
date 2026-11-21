import {table} from './table.js';
import {esc} from '../../utils/format.js';
export function wait(s){s=Number(s);if(s<60)return s+'秒';if(s<3600)return Math.round(s/60)+'分钟';return (s/3600).toFixed(1).replace(/\.0$/,'')+'小时';}
export function pct(x){return (x*100).toFixed(1).replace(/\.0$/,'')+'%';}
export function summaryStrip(r){
  const s=r.summary;
  return `<section class="strip"><span>事件版本 v${r.base_version}</span><span>配对 ${s.pairs} 次</span><span>归因 ${s.persons_with_pairs} 人</span><span>总等待 ${wait(s.total_wait_seconds)}</span><span>平均等待 ${wait(s.avg_wait_seconds)}</span><span>未配对触达 ${s.unmatched_touches} / 点击 ${s.unmatched_clicks}</span></section>`;
}
export function channelTable(stats){
  return table(['渠道','首点人数','首点率','归因点击','归因人数','平均等待'],
    stats.map(c=>[c.channel,c.first_clicks,{html:`<b>${pct(c.first_click_rate)}</b>`},c.attributed_clicks,c.attributed_persons,wait(c.avg_wait_seconds)]));
}
export function pairsTable(pairs){
  return table(['同一人','点击编号','触达编号','渠道','触达时间','点击时间','等待'],
    pairs.map(p=>[p.person,'C'+p.click_no,'T'+p.touch_no,p.channel,esc(p.touch_at.replace('T',' ').slice(0,16)),esc(p.click_at.replace('T',' ').slice(0,16)),wait(p.wait_seconds)]));
}
export function changesBlock(ch){
  if(!ch)return '';
  const rows=[
    ...ch.reassigned.map(x=>['改派',`${x.person} 点击C${x.click_no}`,`触达T${x.old_touch_no}(${x.old_channel}) → T${x.new_touch_no}(${x.new_channel})`]),
    ...ch.added.map(x=>['新增配对',`${x.person} 点击C${x.click_no}`,`触达T${x.touch_no}(${x.channel}) · 等待${wait(x.wait_seconds)}`]),
    ...ch.removed.map(x=>['移除配对',`${x.person} 点击C${x.click_no}`,`原触达T${x.touch_no}(${x.channel})`]),
  ];
  if(!rows.length)return '<p class="method-note">与上一发布版相比,配对没有变化。</p>';
  return table(['变化','对象','说明'],rows);
}
export function resultView(run){
  const r=run.result;
  return `${summaryStrip(r)}<h2>分渠道首点率 <small>与配对明细同源同版,一次性切换</small></h2>${channelTable(r.channel_stats)}<h2>配对明细 <small>${r.pairs.length} 对 · 一触达一点击</small></h2>${pairsTable(r.pairs)}<h2>相对上一发布版的改派</h2>${changesBlock(r.changes)}`;
}
