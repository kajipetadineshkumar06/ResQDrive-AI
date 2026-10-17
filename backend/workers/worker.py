from rq import Queue
from rq.worker import SimpleWorker

from core.redis_client import redis_client


listen = [
    "resqdrive"
]


if __name__ == "__main__":

    print("====================================")
    print("ResQDrive AI RQ Worker")
    print("Windows Worker")
    print("Listening on queue: resqdrive")
    print("====================================")

    worker = SimpleWorker(
        listen,
        connection=redis_client
    )

    worker.work()