import redis


redis_client = redis.Redis(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=False
)


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