from datetime import datetime,timezone
from fastapi import HTTPException
from sqlalchemy import select,func,update
from src.models.project import Project
from src.models.event import Event
from src.models.run import Run
from src.services import queue
from src.services.audits import log
from src.utils.serializers import record,now

MAX_EVENTS=2000   # 小型本地应用边界:单项目事件上限
MAX_BATCH=500
MIN_TS=946684800      # 2000-01-01
MAX_TS=4102444800     # 2100-01-01

def list_projects(db):
    out=[]
    for p in db.scalars(select(Project).order_by(Project.id)):
        x=record(p)
        x['active_touches']=db.scalar(select(func.count()).select_from(Event).where(Event.project_id==p.id,Event.kind=='touch',Event.status=='active'))
        x['active_clicks']=db.scalar(select(func.count()).select_from(Event).where(Event.project_id==p.id,Event.kind=='click',Event.status=='active'))
        x['withdrawn']=db.scalar(select(func.count()).select_from(Event).where(Event.project_id==p.id,Event.status=='withdrawn'))
        cur=db.get(Run,p.current_run_id) if p.current_run_id else None
        x['current']=digest(cur) if cur else None
        out.append(x)
    return out

def digest(run):
    if not run: return None
    r=record(run)
    if run.result: r['summary']=run.result.get('summary')
    r.pop('result',None)
    return r

def create_project(db,data,user):
    if db.scalar(select(Project).where(Project.name==data.name)): raise HTTPException(409,'项目名称已存在')
    channels=[];
    for c in data.channels:
        c=c.strip()
        if not c or len(c)>40: raise HTTPException(422,'渠道名须为1到40个字符')
        if c in channels: raise HTTPException(409,f'渠道重复: {c}')
        channels.append(c)
    if not 1<=len(channels)<=12: raise HTTPException(422,'渠道名单须为1到12个')
    seconds=int(round(data.window_hours*3600))
    if not 1800<=seconds<=720*3600: raise HTTPException(422,'约定时窗须在0.5到720小时之间')
    p=Project(name=data.name,channels=channels,window_seconds=seconds,description=data.description,
              event_version=0,created_at=now())
    db.add(p);log(db,user,'project.create',data.name);db.commit();db.refresh(p)
    return record(p)

def require(db,id):
    p=db.get(Project,id)
    if not p: raise HTTPException(404,'归因项目不存在')
    return p

def list_events(db,project_id):
    require(db,project_id)
    return [record(x) for x in db.scalars(select(Event).where(Event.project_id==project_id)
                                          .order_by(Event.kind,Event.event_no))]

def _parse_time(value):
    try:
        dt=datetime.fromisoformat(value.replace('Z','+00:00')) if isinstance(value,str) else None
    except ValueError:
        dt=None
    if dt is None: raise HTTPException(422,f'时间格式非法: {value!r},需ISO 8601并带时区')
    if dt.tzinfo is None: raise HTTPException(422,'时间必须带时区(如 2026-11-10T09:00:00Z)')
    dt=dt.astimezone(timezone.utc);ts=int(dt.timestamp())
    if not MIN_TS<=ts<=MAX_TS: raise HTTPException(422,'时间须在2000到2100年之间')
    return dt.isoformat(),ts

def _validate_items(project,items):
    """整批校验,任一非法则整批拒绝。返回规范化后的 dict 列表。"""
    if not 1<=len(items)<=MAX_BATCH: raise HTTPException(422,f'每批须为1到{MAX_BATCH}条')
    clean=[];seen=set()
    for raw in items:
        kind=raw.kind
        if kind not in ('touch','click'): raise HTTPException(422,'事件类型须为 touch 或 click')
        person=raw.person.strip()
        if not person: raise HTTPException(422,'同一人标识不能为空')
        channel=(raw.channel or '').strip()
        if kind=='touch':
            if not channel: raise HTTPException(422,f'触达 {raw.event_no} 缺少渠道')
            if channel not in project.channels: raise HTTPException(422,f'渠道 "{channel}" 不在项目约定名单内')
        elif channel: raise HTTPException(422,'点击事件不带渠道')
        occurred_at,ts=_parse_time(raw.occurred_at)
        key=(kind,raw.event_no)
        if key in seen: raise HTTPException(409,f'批内编号重复: {kind} {raw.event_no}')
        seen.add(key)
        clean.append({'kind':kind,'event_no':raw.event_no,'person':person,'channel':channel,
                      'occurred_at':occurred_at,'occurred_ts':ts})
    return clean

