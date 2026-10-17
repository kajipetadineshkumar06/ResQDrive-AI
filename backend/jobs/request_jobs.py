from datetime import timedelta

from database import SessionLocal
from models.service_request import ServiceRequest
from models.service_provider import ServiceProvider
from services.assignment_service import release_provider_if_idle
from services.timeout_service import (
    PROVIDER_TIMEOUT_SECONDS,
    db_now,
    has_provider_timed_out,
    normalize_datetime,
    process_request_timeout,
)


def cancel_expired_request(request_id: int):
    db = SessionLocal()

    try:
        request = (
            db.query(ServiceRequest)
            .filter(
                ServiceRequest.request_id == request_id
            )
            .with_for_update()
            .first()
        )

        if not request:
            return {
                "success": False,
                "request_id": request_id,
                "message": "Request not found"
            }

        print(
            f"Current request status: "
            f"{request.request_status}"
        )

        if request.request_status != "pending":
            return {
                "success": True,
                "request_id": request_id,
                "status": request.request_status,
                "message": "Request does not need timeout"
            }

        if not request.requested_at:
            return {
                "success": False,
                "request_id": request_id,
                "message": "Request timestamp is missing"
            }

        expected_provider_id = request.provider_id
        if expected_provider_id is None:
            return {
                "success": True,
                "request_id": request_id,
                "provider_id": None,
                "status": "pending",
                "message": "Request has no assigned provider",
            }

        if not has_provider_timed_out(request):
            assigned_at = normalize_datetime(request.requested_at)
            expiration_time = assigned_at + timedelta(
                seconds=PROVIDER_TIMEOUT_SECONDS
            )
            remaining_seconds = max(
                0,
                int((expiration_time - db_now()).total_seconds()),
            )
            return {
                "success": True,
                "request_id": request_id,
                "status": "still_pending",
                "remaining_seconds": remaining_seconds,
            }

    except Exception as e:
        db.rollback()
        raise

    finally:
        db.close()

    # The active processor locks the request again and verifies both its
    # pending state and the provider observed above before reassigning it.
    result = process_request_timeout(
        request_id=request_id,
        expected_provider_id=expected_provider_id,
    )

    if result is None:
        return {
            "success": False,
            "request_id": request_id,
            "message": "Timeout processing did not complete",
        }

    current_provider_id = result.provider_id
    current_status = result.request_status

    return {
        "success": True,
        "request_id": request_id,
        "provider_id": current_provider_id,
        "status": current_status,
        "checked_at": db_now().isoformat(),
        "message": "Timeout evaluated through the active timeout workflow",
    }


def release_provider(provider_id: int):

    print("========================================")
    print("ResQDrive AI - Provider Release Job")
    print("========================================")

    print(
        f"Releasing provider {provider_id}"
    )

    db = SessionLocal()

    try:

        provider = (
            db.query(ServiceProvider)
            .filter(ServiceProvider.provider_id == provider_id)
            .with_for_update()
            .first()
        )

        if not provider:

            print(
                f"Provider {provider_id} "
                f"not found."
            )

            return {
                "success": False,
                "provider_id": provider_id,
                "message": "Provider not found"
            }

        released = release_provider_if_idle(
            db,
            provider_id,
        )

        db.commit()

        result = {
            "success": released,
            "provider_id": provider_id,
            "status": (
                "provider_released"
                if released
                else "provider_still_assigned"
            ),
            "message": (
                "Provider released"
                if released
                else "Provider still has an active service request"
            ),
        }

        print(
            "Provider release completed:"
        )

        print(result)

        return result

    except Exception as e:

        db.rollback()

        print(
            "ERROR while releasing provider:"
        )

        print(
            f"Error type: {type(e).__name__}"
        )

        print(
            f"Error message: {str(e)}"
        )

        raise

    finally:

        db.close()
