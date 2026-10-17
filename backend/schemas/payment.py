from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime
from typing import Optional
from enum import Enum


class PaymentMethod(str, Enum):
    upi = "upi"
    card = "card"
    cash = "cash"
    wallet = "wallet"


class PaymentStatus(str, Enum):
    pending = "pending"
    success = "success"
    failed = "failed"
    refunded = "refunded"


# ==========================
# CREATE PAYMENT
# ==========================

class PaymentCreate(BaseModel):
    request_id: int
    payment_method: PaymentMethod


# ==========================
# UPDATE PAYMENT
# ==========================

class PaymentUpdate(BaseModel):
    payment_status: PaymentStatus
    transaction_id: Optional[str] = None
    invoice_number: Optional[str] = None


# ==========================
# PAYMENT RESPONSE
# ==========================

class PaymentResponse(BaseModel):
    payment_id: int
    request_id: int
    user_id: int
    amount: Decimal
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    transaction_id: Optional[str]
    invoice_number: Optional[str]
    paid_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True
