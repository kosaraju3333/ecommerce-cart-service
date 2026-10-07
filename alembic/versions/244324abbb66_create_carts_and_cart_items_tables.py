"""create carts and cart_items tables

Revision ID: 244324abbb66
Revises: 
Create Date: 2026-10-07 12:02:33.373230

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '244324abbb66'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:

    op.create_table(
        "carts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True
        ),
        sa.PrimaryKeyConstraint("id")
    )

    op.create_index(
        "ix_carts_id",
        "carts",
        ["id"],
        unique=False
    )

    op.create_index(
        "ix_carts_user_id",
        "carts",
        ["user_id"],
        unique=True
    )

    op.create_table(
        "cart_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cart_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),

        sa.ForeignKeyConstraint(
            ["cart_id"],
            ["carts.id"]
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint(
            "cart_id",
            "product_id",
            name="uq_cart_product"
        )
    )

    op.create_index(
        "ix_cart_items_id",
        "cart_items",
        ["id"],
        unique=False
    )

    op.create_index(
        "ix_cart_items_product_id",
        "cart_items",
        ["product_id"],
        unique=False
    )

def downgrade() -> None:

    op.drop_index(
        "ix_cart_items_product_id",
        table_name="cart_items"
    )

    op.drop_index(
        "ix_cart_items_id",
        table_name="cart_items"
    )

    op.drop_table("cart_items")

    op.drop_index(
        "ix_carts_user_id",
        table_name="carts"
    )

    op.drop_index(
        "ix_carts_id",
        table_name="carts"
    )

    op.drop_table("carts")