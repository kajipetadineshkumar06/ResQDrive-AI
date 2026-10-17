from sqlalchemy import (
    Column,
    Integer,
    String,
    DECIMAL,
    ForeignKey,
    TIMESTAMP
)

from sqlalchemy.sql import func

from database import Base


class Invoice(Base):

    __tablename__ = "invoices"

    invoice_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    payment_id = Column(
        Integer,
        ForeignKey("payments.payment_id"),
        nullable=False
    )

    invoice_number = Column(
        String(100),
        unique=True,
        nullable=False
    )

    invoice_date = Column(
        TIMESTAMP,
        server_default=func.now()
    )

    total_amount = Column(
        DECIMAL(10, 2),
        nullable=False
    )

    tax_amount = Column(
        DECIMAL(10, 2),
        default=0.00
    )

    discount_amount = Column(
        DECIMAL(10, 2),
        default=0.00
    )

    final_amount = Column(
        DECIMAL(10, 2),
        nullable=False
    )

    pdf_path = Column(
        String(255),
        nullable=True
    )