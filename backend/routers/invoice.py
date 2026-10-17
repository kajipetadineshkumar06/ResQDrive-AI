import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db

from auth.oauth2 import get_current_user

from models.models import User
from models.invoice import Invoice
from models.payment import Payment
from models.service_request import ServiceRequest

from schemas.invoice import (
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceResponse
)

router = APIRouter(
    prefix="/invoices",
    tags=["Invoices"]
)


# ======================================================
# CREATE INVOICE
# ======================================================

@router.post(
    "/",
    response_model=InvoiceResponse
)
def create_invoice(
    invoice: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    payment = db.query(Payment).filter(
        Payment.payment_id == invoice.payment_id,
        Payment.user_id == current_user.user_id
    ).first()

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment not found"
        )

    if payment.payment_status != "success":
        raise HTTPException(
            status_code=400,
            detail="An invoice can only be issued after payment is verified",
        )

    service_request = db.query(ServiceRequest).filter(
        ServiceRequest.request_id == payment.request_id,
        ServiceRequest.user_id == current_user.user_id,
        ServiceRequest.request_status == "completed",
    ).first()
    if not service_request:
        raise HTTPException(
            status_code=400,
            detail="Invoice requires the owner's completed service request",
        )

    if invoice.total_amount != payment.amount:
        raise HTTPException(
            status_code=400,
            detail="Invoice total must match the verified payment amount",
        )

    if (
        invoice.total_amount <= 0
        or invoice.tax_amount < 0
        or invoice.discount_amount < 0
        or invoice.discount_amount > invoice.total_amount + invoice.tax_amount
        or invoice.final_amount <= 0
    ):
        raise HTTPException(
            status_code=400,
            detail="Invoice amounts must be positive and internally consistent",
        )

    expected_final = (
        invoice.total_amount
        + invoice.tax_amount
        - invoice.discount_amount
    )
    if invoice.final_amount != expected_final:
        raise HTTPException(
            status_code=400,
            detail="Invoice final amount does not match total, tax, and discount",
        )

    existing_invoice = db.query(Invoice).filter(
        Invoice.payment_id == invoice.payment_id
    ).first()

    if existing_invoice:
        raise HTTPException(
            status_code=400,
            detail="Invoice already exists for this payment"
        )

    invoice_number = f"INV-{uuid.uuid4().hex[:10].upper()}"

    new_invoice = Invoice(
        payment_id=invoice.payment_id,
        invoice_number=invoice_number,
        total_amount=invoice.total_amount,
        tax_amount=invoice.tax_amount,
        discount_amount=invoice.discount_amount,
        final_amount=invoice.final_amount,
        pdf_path=None
    )

    payment.invoice_number = invoice_number
    db.add(new_invoice)
    db.commit()
    db.refresh(new_invoice)

    return new_invoice


# ======================================================
# GET ALL INVOICES
# ======================================================

@router.get(
    "/",
    response_model=list[InvoiceResponse]
)
def get_all_invoices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    return (
        db.query(Invoice)
        .join(Payment)
        .filter(Payment.user_id == current_user.user_id)
        .all()
    )


# ======================================================
# GET MY INVOICES
# ======================================================

@router.get(
    "/my",
    response_model=list[InvoiceResponse]
)
def get_my_invoices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return (
        db.query(Invoice)
        .join(Payment)
        .filter(Payment.user_id == current_user.user_id)
        .all()
    )


# ======================================================
# GET SINGLE INVOICE
# ======================================================

@router.get(
    "/{invoice_id}",
    response_model=InvoiceResponse
)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    invoice = (
        db.query(Invoice)
        .join(Payment)
        .filter(
            Invoice.invoice_id == invoice_id,
            Payment.user_id == current_user.user_id
        )
        .first()
    )

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found"
        )

    return invoice


# ======================================================
# UPDATE INVOICE
# ======================================================

@router.put(
    "/{invoice_id}",
    response_model=InvoiceResponse
)
def update_invoice(
    invoice_id: int,
    data: InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    invoice = (
        db.query(Invoice)
        .join(Payment)
        .filter(
            Invoice.invoice_id == invoice_id,
            Payment.user_id == current_user.user_id
        )
        .first()
    )

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found"
        )

    raise HTTPException(
        status_code=405,
        detail="Issued invoices are immutable",
    )



# ======================================================
# DELETE INVOICE
# ======================================================

@router.delete("/{invoice_id}")
def delete_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    invoice = (
        db.query(Invoice)
        .join(Payment)
        .filter(
            Invoice.invoice_id == invoice_id,
            Payment.user_id == current_user.user_id
        )
        .first()
    )

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found"
        )

    raise HTTPException(
        status_code=405,
        detail="Issued invoices cannot be deleted",
    )
