from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cart import Cart, CartItem
from app.schemas.cart import CartItemCreate, CartItemUpdate
from app.utils.dependencies import get_current_user
from app.clients.product_client import get_product


router = APIRouter(
    prefix="/api/cart",
    tags=["Cart"]
)


# ============================================================
# ADD PRODUCT TO CART
# ============================================================

@router.post("/items")
def add_to_cart(
    item: CartItemCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):

    user_id = current_user["id"]

    # Ask Product Service for product information
    product = get_product(item.product_id)

    # Check whether product is active
    if not product["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product is not available"
        )

    # Check stock
    if product["stock_quantity"] < item.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient stock"
        )

    # Find customer's cart
    cart = (
        db.query(Cart)
        .filter(Cart.user_id == user_id)
        .first()
    )

    # Create cart if it doesn't exist
    if not cart:

        cart = Cart(
            user_id=user_id
        )

        db.add(cart)
        db.commit()
        db.refresh(cart)

    # Check whether product already exists in cart
    cart_item = (
        db.query(CartItem)
        .filter(
            CartItem.cart_id == cart.id,
            CartItem.product_id == item.product_id
        )
        .first()
    )

    if cart_item:

        new_quantity = (
            cart_item.quantity + item.quantity
        )

        if product["stock_quantity"] < new_quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient stock"
            )

        cart_item.quantity = new_quantity

    else:

        cart_item = CartItem(
            cart_id=cart.id,
            product_id=item.product_id,
            quantity=item.quantity
        )

        db.add(cart_item)

    db.commit()
    db.refresh(cart_item)

    return {
        "message": "Product added to cart",
        "cart_item_id": cart_item.id,
        "product_id": cart_item.product_id,
        "quantity": cart_item.quantity
    }


# ============================================================
# GET CART
# ============================================================

@router.get("/")
def get_cart(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):

    user_id = current_user["id"]

    cart = (
        db.query(Cart)
        .filter(Cart.user_id == user_id)
        .first()
    )

    if not cart:
        return {
            "items": [],
            "total": 0
        }

    items = []
    total = Decimal("0.00")

    # for cart_item in cart.items:

    #     # Get current product information from Product Service
    #     product = get_product(
    #         cart_item.product_id
    #     )

    #     price = Decimal(
    #         str(product["price"])
    #     )

    #     subtotal = (
    #         price * cart_item.quantity
    #     )

    #     total += subtotal

    #     items.append({
    #         "cart_item_id": cart_item.id,
    #         "product_id": product["id"],
    #         "name": product["name"],
    #         "price": price,
    #         "image_url": product["image_url"],
    #         "quantity": cart_item.quantity,
    #         "subtotal": subtotal
    #     })

    for cart_item in cart.items:

        product = get_product(
            cart_item.product_id
        )

        # Product was removed from the store
        if not product["is_active"]:

            items.append({
                "cart_item_id": cart_item.id,
                "product_id": product["id"],
                "name": product["name"],
                "price": product["price"],
                "image_url": product["image_url"],
                "quantity": cart_item.quantity,
                "subtotal": 0,
                "available": False
            })

            continue

        price = Decimal(
            str(product["price"])
        )

        subtotal = (
            price * cart_item.quantity
        )

        total += subtotal

        items.append({
            "cart_item_id": cart_item.id,
            "product_id": product["id"],
            "name": product["name"],
            "price": price,
            "image_url": product["image_url"],
            "quantity": cart_item.quantity,
            "subtotal": subtotal,
            "available": True
        })

    return {
        "cart_id": cart.id,
        "items": items,
        "total": total
    }


# ============================================================
# UPDATE CART ITEM
# ============================================================

@router.put("/items/{cart_item_id}")
def update_cart_item(
    cart_item_id: int,
    item: CartItemUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):

    user_id = current_user["id"]

    # Find user's cart
    cart = (
        db.query(Cart)
        .filter(Cart.user_id == user_id)
        .first()
    )

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found"
        )

    # Find item in this user's cart
    cart_item = (
        db.query(CartItem)
        .filter(
            CartItem.id == cart_item_id,
            CartItem.cart_id == cart.id
        )
        .first()
    )

    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found"
        )

    # Ask Product Service for current stock
    product = get_product(
        cart_item.product_id
    )

    if item.quantity > product["stock_quantity"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient stock"
        )

    cart_item.quantity = item.quantity

    db.commit()
    db.refresh(cart_item)

    return {
        "message": "Cart item updated",
        "cart_item_id": cart_item.id,
        "product_id": cart_item.product_id,
        "quantity": cart_item.quantity
    }


# ============================================================
# DELETE CART ITEM
# ============================================================

@router.delete("/items/{cart_item_id}")
def delete_cart_item(
    cart_item_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):

    user_id = current_user["id"]

    cart = (
        db.query(Cart)
        .filter(Cart.user_id == user_id)
        .first()
    )

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found"
        )

    cart_item = (
        db.query(CartItem)
        .filter(
            CartItem.id == cart_item_id,
            CartItem.cart_id == cart.id
        )
        .first()
    )

    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found"
        )

    db.delete(cart_item)
    db.commit()

    return {
        "message": "Product removed from cart"
    }


# ============================================================
# CLEAR CART
# ============================================================

@router.delete("/")
def clear_cart(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):

    user_id = current_user["id"]

    cart = (
        db.query(Cart)
        .filter(Cart.user_id == user_id)
        .first()
    )

    if not cart:
        return {
            "message": "Cart is already empty"
        }

    # Delete all items but keep the cart itself
    (
        db.query(CartItem)
        .filter(CartItem.cart_id == cart.id)
        .delete(synchronize_session=False)
    )

    db.commit()

    return {
        "message": "Cart cleared successfully"
    }