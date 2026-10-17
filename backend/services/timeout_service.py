# ==========================================
# services/timeout_service.py
# ==========================================

import os
import time
import threading

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from database import SessionLocal
from models.service_request import ServiceRequest
from models.emergency import Emergency
from services.assignment_service import reject_request


# ==========================================
# CONFIGURATION
# ==========================================

def _provider_timeout_seconds() -> int:
    """Resolve the timeout while preserving the legacy minute setting."""
    timeout_seconds = os.getenv("PROVIDER_TIMEOUT_SECONDS")
    if timeout_seconds is not None:
        return int(timeout_seconds)

    timeout_minutes = os.getenv("REQUEST_TIMEOUT_MINUTES")
    if timeout_minutes is not None:
        return int(timeout_minutes) * 60

    # The legacy request job defaulted to five minutes.
    return 5 * 60


PROVIDER_TIMEOUT_SECONDS = _provider_timeout_seconds()

# Your MySQL database is storing naive timestamps
# that represent Indian Standard Time.
INDIA_TIMEZONE = ZoneInfo("Asia/Kolkata")


# ==========================================
# DATABASE CURRENT TIME
# ==========================================

def db_now():
    """
    Return current India/IST time as a naive datetime.

    IMPORTANT:
    MySQL service_requests.requested_at is currently
    storing naive timestamps such as:

        2026-08-26 16:45:29

    These timestamps represent IST.

    Therefore Python must also compare them using IST.
    """

    current_time = datetime.now(INDIA_TIMEZONE)

    # Remove timezone information because the database
    # stores naive DATETIME values.
    return current_time.replace(
        tzinfo=None
    )


# ==========================================
# NORMALIZE DATETIME
# ==========================================

def normalize_datetime(value):
    """
    Convert a datetime into a naive IST datetime.

    Handles both:

    1. Naive datetime
       Example:
           2026-08-26 16:45:29

    2. Timezone-aware datetime
       Example:
           2026-08-26 16:45:29+05:30

    If the datetime is timezone-aware, it is first
    converted to IST before removing timezone info.
    """

    if value is None:
        return None

    # --------------------------------------
    # Timezone-aware datetime
    # --------------------------------------

    if value.tzinfo is not None:

        value = value.astimezone(
            INDIA_TIMEZONE
        )

        return value.replace(
            tzinfo=None
        )

    # --------------------------------------
    # Already naive
    # --------------------------------------

    return value


# ==========================================
# CHECK PROVIDER TIMEOUT
# ==========================================

def has_provider_timed_out(request):
    """
    Check whether the currently assigned provider
    has exceeded the provider timeout.

    A request can timeout only when:

        request_status == "pending"
        provider_id is not None
        requested_at exists
    """

    # --------------------------------------
    # Request must still be pending
    # --------------------------------------

    if request.request_status != "pending":
        return False

    # --------------------------------------
    # Provider must exist
    # --------------------------------------

    if request.provider_id is None:
        return False

    # --------------------------------------
    # Requested time must exist
    # --------------------------------------

    if request.requested_at is None:
        return False

    # --------------------------------------
    # Normalize assigned/requested time
    # --------------------------------------

    assigned_time = normalize_datetime(
        request.requested_at
    )

    if assigned_time is None:
        return False

    # --------------------------------------
    # Current IST time
    # --------------------------------------

    current_time = db_now()

    # --------------------------------------
    # Calculate expiration
    # --------------------------------------

    expiration_time = (
        assigned_time
        + timedelta(
            seconds=PROVIDER_TIMEOUT_SECONDS
        )
    )

    # --------------------------------------
    # Debug information
    # --------------------------------------

    print(
        f"⏱️ Request {request.request_id}: "
        f"assigned={assigned_time}, "
        f"expires={expiration_time}, "
        f"now={current_time}"
    )

    # --------------------------------------
    # Timeout check
    # --------------------------------------

    return current_time >= expiration_time


# ==========================================
# PROVIDER TIMEOUT THREAD
# ==========================================

