from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db

from auth.oauth2 import get_current_user

from models.models import User
from models.payment import Payment

from schemas.payment import (
    PaymentCreate,
    PaymentUpdate,
    PaymentResponse
)
from services.payment_pricing_service import is_server_pricing_configured


router = APIRouter(
    prefix="/payments",
    tags=["Payments"]
)


@router.get("/readiness")
def get_payment_readiness(
    current_user: User = Depends(get_current_user),
):
    """Report why checkout is unavailable without exposing payment secrets."""
    pricing_configured = is_server_pricing_configured()
    # No payment processor is integrated and verified yet. Keep this false
    # until an integration with verified callbacks is implemented.
    gateway_configured = False
    checkout_available = pricing_configured and gateway_configured
    if not pricing_configured:
        message = (
            "Checkout is unavailable until server-side pricing and a "
            "verified payment gateway are configured."
        )
    else:
        message = (
            "Server-side pricing is configured; a verified payment "
            "gateway is still required."
        )
    return {
        "checkout_available": checkout_available,
        "server_side_pricing_configured": pricing_configured,
        "payment_gateway_configured": gateway_configured,
        "message": message,
    }

# ==========================
# CREATE PAYMENT
# ==========================

@router.post("/")
def create_payment(
    payment: PaymentCreate,
    current_user: User = Depends(get_current_user)
):

    # Fail closed: never create a payable-looking record from an untrusted
    # client amount while authoritative pricing and a processor are absent.
    raise HTTPException(
        status_code=503,
        detail=(
            "Checkout is unavailable until server-side pricing and a "
            "verified payment gateway are configured."
        ),
    )


# ==========================
# GET ALL PAYMENTS
# ==========================

@router.get(
    "/",
    response_model=list[PaymentResponse]
)
def get_all_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    return db.query(Payment).filter(
        Payment.user_id == current_user.user_id
    ).all()


# ==========================
# GET MY PAYMENTS
# ==========================

@router.get(
    "/my",
    response_model=list[PaymentResponse]
)
def get_my_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return db.query(Payment).filter(
        Payment.user_id == current_user.user_id
    ).all()


# ==========================
# GET SINGLE PAYMENT
# ==========================

@router.get(
    "/{payment_id}",
    response_model=PaymentResponse
)
def get_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    payment = db.query(Payment).filter(
        Payment.payment_id == payment_id,
        Payment.user_id == current_user.user_id,
    ).first()

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment not found"
        )

    return payment


# ==========================
# UPDATE PAYMENT
# ==========================

@router.put(
    "/{payment_id}",
    response_model=PaymentResponse
)
def update_payment(
    payment_id: int,
    data: PaymentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    payment = db.query(Payment).filter(
        Payment.payment_id == payment_id,
        Payment.user_id == current_user.user_id,
    ).first()

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment not found"
        )

    requested_status = getattr(data.payment_status, "value", data.payment_status)
    if requested_status != "failed" or payment.payment_status != "pending":
        raise HTTPException(
            status_code=400,
            detail=(
                "Payment success and refunds require a verified payment "
                "processor; clients may only mark a pending attempt failed."
            ),
        )

    payment.payment_status = "failed"
    db.commit()
    db.refresh(payment)
    return payment


# ==========================
# DELETE PAYMENT
# ==========================

@router.delete("/{payment_id}")
def delete_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    payment = db.query(Payment).filter(
        Payment.payment_id == payment_id,
        Payment.user_id == current_user.user_id,
    ).first()

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment not found"
        )

    if payment.payment_status not in {"pending", "failed"}:
        raise HTTPException(
            status_code=400,
            detail="Only pending or failed payment attempts can be deleted",
        )

    db.delete(payment)
    db.commit()

    return {
        "message": "Payment deleted successfully"
    }
