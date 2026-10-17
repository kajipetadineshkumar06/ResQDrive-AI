# ==========================================
# routers/jobs.py
# ==========================================

from fastapi import APIRouter, HTTPException

from jobs.request_jobs import (
    cancel_expired_request,
    release_provider
)


router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"]
)


# ==========================================
# CHECK / PROCESS REQUEST TIMEOUT
# ==========================================

@router.post(
    "/request-timeout/{request_id}"
)
def request_timeout(
    request_id: int
):
    """
    Check a service request and process its
    timeout/reassignment workflow.

    Pending request:
        pending
            ↓
        provider timeout
            ↓
        find another provider
            ↓
        pending

    The request is NOT marked as cancelled
    or timeout.
    """

    try:

        result = cancel_expired_request(
            request_id
        )

        return result

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to process request timeout: "
                f"{str(error)}"
            )
        )


# ==========================================
# RELEASE PROVIDER
# ==========================================

@router.post(
    "/release-provider/{provider_id}"
)
def provider_release(
    provider_id: int
):
    """
    Make a provider available again.
    """

    try:

        result = release_provider(
            provider_id
        )

        return result

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to release provider: "
                f"{str(error)}"
            )
        )