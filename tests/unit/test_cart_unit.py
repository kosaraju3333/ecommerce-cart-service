from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.routers.cart import (
    add_to_cart,
    get_cart,
    update_cart_item,
    delete_cart_item,
    clear_cart,
)
from app.schemas.cart import CartItemCreate, CartItemUpdate


# ============================================================
# Helpers
# ============================================================

def current_user():
    return {
        "id": 1,
        "username": "customer1",
        "role": "CUSTOMER",
    }


def sample_product():
    return {
        "id": 10,
        "name": "iPhone 17",
        "price": "79999.00",
        "image_url": "/images/iphone-17.jpg",
        "stock_quantity": 25,
        "is_active": True,
    }


def sample_cart():
    cart = MagicMock()
    cart.id = 1
    cart.user_id = 1
    cart.items = []
    return cart


def sample_cart_item():
    item = MagicMock()
    item.id = 100
    item.cart_id = 1
    item.product_id = 10
    item.quantity = 2
    return item


# ============================================================
# ADD TO CART
# ============================================================

@patch("app.routers.cart.get_product")
def test_add_to_cart_new_item_success(mock_get_product):
    db = MagicMock()

    mock_get_product.return_value = sample_product()

    cart = sample_cart()

    # First query -> user's cart
    # Second query -> existing CartItem
    db.query.return_value.filter.return_value.first.side_effect = [
        cart,
        None,
    ]

    request = CartItemCreate(
        product_id=10,
        quantity=2,
    )

    result = add_to_cart(
        item=request,
        db=db,
        current_user=current_user(),
    )

    mock_get_product.assert_called_once_with(10)

    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()

    created_item = db.add.call_args[0][0]

    assert created_item.cart_id == 1
    assert created_item.product_id == 10
    assert created_item.quantity == 2

    assert result["message"] == "Product added to cart"
    assert result["product_id"] == 10
    assert result["quantity"] == 2


@patch("app.routers.cart.get_product")
def test_add_to_cart_creates_cart_when_missing(mock_get_product):
    db = MagicMock()

    mock_get_product.return_value = sample_product()

    # No existing cart.
    # Then no existing CartItem.
    db.query.return_value.filter.return_value.first.side_effect = [
        None,
        None,
    ]

    request = CartItemCreate(
        product_id=10,
        quantity=2,
    )

    result = add_to_cart(
        item=request,
        db=db,
        current_user=current_user(),
    )

    # Cart + CartItem should both be added.
    assert db.add.call_count == 2

    created_cart = db.add.call_args_list[0][0][0]
    created_item = db.add.call_args_list[1][0][0]

    assert created_cart.user_id == 1
    assert created_item.product_id == 10
    assert created_item.quantity == 2

    assert result["message"] == "Product added to cart"


@patch("app.routers.cart.get_product")
def test_add_existing_product_increases_quantity(mock_get_product):
    db = MagicMock()

    mock_get_product.return_value = sample_product()

    cart = sample_cart()
    cart_item = sample_cart_item()
    cart_item.quantity = 2

    db.query.return_value.filter.return_value.first.side_effect = [
        cart,
        cart_item,
    ]

    request = CartItemCreate(
        product_id=10,
        quantity=3,
    )

    result = add_to_cart(
        item=request,
        db=db,
        current_user=current_user(),
    )

    assert cart_item.quantity == 5
    assert result["quantity"] == 5

    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(cart_item)