def provider_timeout(
    request_id: int,
    provider_id: int,
    timeout: int
):
    """
    Wait for the provider timeout and then
    verify that the request is still assigned
    to the same provider.

    The database remains the source of truth.
    """

    print(
        f"⏱️ Timeout started: "
        f"Request {request_id}, "
        f"Provider {provider_id}, "
        f"{timeout}s"
    )

    # --------------------------------------
    # Wait
    # --------------------------------------

    time.sleep(timeout)

    # --------------------------------------
    # Process timeout
    # --------------------------------------

    process_request_timeout(
        request_id=request_id,
        expected_provider_id=provider_id
    )


# ==========================================
# PROCESS ONE TIMEOUT
# ==========================================

def process_request_timeout(
    request_id: int,
    expected_provider_id: int | None = None
):
    """
    Process timeout for one service request.

    Timeout is processed only when:

    1. Request exists
    2. Provider matches expected provider
    3. Request is still pending
    4. Provider still exists
    5. Actual timeout has expired

    Then assignment_service.reject_request()
    excludes the old provider and attempts to
    assign another provider.
    """

    db: Session = SessionLocal()

    try:

        print(
            f"🔎 Checking timeout for "
            f"Request {request_id}"
        )

        # ==================================
        # LOCK REQUEST
        # ==================================

        request = (
            db.query(ServiceRequest)
            .filter(
                ServiceRequest.request_id
                == request_id
            )
            .with_for_update()
            .first()
        )

        # ==================================
        # REQUEST NOT FOUND
        # ==================================

        if request is None:

            print(
                f"⚠️ Timeout ignored: "
                f"Request {request_id} "
                f"not found."
            )

            return None

        print(
            f"📋 Request {request_id}: "
            f"provider={request.provider_id}, "
            f"status={request.request_status}"
        )

        # ==================================
        # STALE TIMEOUT CHECK
        # ==================================

        if (
            expected_provider_id is not None
            and request.provider_id
            != expected_provider_id
        ):

            print(
                f"↩️ Stale timeout ignored: "
                f"Request {request_id}; "
                f"expected Provider "
                f"{expected_provider_id}, "
                f"current Provider "
                f"{request.provider_id}"
            )

            return request

        # ==================================
        # REQUEST MUST BE PENDING
        # ==================================

        if request.request_status != "pending":

            print(
                f"↩️ Timeout ignored: "
                f"Request {request_id} "
                f"is already "
                f"{request.request_status}."
            )

            return request

        # ==================================
        # PROVIDER MUST EXIST
        # ==================================

        if request.provider_id is None:

            print(
                f"↩️ Timeout ignored: "
                f"Request {request_id} "
                f"has no provider."
            )

            return request

        # ==================================
        # CHECK ACTUAL TIME
        # ==================================

        if not has_provider_timed_out(request):

            print(
                f"⏳ Request {request_id} "
                f"has NOT timed out yet."
            )

            return request

        # ==================================
        # GET EMERGENCY
        # ==================================

        emergency = (
            db.query(Emergency)
            .filter(
                Emergency.emergency_id
                == request.emergency_id
            )
            .first()
        )

        if emergency is None:

            print(
                f"⚠️ Emergency not found "
                f"for Request {request_id}."
            )

            return None

        # ==================================
        # CURRENT PROVIDER
        # ==================================

        current_provider_id = int(
            request.provider_id
        )

        print(
            f"⏱️ Provider "
            f"{current_provider_id} "
            f"timed out for Request "
            f"{request_id}."
        )

        # ==================================
        # REJECT / REASSIGN
        # ==================================

        result = reject_request(
            db=db,
            request=request,
            emergency=emergency
        )

        # ==================================
        # NO RESULT
        # ==================================

        if result is None:

            print(
                f"⚠️ Timeout processing "
                f"failed for Request "
                f"{request_id}."
            )

            return None

        # ==================================
        # NO PROVIDER AVAILABLE
        # ==================================

        if result.provider_id is None:

            print(
                f"✅ Request "
                f"{request_id}: "
                f"Provider "
                f"{current_provider_id} "
                f"timed out."
            )

            print(
                f"⏳ Request "
                f"{request_id} "
                f"is waiting for another "
                f"provider."
            )

            return result

        # ==================================
        # SAME PROVIDER
        # ==================================

        if (
            result.provider_id
            == current_provider_id
        ):

            print(
                f"⚠️ Request "
                f"{request_id}: "
                f"No alternate provider "
                f"available."
            )

            return result

        # ==================================
        # SUCCESSFUL REASSIGNMENT
        # ==================================

        print(
            f"✅ Request "
            f"{request_id}: "
            f"Provider "
            f"{current_provider_id} "
            f"timed out."
        )

        print(
            f"➡️ Request "
            f"{request_id} "
            f"reassigned to Provider "
            f"{result.provider_id}."
        )

        return result

    except Exception as error:

        db.rollback()

        print(
            f"❌ Error processing timeout "
            f"for Request {request_id}: "
            f"{error}"
        )

        return None

    finally:

        db.close()