def add_events(db,project_id,items,user):
    """补报/录入:整批校验、单次版本递进、同事务自动排队重算。"""
    project=require(db,project_id)
    clean=_validate_items(project,items)
    total=db.scalar(select(func.count()).select_from(Event).where(Event.project_id==project_id))
    if total+len(clean)>MAX_EVENTS: raise HTTPException(422,f'单项目事件上限{MAX_EVENTS}条')
    for c in clean:
        dup=db.scalar(select(Event.id).where(Event.project_id==project_id,Event.kind==c['kind'],Event.event_no==c['event_no']))
        if dup: raise HTTPException(409,f'编号已存在(含已撤回): {c["kind"]} {c["event_no"]}')
    version=_bump(db,project_id)
    received=now()
    for c in clean:
        db.add(Event(project_id=project_id,version_added=version,received_at=received,**c))
    log(db,user,'event.add' if len(clean)==1 else 'event.batch',f'项目{project_id} v{version} +{len(clean)}条')
    run=_enqueue(db,project_id,version,'auto')
    log(db,user,'run.enqueue',f'运行{run.id} 基于v{version} (auto)')
    db.commit()
    queue.enqueue(run.id)   # 提交后再入队,避免worker先于提交看到空记录
    return {'version':version,'added':len(clean),'run_id':run.id}

def withdraw(db,project_id,data,user):
    """撤回:原配对随下一次计算改派,历史版本仍可复算。"""
    require(db,project_id)
    ev=db.scalar(select(Event).where(Event.project_id==project_id,Event.kind==data.kind,Event.event_no==data.event_no))
    if not ev: raise HTTPException(404,'事件不存在')
    if ev.status=='withdrawn': raise HTTPException(409,'事件已撤回,不可重复操作')
    version=_bump(db,project_id)
    ev.status='withdrawn';ev.version_withdrawn=version
    log(db,user,'event.withdraw',f'项目{project_id} v{version} 撤回 {data.kind} {data.event_no}')
    run=_enqueue(db,project_id,version,'auto')
    log(db,user,'run.enqueue',f'运行{run.id} 基于v{version} (auto)')
    db.commit()
    queue.enqueue(run.id)
    return {'version':version,'withdrawn':f'{data.kind} {data.event_no}','run_id':run.id}

def _bump(db,project_id):
    """事件版本原子递进;行锁与发布检查互斥,保证并发语义。"""
    db.execute(update(Project).where(Project.id==project_id).values(event_version=Project.event_version+1))
    return db.scalar(select(Project.event_version).where(Project.id==project_id))

def _enqueue(db,project_id,version,triggered_by):
    """创建计算任务行;Redis 入队由调用方在提交后执行。"""
    run=Run(project_id=project_id,base_version=version,triggered_by=triggered_by,created_at=now())
    db.add(run);db.flush()
    return run

def active_events(db,project_id,version):
    """重建指定版本的在版事件:录入版本<=v 且(未撤回或撤回版本>v)。"""
    rows=db.scalars(select(Event).where(Event.project_id==project_id,Event.version_added<=version)
                    .order_by(Event.kind,Event.event_no))
    return [{'kind':e.kind,'event_no':e.event_no,'person':e.person,'channel':e.channel,
             'occurred_at':e.occurred_at,'occurred_ts':e.occurred_ts}
            for e in rows if e.version_withdrawn is None or e.version_withdrawn>version]
