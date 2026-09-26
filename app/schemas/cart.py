from pydantic import BaseModel, Field


class CartItemCreate(BaseModel):

    product_id: int

    quantity: int = Field(
        default=1,
        ge=1
    )


class CartItemUpdate(BaseModel):

    quantity: int = Field(
        ge=1
    )