@patch("app.routers.cart.get_product")
def test_add_to_cart_inactive_product(mock_get_product):
    db = MagicMock()

    product = sample_product()
    product["is_active"] = False

    mock_get_product.return_value = product

    request = CartItemCreate(
        product_id=10,
        quantity=1,
    )

    with pytest.raises(HTTPException) as exc:
        add_to_cart(
            item=request,
            db=db,
            current_user=current_user(),
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Product is not available"

    db.commit.assert_not_called()


@patch("app.routers.cart.get_product")
def test_add_to_cart_insufficient_stock(mock_get_product):
    db = MagicMock()

    product = sample_product()
    product["stock_quantity"] = 2

    mock_get_product.return_value = product

    request = CartItemCreate(
        product_id=10,
        quantity=5,
    )

    with pytest.raises(HTTPException) as exc:
        add_to_cart(
            item=request,
            db=db,
            current_user=current_user(),
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Insufficient stock"

    db.commit.assert_not_called()


@patch("app.routers.cart.get_product")
def test_add_existing_item_total_quantity_exceeds_stock(
    mock_get_product,
):
    db = MagicMock()

    product = sample_product()
    product["stock_quantity"] = 5

    mock_get_product.return_value = product

    cart = sample_cart()

    cart_item = sample_cart_item()
    cart_item.quantity = 4

    db.query.return_value.filter.return_value.first.side_effect = [
        cart,
        cart_item,
    ]

    # Existing 4 + requested 2 = 6, but stock = 5
    request = CartItemCreate(
        product_id=10,
        quantity=2,
    )

    with pytest.raises(HTTPException) as exc:
        add_to_cart(
            item=request,
            db=db,
            current_user=current_user(),
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Insufficient stock"

    assert cart_item.quantity == 4
    db.commit.assert_not_called()


# ============================================================
# GET CART
# ============================================================

def test_get_cart_when_cart_does_not_exist():
    db = MagicMock()

    db.query.return_value.filter.return_value.first.return_value = None

    result = get_cart(
        db=db,
        current_user=current_user(),
    )

    assert result == {
        "items": [],
        "total": 0,
    }


@patch("app.routers.cart.get_product")
def test_get_cart_success(mock_get_product):
    db = MagicMock()

    cart = sample_cart()

    cart_item = sample_cart_item()
    cart_item.quantity = 2

    cart.items = [cart_item]

    db.query.return_value.filter.return_value.first.return_value = cart

    mock_get_product.return_value = sample_product()

    result = get_cart(
        db=db,
        current_user=current_user(),
    )

    assert result["cart_id"] == 1
    assert len(result["items"]) == 1

    item = result["items"][0]

    assert item["product_id"] == 10
    assert item["quantity"] == 2
    assert item["price"] == Decimal("79999.00")
    assert item["subtotal"] == Decimal("159998.00")
    assert item["available"] is True

    assert result["total"] == Decimal("159998.00")


@patch("app.routers.cart.get_product")
def test_get_cart_with_inactive_product(mock_get_product):
    db = MagicMock()

    cart = sample_cart()

    cart_item = sample_cart_item()
    cart.items = [cart_item]

    db.query.return_value.filter.return_value.first.return_value = cart

    product = sample_product()
    product["is_active"] = False

    mock_get_product.return_value = product

    result = get_cart(
        db=db,
        current_user=current_user(),
    )

    assert result["cart_id"] == 1
    assert len(result["items"]) == 1

    item = result["items"][0]

    assert item["product_id"] == 10
    assert item["available"] is False
    assert item["subtotal"] == 0

    # Inactive product should not contribute to total.
    assert result["total"] == Decimal("0.00")


# ============================================================
# UPDATE CART ITEM
# ============================================================

@patch("app.routers.cart.get_product")
def test_update_cart_item_success(mock_get_product):
    db = MagicMock()

    cart = sample_cart()
    cart_item = sample_cart_item()

    db.query.return_value.filter.return_value.first.side_effect = [
        cart,
        cart_item,
    ]

    mock_get_product.return_value = sample_product()

    request = CartItemUpdate(
        quantity=5,
    )

    result = update_cart_item(
        cart_item_id=100,
        item=request,
        db=db,
        current_user=current_user(),
    )

    assert cart_item.quantity == 5

    assert result == {
        "message": "Cart item updated",
        "cart_item_id": 100,
        "product_id": 10,
        "quantity": 5,
    }

    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(cart_item)


def test_update_cart_item_cart_not_found():
    db = MagicMock()

    db.query.return_value.filter.return_value.first.return_value = None

    request = CartItemUpdate(
        quantity=2,
    )

    with pytest.raises(HTTPException) as exc:
        update_cart_item(
            cart_item_id=100,
            item=request,
            db=db,
            current_user=current_user(),
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "Cart not found"

    db.commit.assert_not_called()


def test_update_cart_item_not_found():
    db = MagicMock()

    cart = sample_cart()

    db.query.return_value.filter.return_value.first.side_effect = [
        cart,
        None,
    ]

    request = CartItemUpdate(
        quantity=2,
    )

    with pytest.raises(HTTPException) as exc:
        update_cart_item(
            cart_item_id=999,
            item=request,
            db=db,
            current_user=current_user(),
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "Cart item not found"

    db.commit.assert_not_called()


@patch("app.routers.cart.get_product")
def test_update_cart_item_insufficient_stock(mock_get_product):
    db = MagicMock()

    cart = sample_cart()
    cart_item = sample_cart_item()

    db.query.return_value.filter.return_value.first.side_effect = [
        cart,
        cart_item,
    ]

    product = sample_product()
    product["stock_quantity"] = 3

    mock_get_product.return_value = product

    request = CartItemUpdate(
        quantity=5,
    )

    with pytest.raises(HTTPException) as exc:
        update_cart_item(
            cart_item_id=100,
            item=request,
            db=db,
            current_user=current_user(),
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Insufficient stock"

    db.commit.assert_not_called()


# ============================================================
# DELETE CART ITEM
# ============================================================

def test_delete_cart_item_success():
    db = MagicMock()

    cart = sample_cart()
    cart_item = sample_cart_item()

    db.query.return_value.filter.return_value.first.side_effect = [
        cart,
        cart_item,
    ]

    result = delete_cart_item(
        cart_item_id=100,
        db=db,
        current_user=current_user(),
    )

    db.delete.assert_called_once_with(cart_item)
    db.commit.assert_called_once()

    assert result == {
        "message": "Product removed from cart"
    }


def test_delete_cart_item_cart_not_found():
    db = MagicMock()

    db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc:
        delete_cart_item(
            cart_item_id=100,
            db=db,
            current_user=current_user(),
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "Cart not found"

    db.delete.assert_not_called()
    db.commit.assert_not_called()


def test_delete_cart_item_not_found():
    db = MagicMock()

    cart = sample_cart()

    db.query.return_value.filter.return_value.first.side_effect = [
        cart,
        None,
    ]

    with pytest.raises(HTTPException) as exc:
        delete_cart_item(
            cart_item_id=999,
            db=db,
            current_user=current_user(),
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "Cart item not found"

    db.delete.assert_not_called()
    db.commit.assert_not_called()


# ============================================================
# CLEAR CART
# ============================================================

def test_clear_cart_success():
    db = MagicMock()

    cart = sample_cart()

    db.query.return_value.filter.return_value.first.return_value = cart

    result = clear_cart(
        db=db,
        current_user=current_user(),
    )

    db.query.return_value.filter.return_value.delete.assert_called_once_with(
        synchronize_session=False
    )

    db.commit.assert_called_once()

    assert result == {
        "message": "Cart cleared successfully"
    }


def test_clear_cart_when_cart_does_not_exist():
    db = MagicMock()

    db.query.return_value.filter.return_value.first.return_value = None

    result = clear_cart(
        db=db,
        current_user=current_user(),
    )

    assert result == {
        "message": "Cart is already empty"
    }

    db.commit.assert_not_called()