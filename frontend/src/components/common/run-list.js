import {table} from './table.js';
import {status} from './status.js';
import {esc} from '../../utils/format.js';
const TRIGGER={auto:'补报/撤回',manual:'手动重算'};
export function runList(rows,withProject=false){
  const head=[...(withProject?['项目']:[]),'运行','状态','基于版本','触发','排队时间','校验'];
  return table(head,rows.map(r=>[...(withProject?[r.project_name]:[]),
    {html:`<a href="#review/${r.id}">#${r.id}</a>`},{html:status(r.status)},'v'+r.base_version,
    TRIGGER[r.triggered_by]||r.triggered_by,esc((r.created_at||'').replace('T',' ').slice(0,19)),
    r.checksum?r.checksum.slice(0,12):'—']));
}
