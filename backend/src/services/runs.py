from sqlalchemy import select
from fastapi import HTTPException
from src.models.project import Project
from src.models.run import Run
from src.services import attribution,queue
from src.services.matching import attribute,channel_stats,summarize,diff_pairs
from src.services.audits import log
from src.utils.serializers import record,now,checksum

def list_runs(db,project_id=None):
    q=select(Run).order_by(Run.id.desc())
    if project_id: q=q.where(Run.project_id==project_id)
    return [_view(db,r) for r in db.scalars(q.limit(200))]

def _view(db,run):
    r=record(run)
    r['project_name']=db.get(Project,run.project_id).name
    r['has_result']=run.result is not None
    r.pop('result',None)
    return r

def get(db,id):
    run=db.get(Run,id)
    if not run: raise HTTPException(404,'计算运行不存在')
    r=record(run)
    project=db.get(Project,run.project_id)
    r['project_name']=project.name
    r['is_current']=project.current_run_id==run.id
    return r

def current(db,project_id):
    project=attribution.require(db,project_id)
    if not project.current_run_id: return {'project':record(project),'run':None}
    run=get(db,project.current_run_id)
    return {'project':record(project),'run':run}

def create_manual(db,project_id,user):
    """手动重算:基于当前事件版本排队;同版本在途任务去重。"""
    project=attribution.require(db,project_id)
    version=project.event_version
    if version==0: raise HTTPException(422,'尚无事件,先录入触达与点击')
    dup=db.scalar(select(Run).where(Run.project_id==project_id,Run.base_version==version,
                                    Run.status.in_(('queued','running'))))
    if dup: return {'run_id':dup.id,'version':version,'deduplicated':True}
    run=attribution._enqueue(db,project_id,version,'manual')
    log(db,user,'run.enqueue',f'运行{run.id} 基于v{version} (manual)');db.commit()
    queue.enqueue(run.id)
    return {'run_id':run.id,'version':version,'deduplicated':False}

def process(db,id):
    """worker 入口:按 base_version 重建事件快照并计算,随后受版本守卫地发布。
    旧计算不得发布为当前结果;明细与首点率在同一事务内随当前指针一次性切换。"""
    run=db.get(Run,id)
    if not run or run.status in ('published','superseded','stale','failed'): return
    run.status='running';db.commit()
    project=db.get(Project,run.project_id)
    try:
        events=attribution.active_events(db,run.project_id,run.base_version)
        pairs=attribute(events,project.window_seconds)
        previous=db.get(Run,project.current_run_id) if project.current_run_id else None
        old_pairs=previous.result['pairs'] if previous and previous.result else []
        result={'base_version':run.base_version,'computed_at':now(),
                'summary':summarize(events,pairs,project.window_seconds),
                'channel_stats':channel_stats(pairs),'pairs':pairs,
                'changes':diff_pairs(old_pairs,pairs)}
        run.checksum=checksum(events);run.result=result;run.error=''
    except Exception as e:
        run.status='failed';run.error=str(e);run.finished_at=now()
        log(db,'worker','run.failed',f'运行{id}: {e}');db.commit();return
    # 发布守卫:锁定项目行,版本未前进才允许成为当前结果,同一事务完成切换
    # (PostgreSQL 行锁与事件递进的行更新互斥;SQLite 仅用于本地测试,单worker语义不变)
    q=select(Project.event_version).where(Project.id==run.project_id)
    if db.bind.dialect.name!='sqlite': q=q.with_for_update()
    version=db.scalar(q)
    run.finished_at=now()
    if version!=run.base_version:
        run.status='stale'
        log(db,'worker','run.stale',f'运行{id} 基于v{run.base_version},当前已v{version},不发布')
    else:
        if project.current_run_id:
            old=db.get(Run,project.current_run_id)
            if old and old.status=='published': old.status='superseded'
        run.status='published'
        project.current_run_id=run.id
        log(db,'worker','run.publish',f'运行{id} 发布v{run.base_version},配对{len(run.result["pairs"])}')
    db.commit()
