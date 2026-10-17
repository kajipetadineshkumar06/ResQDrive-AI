from rq import Queue

from core.redis_client import redis_client


task_queue = Queue(
    name="resqdrive",
    connection=redis_client
)