import os,time,logging
from pathlib import Path
from redis import Redis
from sqlalchemy import select
from src.config.database import Session
from src.models.run import Run
from src.models import user,project,event,audit
from src.services import runs
from src.constants.enums import QUEUE
redis=Redis.from_url(os.environ['REDIS_URL'])
Path('/app/artifacts').mkdir(exist_ok=True)
# 崩溃恢复:在途任务重新排队;本项目恰好一个worker
with Session() as db:
    for run in db.scalars(select(Run).where(Run.status.in_(['queued','running']))):
        redis.rpush(QUEUE,run.id)
while True:
    Path('/tmp/worker-heartbeat').touch()
    job=redis.blpop(QUEUE,timeout=2)
    if not job: continue
    try:
        with Session() as db: runs.process(db,int(job[1]))
    except Exception: logging.exception('run processing failed')