# ==========================================
# START TIMEOUT
# ==========================================

def start_timeout(
    request_id: int,
    provider_id: int | None = None,
    timeout: int = PROVIDER_TIMEOUT_SECONDS
):
    """
    Start the background timeout thread for
    a currently assigned service request.

    provider_id is optional.

    If provider_id is not supplied,
    it is loaded from the database.
    """

    db: Session = SessionLocal()

    try:

        # ==================================
        # GET REQUEST
        # ==================================

        request = (
            db.query(ServiceRequest)
            .filter(
                ServiceRequest.request_id
                == request_id
            )
            .first()
        )

        # ==================================
        # REQUEST NOT FOUND
        # ==================================

        if request is None:

            print(
                f"⚠️ Cannot start timeout: "
                f"Request {request_id} "
                f"not found."
            )

            return None

        # ==================================
        # REQUEST MUST BE PENDING
        # ==================================

        if request.request_status != "pending":

            print(
                f"⚠️ Cannot start timeout: "
                f"Request {request_id} "
                f"is "
                f"{request.request_status}."
            )

            return None

        # ==================================
        # USE DATABASE PROVIDER IF NEEDED
        # ==================================

        if provider_id is None:

            provider_id = request.provider_id

        # ==================================
        # PROVIDER REQUIRED
        # ==================================

        if provider_id is None:

            print(
                f"⚠️ Cannot start timeout: "
                f"Request {request_id} "
                f"has no provider."
            )

            return None

        # ==================================
        # REQUESTED TIME REQUIRED
        # ==================================

        if request.requested_at is None:

            print(
                f"⚠️ Cannot start timeout: "
                f"Request {request_id} "
                f"has no requested_at "
                f"timestamp."
            )

            return None

    except Exception as error:

        print(
            f"❌ Cannot start timeout "
            f"for Request {request_id}: "
            f"{error}"
        )

        return None

    finally:

        db.close()

    # ======================================
    # START THREAD
    # ======================================

    thread = threading.Thread(
        target=provider_timeout,
        args=(
            request_id,
            int(provider_id),
            int(timeout)
        ),
        daemon=True
    )

    thread.start()

    print(
        f"🚀 Timeout thread started: "
        f"Request {request_id}, "
        f"Provider {provider_id}, "
        f"{timeout}s"
    )

    return thread


# ==========================================
# RECOVER TIMED-OUT REQUESTS
# ==========================================

def recover_timed_out_requests():
    """
    Restart-safe timeout recovery.

    APScheduler can call this periodically.

    Background timeout threads disappear when
    Uvicorn restarts, but requested_at remains
    in the database.

    Therefore this function finds pending
    requests with assigned providers and
    processes expired ones.
    """

    db: Session = SessionLocal()

    try:

        # ==================================
        # FIND PENDING ASSIGNED REQUESTS
        # ==================================

        requests = (
            db.query(ServiceRequest)
            .filter(
                ServiceRequest.request_status
                == "pending",

                ServiceRequest.provider_id
                .isnot(None),

                ServiceRequest.requested_at
                .isnot(None)
            )
            .all()
        )

        # ==================================
        # CHECK EACH REQUEST
        # ==================================

        for request in requests:

            if not has_provider_timed_out(
                request
            ):
                continue

            provider_id = int(
                request.provider_id
            )

            print(
                f"🔎 Timeout recovery: "
                f"Request "
                f"{request.request_id}, "
                f"Provider "
                f"{provider_id}"
            )

            # ==================================
            # PROCESS TIMEOUT
            # ==================================

            process_request_timeout(
                request_id=request.request_id,
                expected_provider_id=provider_id
            )

    except Exception as error:

        db.rollback()

        print(
            f"❌ Timeout recovery error: "
            f"{error}"
        )

    finally:

        db.close()
