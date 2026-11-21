import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
class Base(DeclarativeBase):
    pass
_url=os.environ['DATABASE_URL']
_kwargs={'pool_pre_ping':True}
if _url.startswith('sqlite'):  # 本地测试/开发;生产为 PostgreSQL
    from sqlalchemy.pool import NullPool
    _kwargs.update(connect_args={'check_same_thread':False},poolclass=NullPool)
engine = create_engine(_url, **_kwargs)
Session = sessionmaker(bind=engine, expire_on_commit=False)
def get_db():
    with Session() as db:
        yield db
