"""服务层测试:版本递进、发布守卫(旧计算不得发布)、一次性切换、撤回改派、校验拒绝。"""
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from src.models.project import Project
from src.models.run import Run
from src.schemas.project import ProjectInput
from src.schemas.event import EventInput,WithdrawInput
from src.services import attribution,runs
from tests.helpers import make_user,E

def new_project(db,user,name='测试项目',hours=72):
    return attribution.create_project(db,ProjectInput(name=name,window_hours=hours,channels=['短信','邮件'],description=''),user)

def test_version_guard_blocks_stale_publish(db):
    user=make_user(db)
    p=new_project(db,user);pid=p['id']
    attribution.add_events(db,pid,[E('touch',1,'P1','2026-11-10T09:00:00Z','短信'),E('click',1,'P1','2026-11-10T10:00:00Z')],user)
    run1=db.scalar(select(Run).where(Run.base_version==1))
    runs.process(db,run1.id)
    project=db.get(Project,pid)
    assert project.current_run_id==run1.id and db.get(Run,run1.id).status=='published'
    # 事件前进到 v2 后,基于 v1 的旧计算不得发布为当前结果
    attribution.add_events(db,pid,[E('touch',2,'P2','2026-11-10T09:00:00Z','邮件'),E('click',2,'P2','2026-11-10T09:30:00Z')],user)
    stale_run=Run(project_id=pid,base_version=1,triggered_by='manual',created_at='2026-11-10T12:00:00Z')
    db.add(stale_run);db.commit()
    runs.process(db,stale_run.id)
    db.refresh(project)
    assert db.get(Run,stale_run.id).status=='stale'
    assert project.current_run_id==run1.id  # 当前结果未被旧计算覆盖
    # 基于 v2 的计算发布,一次性切换:旧版转 superseded,指针指向新版
    run2=db.scalar(select(Run).where(Run.base_version==2))
    runs.process(db,run2.id)
    db.refresh(project)
    assert db.get(Run,run2.id).status=='published'
    assert db.get(Run,run1.id).status=='superseded'
    assert project.current_run_id==run2.id
    result=db.get(Run,run2.id).result
    assert result['base_version']==2 and len(result['pairs'])==2
    assert result['channel_stats'] and result['summary']['pairs']==2  # 明细与首点率同版同窗

def test_withdraw_reassigns_and_history_reconstructable(db):
    user=make_user(db)
    p=new_project(db,user);pid=p['id']
    attribution.add_events(db,pid,[E('touch',1,'P1','2026-11-10T08:00:00Z','短信'),
                                   E('touch',2,'P1','2026-11-10T09:00:00Z','邮件'),
                                   E('click',1,'P1','2026-11-10T10:00:00Z')],user)
    runs.process(db,db.scalar(select(Run).where(Run.base_version==1)).id)
    pair=db.get(Project,pid).current_run_id
    r=db.get(Run,pair).result['pairs'][0]
    assert r['touch_no']==2 and r['wait_seconds']==3600  # 邮件等待更短
    attribution.withdraw(db,pid,WithdrawInput(kind='touch',event_no=2),user)
    runs.process(db,db.scalar(select(Run).where(Run.base_version==2)).id)
    cur=db.get(Run,db.get(Project,pid).current_run_id)
    assert cur.result['pairs'][0]['touch_no']==1 and cur.result['pairs'][0]['wait_seconds']==7200
    ch=cur.result['changes']['reassigned'][0]
    assert (ch['old_touch_no'],ch['new_touch_no'])==(2,1)  # 撤回引起改派
    # 历史版本可复算:v1 快照里邮件触达仍在版
    v1=attribution.active_events(db,pid,1)
    assert sum(1 for e in v1 if e['kind']=='touch')==2
    v2=attribution.active_events(db,pid,2)
    assert sum(1 for e in v2 if e['kind']=='touch')==1

def test_validation_and_batch_atomicity(db):
    user=make_user(db)
    p=new_project(db,user);pid=p['id']
    with pytest.raises(HTTPException) as e:
        attribution.add_events(db,pid,[E('touch',1,'P1','2026-11-10T09:00:00Z','飞书')],user)
    assert e.value.status_code==422 and '渠道' in e.value.detail
    with pytest.raises(HTTPException) as e:
        attribution.add_events(db,pid,[E('click',1,'P1','2026-11-10T09:00:00Z','短信')],user)
    assert e.value.status_code==422
    with pytest.raises(HTTPException) as e:
        attribution.add_events(db,pid,[E('touch',1,'P1','2026-11-10T09:00:00','短信')],user)
    assert e.value.status_code==422 and '时区' in e.value.detail
    # 整批原子:第二条非法 -> 一条都不落,版本不动
    with pytest.raises(HTTPException):
        attribution.add_events(db,pid,[E('touch',1,'P1','2026-11-10T09:00:00Z','短信'),
                                       E('touch',1,'P2','2026-11-10T09:00:00Z','短信')],user)
    assert db.get(Project,pid).event_version==0
    assert attribution.list_events(db,pid)==[]
    attribution.add_events(db,pid,[E('touch',1,'P1','2026-11-10T09:00:00Z','短信')],user)
    with pytest.raises(HTTPException) as e:
        attribution.add_events(db,pid,[E('touch',1,'P9','2026-11-10T09:00:00Z','短信')],user)
    assert e.value.status_code==409 and '编号' in e.value.detail
    # 撤回不存在/重复撤回
    with pytest.raises(HTTPException) as e:
        attribution.withdraw(db,pid,WithdrawInput(kind='touch',event_no=99),user)
    assert e.value.status_code==404
    attribution.withdraw(db,pid,WithdrawInput(kind='touch',event_no=1),user)
    with pytest.raises(HTTPException) as e:
        attribution.withdraw(db,pid,WithdrawInput(kind='touch',event_no=1),user)
    assert e.value.status_code==409

def test_manual_recalc_deduplicates(db):
    user=make_user(db)
    p=new_project(db,user);pid=p['id']
    attribution.add_events(db,pid,[E('touch',1,'P1','2026-11-10T09:00:00Z','短信'),E('click',1,'P1','2026-11-10T09:05:00Z')],user)
    runs.process(db,db.scalar(select(Run).where(Run.base_version==1)).id)  # 清空自动排队的在途计算
    first=runs.create_manual(db,pid,user)
    second=runs.create_manual(db,pid,user)
    assert first['deduplicated'] is False and second['deduplicated'] is True
    assert first['run_id']==second['run_id']

def test_same_version_recompute_is_reproducible(db):
    user=make_user(db)
    p=new_project(db,user);pid=p['id']
    attribution.add_events(db,pid,[E('touch',1,'P1','2026-11-10T09:00:00Z','短信'),E('click',1,'P1','2026-11-10T09:05:00Z')],user)
    run=db.scalar(select(Run).where(Run.base_version==1))
    runs.process(db,run.id)
    snapshot=(run.checksum,run.result['pairs'],run.result['channel_stats'])
    # 用同一版本事件重算,校验和与结果一致(可复现)
    events=attribution.active_events(db,pid,1)
    from src.services.matching import attribute,channel_stats
    from src.utils.serializers import checksum
    assert checksum(events)==snapshot[0]
    assert attribute(events,72*3600)==snapshot[1]
    assert channel_stats(snapshot[1])==snapshot[2]
