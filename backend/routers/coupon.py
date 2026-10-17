from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db

from models.coupon import Coupon

from schemas.coupon import (
    CouponCreate,
    CouponUpdate,
    CouponResponse,
    ApplyCoupon,
    ApplyCouponResponse
)

router = APIRouter(
    prefix="/coupons",
    tags=["Coupons"]
)


# ======================================================
# CREATE COUPON
# ======================================================

@router.post(
    "/",
    response_model=CouponResponse
)
def create_coupon(
    coupon: CouponCreate,
    db: Session = Depends(get_db)
):

    existing_coupon = db.query(Coupon).filter(
        Coupon.coupon_code == coupon.coupon_code
    ).first()

    if existing_coupon:
        raise HTTPException(
            status_code=400,
            detail="Coupon already exists"
        )

    new_coupon = Coupon(
        coupon_code=coupon.coupon_code,
        description=coupon.description,
        discount_type=coupon.discount_type,
        discount_value=coupon.discount_value,
        minimum_amount=coupon.minimum_amount,
        maximum_discount=coupon.maximum_discount,
        expiry_date=coupon.expiry_date,
        is_active=coupon.is_active
    )

    db.add(new_coupon)
    db.commit()
    db.refresh(new_coupon)

    return new_coupon


# ======================================================
# GET ALL COUPONS
# ======================================================

@router.get(
    "/",
    response_model=list[CouponResponse]
)
def get_all_coupons(
    db: Session = Depends(get_db)
):

    return db.query(Coupon).all()


# ======================================================
# GET SINGLE COUPON
# ======================================================

@router.get(
    "/{coupon_id}",
    response_model=CouponResponse
)
def get_coupon(
    coupon_id: int,
    db: Session = Depends(get_db)
):

    coupon = db.query(Coupon).filter(
        Coupon.coupon_id == coupon_id
    ).first()

    if not coupon:
        raise HTTPException(
            status_code=404,
            detail="Coupon not found"
        )

    return coupon


# ======================================================
# UPDATE COUPON
# ======================================================

@router.put(
    "/{coupon_id}",
    response_model=CouponResponse
)
def update_coupon(
    coupon_id: int,
    data: CouponUpdate,
    db: Session = Depends(get_db)
):

    coupon = db.query(Coupon).filter(
        Coupon.coupon_id == coupon_id
    ).first()

    if not coupon:
        raise HTTPException(
            status_code=404,
            detail="Coupon not found"
        )

    coupon.description = data.description
    coupon.discount_type = data.discount_type
    coupon.discount_value = data.discount_value
    coupon.minimum_amount = data.minimum_amount
    coupon.maximum_discount = data.maximum_discount
    coupon.expiry_date = data.expiry_date
    coupon.is_active = data.is_active

    db.commit()
    db.refresh(coupon)

    return coupon


# ======================================================
# DELETE COUPON
# ======================================================

@router.delete("/{coupon_id}")
def delete_coupon(
    coupon_id: int,
    db: Session = Depends(get_db)
):

    coupon = db.query(Coupon).filter(
        Coupon.coupon_id == coupon_id
    ).first()

    if not coupon:
        raise HTTPException(
            status_code=404,
            detail="Coupon not found"
        )

    db.delete(coupon)
    db.commit()

    return {
        "message": "Coupon deleted successfully"
    }


# ======================================================
# APPLY COUPON
# ======================================================

@router.post(
    "/apply",
    response_model=ApplyCouponResponse
)
def apply_coupon(
    data: ApplyCoupon,
    db: Session = Depends(get_db)
):

    coupon = db.query(Coupon).filter(
        Coupon.coupon_code == data.coupon_code
    ).first()

    if not coupon:
        raise HTTPException(
            status_code=404,
            detail="Invalid coupon"
        )

    if not coupon.is_active:
        raise HTTPException(
            status_code=400,
            detail="Coupon is inactive"
        )

    if coupon.expiry_date < datetime.utcnow():
        raise HTTPException(
            status_code=400,
            detail="Coupon expired"
        )

    if data.amount < coupon.minimum_amount:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum purchase amount is {coupon.minimum_amount}"
        )

    discount = Decimal("0")

    if coupon.discount_type == "percentage":

        discount = (
            data.amount *
            coupon.discount_value
        ) / Decimal("100")

        if (
            coupon.maximum_discount is not None
            and
            discount > coupon.maximum_discount
        ):
            discount = coupon.maximum_discount

    else:

        discount = coupon.discount_value

    final_amount = data.amount - discount

    if final_amount < 0:
        final_amount = Decimal("0")

    return ApplyCouponResponse(
        coupon_code=coupon.coupon_code,
        original_amount=data.amount,
        discount=discount,
        final_amount=final_amount
    )