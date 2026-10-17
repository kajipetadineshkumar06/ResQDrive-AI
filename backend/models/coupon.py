from sqlalchemy import (
    Column,
    Integer,
    String,
    DECIMAL,
    Boolean,
    Enum,
    DateTime,
    TIMESTAMP
)

from sqlalchemy.sql import func

from database import Base


class Coupon(Base):

    __tablename__ = "coupons"

    coupon_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    coupon_code = Column(
        String(50),
        unique=True,
        nullable=False
    )

    description = Column(
        String(255)
    )

    discount_type = Column(
        Enum(
            "percentage",
            "fixed",
            name="coupon_discount_type"
        ),
        nullable=False
    )

    discount_value = Column(
        DECIMAL(10, 2),
        nullable=False
    )

    minimum_amount = Column(
        DECIMAL(10, 2),
        default=0
    )

    maximum_discount = Column(
        DECIMAL(10, 2),
        nullable=True
    )

    expiry_date = Column(
        DateTime,
        nullable=False
    )

    is_active = Column(
        Boolean,
        default=True
    )

    created_at = Column(
        TIMESTAMP,
        server_default=func.now()
    )