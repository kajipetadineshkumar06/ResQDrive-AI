import os

import redis


def create_redis_client():
    """Use a deployment-provided URL, retaining the local Redis default."""
    redis_url = os.getenv("REDIS_URL", "").strip()
    if redis_url:
        return redis.Redis.from_url(redis_url, decode_responses=False)

    return redis.Redis(
        host="localhost",
        port=6379,
        db=0,
        decode_responses=False,
    )


redis_client = create_redis_client()


def test_redis():

    try:

        response = redis_client.ping()

        return response

    except redis.RedisError as e:

        print(
            "Redis connection error:",
            e
        )

        return False
