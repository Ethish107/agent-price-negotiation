from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)

from .database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String,
        nullable=False
    )

    list_price = Column(
        Float,
        nullable=False
    )

    floor_price = Column(
        Float,
        nullable=False
    )

    current_inventory = Column(
        Integer,
        nullable=False,
        default=0
    )

    beginning_inventory = Column(
        Integer,
        nullable=False,
        default=0
    )

    weeks_remaining = Column(
        Float,
        nullable=True
    )


class Negotiation(Base):
    __tablename__ = "negotiations"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=False
    )

    buyer_target = Column(
        Float,
        nullable=False
    )

    buyer_budget = Column(
        Float,
        nullable=False
    )

    persona = Column(
        String,
        nullable=False
    )

    max_rounds = Column(
        Integer,
        nullable=False,
        default=4
    )

    status = Column(
        String,
        nullable=False,
        default="in_progress"
    )

    agreed_price = Column(
        Float,
        nullable=True
    )

    payment_link_id = Column(
        String,
        nullable=True
    )

    payment_link_url = Column(
        String,
        nullable=True
    )

    payment_status = Column(
        String,
        nullable=False,
        default="not_created"
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


class Round(Base):
    __tablename__ = "rounds"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    negotiation_id = Column(
        Integer,
        ForeignKey("negotiations.id"),
        nullable=False
    )

    round_no = Column(
        Integer,
        nullable=False
    )

    actor = Column(
        String,
        nullable=False
    )

    offer_amount = Column(
        Float,
        nullable=True
    )

    action = Column(
        String,
        nullable=False
    )

    reasoning = Column(
        Text,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


class Sale(Base):
    __tablename__ = "sales"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=False
    )

    final_price = Column(
        Float,
        nullable=False
    )

    quantity = Column(
        Integer,
        nullable=False,
        default=1
    )

    buyer_persona = Column(
        String,
        nullable=True
    )

    negotiation_rounds = Column(
        Integer,
        nullable=True
    )

    sold_at = Column(
        DateTime,
        default=datetime.utcnow
    )