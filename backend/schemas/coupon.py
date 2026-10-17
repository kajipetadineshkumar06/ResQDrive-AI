from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime
from typing import Optional
from enum import Enum


# ==========================
# ENUMS
# ==========================

class DiscountType(str, Enum):
    percentage = "percentage"
    fixed = "fixed"


# ==========================
# CREATE COUPON
# ==========================

class CouponCreate(BaseModel):
    coupon_code: str
    description: Optional[str] = None
    discount_type: DiscountType
    discount_value: Decimal
    minimum_amount: Decimal = 0
    maximum_discount: Optional[Decimal] = None
    expiry_date: datetime
    is_active: bool = True


# ==========================
# UPDATE COUPON
# ==========================

class CouponUpdate(BaseModel):
    description: Optional[str] = None
    discount_type: DiscountType
    discount_value: Decimal
    minimum_amount: Decimal
    maximum_discount: Optional[Decimal] = None
    expiry_date: datetime
    is_active: bool


# ==========================
# APPLY COUPON
# ==========================

class ApplyCoupon(BaseModel):
    coupon_code: str
    amount: Decimal


# ==========================
# COUPON RESPONSE
# ==========================

class CouponResponse(BaseModel):
    coupon_id: int
    coupon_code: str
    description: Optional[str]
    discount_type: DiscountType
    discount_value: Decimal
    minimum_amount: Decimal
    maximum_discount: Optional[Decimal]
    expiry_date: datetime
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ==========================
# APPLY RESPONSE
# ==========================

class ApplyCouponResponse(BaseModel):
    coupon_code: str
    original_amount: Decimal
    discount: Decimal
    final_amount: Decimal