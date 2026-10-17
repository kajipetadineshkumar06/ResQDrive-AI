from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime
from typing import Optional


# ==========================================
# CREATE INVOICE
# ==========================================

class InvoiceCreate(BaseModel):
    payment_id: int
    total_amount: Decimal
    tax_amount: Decimal = 0
    discount_amount: Decimal = 0
    final_amount: Decimal


# ==========================================
# UPDATE INVOICE
# ==========================================

class InvoiceUpdate(BaseModel):
    total_amount: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    final_amount: Optional[Decimal] = None
    pdf_path: Optional[str] = None


# ==========================================
# RESPONSE
# ==========================================

class InvoiceResponse(BaseModel):
    invoice_id: int
    payment_id: int
    invoice_number: str
    invoice_date: datetime
    total_amount: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    final_amount: Decimal
    pdf_path: Optional[str]

    class Config:
        from_attributes = True