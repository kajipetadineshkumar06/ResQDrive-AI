from fastapi import APIRouter

from core.redis_client import test_redis


router = APIRouter(
    prefix="/redis",
    tags=["Redis"]
)



@router.get("/test")
def redis_test():

    status = test_redis()


    return {

        "redis_running": status

    }