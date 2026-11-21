from sqlalchemy import Column,Integer,String,JSON,Text,ForeignKey
from src.config.database import Base
class AttributionRun(Base):
    __tablename__='runs'
    id=Column(Integer,primary_key=True)
    project_id=Column(Integer,ForeignKey('projects.id'),nullable=False)
    base_version=Column(Integer,nullable=False)   # 计算所基于的事件版本
    status=Column(String(12),default='queued')    # 见 constants.enums.RUN_STATES
    triggered_by=Column(String(10),default='manual')  # manual 手动重算 | auto 补报/撤回触发
    checksum=Column(String(64),default='')        # 该版本事件快照 SHA256,可复算核对
    result=Column(JSON,nullable=True)             # 配对明细+分渠道首点率,同源同版
    error=Column(Text,default='')
    created_at=Column(String(40),nullable=False)
    finished_at=Column(String(40),default='')
Run=AttributionRun
