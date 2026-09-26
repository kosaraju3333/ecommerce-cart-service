from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    DateTime,
    UniqueConstraint
)

from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Cart(Base):

    __tablename__ = "carts"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    # User ID comes from Auth Service JWT.
    # No foreign key to users table.
    user_id = Column(
        Integer,
        nullable=False,
        unique=True,
        index=True
    )

    created_at = Column(
        DateTime,
        server_default=func.now()
    )

    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )

    items = relationship(
        "CartItem",
        back_populates="cart",
        cascade="all, delete-orphan"
    )


class CartItem(Base):

    __tablename__ = "cart_items"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    # Internal Cart Service relationship
    cart_id = Column(
        Integer,
        ForeignKey("carts.id"),
        nullable=False
    )

    # Product ID belongs to Product Service.
    # Store only the ID -- no foreign key.
    product_id = Column(
        Integer,
        nullable=False,
        index=True
    )

    quantity = Column(
        Integer,
        nullable=False,
        default=1
    )

    cart = relationship(
        "Cart",
        back_populates="items"
    )

    __table_args__ = (
        UniqueConstraint(
            "cart_id",
            "product_id",
            name="uq_cart_product"
        ),
    )