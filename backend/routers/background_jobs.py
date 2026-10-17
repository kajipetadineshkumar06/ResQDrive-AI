from fastapi import APIRouter, HTTPException

from core.queue import task_queue

from jobs.request_jobs import (
    cancel_expired_request,
    release_provider
)


router = APIRouter(
    prefix="/jobs",
    tags=["Background Jobs"]
)


# =====================================================
# TEST REQUEST TIMEOUT JOB
# =====================================================

@router.post("/test-timeout/{request_id}")
def test_timeout(
    request_id: int
):

    try:

        job = task_queue.enqueue(
            cancel_expired_request,
            request_id
        )

        return {

            "success": True,

            "message": "Request timeout job added",

            "job_id": job.id,

            "request_id": request_id

        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Failed to enqueue job: {str(e)}"
        )


# =====================================================
# TEST PROVIDER RELEASE JOB
# =====================================================

@router.post("/release-provider/{provider_id}")
def test_release(
    provider_id: int
):

    try:

        job = task_queue.enqueue(
            release_provider,
            provider_id
        )

        return {

            "success": True,

            "message": "Provider release job added",

            "job_id": job.id,

            "provider_id": provider_id

        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Failed to enqueue job: {str(e)}"
        )