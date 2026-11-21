import os,sys,tempfile
from pathlib import Path
os.environ['DATABASE_URL']='sqlite:///'+tempfile.mktemp(suffix='.db',prefix='attr-test-')
os.environ['REDIS_URL']='redis://localhost:6379/0'
os.environ['JWT_SECRET']='test-secret'
os.environ['SEED_DEMO']='false'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import fakeredis
import pytest
from src.config.database import Base,engine,Session
import src.services.queue as queue
import src.middlewares.rate_limit as rate_limit
queue._client=fakeredis.FakeStrictRedis()      # 入队走内存替身,断言可查
rate_limit.redis=fakeredis.FakeStrictRedis()   # 限流同理

@pytest.fixture()
def db():
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
    with Session() as s: yield s

@pytest.fixture()
def client(db):
    import src.main as main
    main.Redis=fakeredis.FakeRedis
    from fastapi.testclient import TestClient
    with TestClient(main.app) as c: yield c

@pytest.fixture()
def admin_headers(client):
    r=client.post('/auth/login',json={'email':'admin@demo.local','password':'Research2026!'})
    assert r.status_code==200,r.text
    return {'Authorization':'Bearer '+r.json()['token']}

@pytest.fixture()
def seeded(client):
    """建表+种子用户(不落业务数据)。"""
    from scripts.seed_demo import seed_users
    seed_users()
    return client
