from sqlalchemy import (
    Column,
    Integer,
    String,
    DECIMAL,
    Enum,
    TIMESTAMP,
    ForeignKey
)

from sqlalchemy.sql import func

from database import Base


class Payment(Base):

    __tablename__ = "payments"

    payment_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    request_id = Column(
        Integer,
        ForeignKey("service_requests.request_id"),
        nullable=False
    )

    user_id = Column(
        Integer,
        ForeignKey("users.user_id"),
        nullable=False
    )

    amount = Column(
        DECIMAL(10, 2),
        nullable=False
    )

    payment_method = Column(
        Enum(
            "upi",
            "card",
            "cash",
            "wallet"
        ),
        default="upi"
    )

    payment_status = Column(
        Enum(
            "pending",
            "success",
            "failed",
            "refunded"
        ),
        default="pending"
    )

    transaction_id = Column(
        String(100),
        nullable=True
    )

    invoice_number = Column(
        String(100),
        nullable=True
    )

    paid_at = Column(
        TIMESTAMP,
        nullable=True
    )

    created_at = Column(
        TIMESTAMP,
        server_default=func.now()
    )