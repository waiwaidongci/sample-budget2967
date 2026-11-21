import json
from sqlalchemy import select,func
from src.config.database import Base,engine,Session
from src.models.user import User
from src.models.project import Project
from src.models.event import Event
from src.models.run import Run
from src.models import audit
from src.schemas.project import ProjectInput
from src.schemas.event import EventInput,WithdrawInput
from src.services import attribution,runs
from src.utils.security import hash_password

PROJECT='榆灯·冬季全渠道归因'
CHANNELS=['短信','推送','邮件','广告']
D='2026-11-'
def E(kind,no,person,at,channel=''):
    return EventInput(kind=kind,event_no=no,person=person,channel=channel,occurred_at=at)
def T(day,hm): return f'{D}{day:02d}T{hm}:00Z'

def seed_users():
    """确保三个演示账号存在;重复调用不覆盖。"""
    with Session() as db:
        for role in ('admin','analyst','viewer'):
            email=role+'@demo.local'
            if not db.scalar(select(User).where(User.email==email)):
                db.add(User(email=email,role=role,password_hash=hash_password('Research2026!')))
        db.commit()

def drain(db):
    """同步清空队列(seed 内演示版本演进;运行中由 worker 实时消费)。"""
    for run in db.scalars(select(Run).where(Run.status.in_(['queued','running'])).order_by(Run.id)):
        runs.process(db,run.id)

def seed():
    Base.metadata.create_all(engine)
    seed_users()
    with Session() as db:
        if db.scalar(select(Project).where(Project.name==PROJECT)):
            return _counts(db)  # 自然键幂等:已初始化则不覆盖
        admin=db.scalar(select(User).where(User.email=='admin@demo.local'))
        p=attribution.create_project(db,ProjectInput(
            name=PROJECT,window_hours=72,channels=CHANNELS,
            description='多渠道触达与点击的一对一归因演示:约定时窗72小时;迟到补报与撤回触发改派,版本化发布。'),admin)
        pid=p['id']
        # v1 基础事件:同一人多渠道触达、一点击多候选、窗口外点击、无触达点击
        attribution.add_events(db,pid,[
            E('touch',1,'U101',T(10,'09:00'),'短信'),E('touch',2,'U101',T(10,'10:00'),'推送'),
            E('touch',3,'U102',T(10,'08:00'),'邮件'),
            E('touch',4,'U103',T(10,'07:00'),'广告'),E('touch',5,'U103',T(10,'07:30'),'短信'),
            E('touch',6,'U104',T(10,'06:00'),'推送'),
            E('touch',7,'U106',T(10,'09:30'),'短信'),E('touch',8,'U106',T(10,'10:30'),'邮件'),
            E('click',1,'U101',T(10,'12:00')),
            E('click',2,'U102',T(10,'09:00')),E('click',3,'U102',T(11,'09:00')),
            E('click',4,'U103',T(10,'08:00')),E('click',5,'U103',T(10,'08:20')),
            E('click',6,'U104',T(14,'10:00')),
            E('click',7,'U105',T(10,'11:00')),
            E('click',8,'U106',T(10,'12:30')),
            E('click',9,'U107',T(10,'08:00')),
        ],admin);drain(db)
        # v2 迟到补报:U101 更近的广告触达改派原配对;U107 迟到的短信触达补上配对
        attribution.add_events(db,pid,[
            E('touch',9,'U101',T(10,'11:30'),'广告'),
            E('touch',10,'U107',T(9,'20:00'),'短信'),
        ],admin);drain(db)
        # v3 撤回:U106 的邮件触达系重复上报,撤回后点击改派短信
        attribution.withdraw(db,pid,WithdrawInput(kind='touch',event_no=8),admin);drain(db)
        # v4 并发剧情:先在 v3 上排一个手动重算,补报随即到达使其过期(stale),新计算发布 v4
        runs.create_manual(db,pid,admin)
        attribution.add_events(db,pid,[
            E('touch',11,'U108',T(11,'09:00'),'推送'),E('click',10,'U108',T(11,'10:00')),
            E('touch',12,'U102',T(11,'08:30'),'广告'),
        ],admin);drain(db)
        return _counts(db)

def _counts(db):
    out={m.__tablename__:db.scalar(select(func.count()).select_from(m)) for m in (User,Project,Event,Run)}
    print(json.dumps(out,ensure_ascii=False));return out
if __name__=='__main__': seed()
