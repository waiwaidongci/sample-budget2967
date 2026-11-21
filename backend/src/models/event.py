from sqlalchemy import Column,Integer,String,ForeignKey,UniqueConstraint
from src.config.database import Base
class TouchClickEvent(Base):
    __tablename__='events'
    # 编号在同一项目同一类事件内唯一,撤回后也不释放,保证历史版本可复算
    __table_args__=(UniqueConstraint('project_id','kind','event_no'),)
    id=Column(Integer,primary_key=True)
    project_id=Column(Integer,ForeignKey('projects.id'),nullable=False)
    kind=Column(String(10),nullable=False)        # touch 触达 | click 点击
    event_no=Column(Integer,nullable=False)       # 事件编号,同分时定序依据
    person=Column(String(60),nullable=False)      # 同一人标识
    channel=Column(String(40),default='')         # 仅触达有渠道
    occurred_at=Column(String(40),nullable=False) # 事件发生时间(UTC ISO)
    occurred_ts=Column(Integer,nullable=False)    # 发生时间 epoch 秒,配对与等待用
    status=Column(String(12),nullable=False,default='active')  # active | withdrawn
    received_at=Column(String(40),nullable=False) # 录入时间,迟到记录据此可辨
    version_added=Column(Integer,nullable=False)      # 录入时的事件版本
    version_withdrawn=Column(Integer,nullable=True)   # 撤回时的事件版本
Event=TouchClickEvent
