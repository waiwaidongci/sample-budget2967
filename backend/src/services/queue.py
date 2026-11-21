import os
from redis import Redis
from src.constants.enums import QUEUE
_client=None
def client():
    global _client
    if _client is None: _client=Redis.from_url(os.environ['REDIS_URL'])
    return _client
def enqueue(run_id):
    client().rpush(QUEUE,run_id)
