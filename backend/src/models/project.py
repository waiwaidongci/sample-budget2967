from sqlalchemy import Column,Integer,String,JSON,Text
from src.config.database import Base
class AttributionProject(Base):
    __tablename__='projects'
    id=Column(Integer,primary_key=True)
    name=Column(String(120),unique=True,nullable=False)
    channels=Column(JSON,nullable=False)          # 约定的渠道名单,触达必须取自其中
    window_seconds=Column(Integer,nullable=False) # 约定归因时窗
    description=Column(Text,default='')
    event_version=Column(Integer,nullable=False,default=0)  # 每次补报/撤回 +1
    current_run_id=Column(Integer,nullable=True)  # 当前发布指针:明细与首点率随它一次性切换
    created_at=Column(String(40),nullable=False)
Project=AttributionProject
