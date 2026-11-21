"""端到端:种子剧情产生 v1→v4 版本史,含迟到改派、撤回改派与过期未发布。"""
from sqlalchemy import select
from src.models.project import Project
from src.models.run import Run
from src.models.event import Event
from scripts.seed_demo import seed,PROJECT

def test_seed_story(db):
    seed()
    p=db.scalar(select(Project).where(Project.name==PROJECT))
    assert p.event_version==4
    runs=db.scalars(select(Run).order_by(Run.id)).all()
    assert [r.status for r in runs]==['superseded','superseded','superseded','stale','published']
    assert p.current_run_id==runs[-1].id
    cur=runs[-1].result
    assert cur['base_version']==4 and cur['summary']['pairs']==8
    stats={c['channel']:c for c in cur['channel_stats']}
    assert stats['短信']['first_clicks']==3 and stats['短信']['first_click_rate']==0.5
    assert stats['广告']['first_clicks']==1
    # v2:迟到补报改派 U101(推送→广告),新增 U107 配对
    v2=runs[1].result['changes']
    assert v2['reassigned']==[{'person':'U101','click_no':1,'old_touch_no':2,'new_touch_no':9,'old_channel':'推送','new_channel':'广告'}]
    assert [a['person'] for a in v2['added']]==['U107']
    # v3:撤回邮件触达,U106 改派短信
    v3=runs[2].result['changes']
    assert v3['reassigned'][0]['new_channel']=='短信'
    # v4:并发补报后新增 U108 与 U102 的第二条配对;run4 过期未发布
    v4=cur['changes']
    assert {(a['person'],a['click_no']) for a in v4['added']}=={('U108',10),('U102',3)}
    assert runs[3].result is not None  # 过期计算留档可查
    # 幂等:再次 seed 不新增
    seed()
    assert len(db.scalars(select(Run)).all())==5
    assert len(db.scalars(select(Event)).all())==22
    assert db.get(Project,p.id).event_version==4

def test_seed_users_idempotent(db):
    from scripts.seed_demo import seed_users
    seed_users();seed_users()
    from src.models.user import User
    assert len(db.scalars(select(User)).all())==3
