from unittest.mock import patch

import httpx

from fastapi import HTTPException

from app.models.cart import CartItem


# ============================================================
# ROOT / HEALTH
# ============================================================


def test_root(client):

    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["service"] == "cart-service"
    assert response.json()["status"] == "running"


def test_health(client):

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "UP"


# ============================================================
# AUTHENTICATION
# ============================================================


def test_get_cart_without_token(client):

    response = client.get("/api/cart/")

    assert response.status_code in (401, 403)


def test_get_cart_invalid_token(client):

    response = client.get(
        "/api/cart/",
        headers={
            "Authorization": "Bearer invalid.jwt.token"
        },
    )

    assert response.status_code == 401


# ============================================================
# EMPTY CART
# ============================================================


def test_get_empty_cart(
    client,
    customer_headers,
):

    response = client.get(
        "/api/cart/",
        headers=customer_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["items"] == []
    assert data["total"] == 0


# ============================================================
# ADD PRODUCT
# ============================================================


def test_add_product_to_cart(
    client,
    customer_headers,
    mock_product,
):

    with patch(
        "app.routers.cart.get_product",
        return_value=mock_product,
    ):

        response = client.post(
            "/api/cart/items",
            json={
                "product_id": 1,
                "quantity": 2,
            },
            headers=customer_headers,
        )

    assert response.status_code == 200

    data = response.json()

    assert data["message"] == "Product added to cart"
    assert data["product_id"] == 1
    assert data["quantity"] == 2


def test_add_same_product_increases_quantity(
    client,
    customer_headers,
    cart_item,
    mock_product,
):

    with patch(
        "app.routers.cart.get_product",
        return_value=mock_product,
    ):

        response = client.post(
            "/api/cart/items",
            json={
                "product_id": 1,
                "quantity": 3,
            },
            headers=customer_headers,
        )

    assert response.status_code == 200

    # Existing 2 + added 3
    assert response.json()["quantity"] == 5


def test_add_product_insufficient_stock(
    client,
    customer_headers,
    mock_product,
):

    mock_product["stock_quantity"] = 2

    with patch(
        "app.routers.cart.get_product",
        return_value=mock_product,
    ):

        response = client.post(
            "/api/cart/items",
            json={
                "product_id": 1,
                "quantity": 5,
            },
            headers=customer_headers,
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Insufficient stock"


def test_existing_item_cannot_exceed_stock(
    client,
    customer_headers,
    cart_item,
    mock_product,
):

    # Existing quantity = 2
    # Add 4
    # New quantity = 6
    # Stock = 5

    mock_product["stock_quantity"] = 5

    with patch(
        "app.routers.cart.get_product",
        return_value=mock_product,
    ):

        response = client.post(
            "/api/cart/items",
            json={
                "product_id": 1,
                "quantity": 4,
            },
            headers=customer_headers,
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Insufficient stock"


def test_cannot_add_inactive_product(
    client,
    customer_headers,
    mock_product,
):

    mock_product["is_active"] = False

    with patch(
        "app.routers.cart.get_product",
        return_value=mock_product,
    ):

        response = client.post(
            "/api/cart/items",
            json={
                "product_id": 1,
                "quantity": 1,
            },
            headers=customer_headers,
        )

    assert response.status_code == 400

    assert (
        response.json()["detail"]
        == "Product is not available"
    )


def test_add_quantity_zero(
    client,
    customer_headers,
):

    response = client.post(
        "/api/cart/items",
        json={
            "product_id": 1,
            "quantity": 0,
        },
        headers=customer_headers,
    )

    # Pydantic Field(ge=1)
    assert response.status_code == 422


def test_add_negative_quantity(
    client,
    customer_headers,
):

    response = client.post(
        "/api/cart/items",
        json={
            "product_id": 1,
            "quantity": -5,
        },
        headers=customer_headers,
    )

    assert response.status_code == 422


# ============================================================
# PRODUCT SERVICE ERRORS
# ============================================================


def test_product_not_found(
    client,
    customer_headers,
):

    with patch(
        "app.routers.cart.get_product",
        side_effect=HTTPException(
            status_code=404,
            detail="Product not found",
        ),
    ):

        response = client.post(
            "/api/cart/items",
            json={
                "product_id": 99999,
                "quantity": 1,
            },
            headers=customer_headers,
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


def test_product_service_unavailable(
    client,
    customer_headers,
):

    with patch(
        "app.routers.cart.get_product",
        side_effect=HTTPException(
            status_code=503,
            detail="Product service is unavailable",
        ),
    ):

        response = client.post(
            "/api/cart/items",
            json={
                "product_id": 1,
                "quantity": 1,
            },
            headers=customer_headers,
        )

    assert response.status_code == 503

    assert (
        response.json()["detail"]
        == "Product service is unavailable"
    )


# ============================================================
# GET CART
# ============================================================


def test_get_cart_with_items(
    client,
    customer_headers,
    cart_item,
    mock_product,
):

    with patch(
        "app.routers.cart.get_product",
        return_value=mock_product,
    ):

        response = client.get(
            "/api/cart/",
            headers=customer_headers,
        )

    assert response.status_code == 200

    data = response.json()

    assert len(data["items"]) == 1

    item = data["items"][0]

    assert item["product_id"] == 1
    assert item["name"] == "iPhone Test"
    assert item["quantity"] == 2
    assert item["available"] is True

    # 79999 * 2
    assert float(item["subtotal"]) == 159998.00
    assert float(data["total"]) == 159998.00


def test_inactive_product_in_cart_marked_unavailable(
    client,
    customer_headers,
    cart_item,
    mock_product,
):

    mock_product["is_active"] = False

    with patch(
        "app.routers.cart.get_product",
        return_value=mock_product,
    ):

        response = client.get(
            "/api/cart/",
            headers=customer_headers,
        )

    assert response.status_code == 200

    data = response.json()

    assert len(data["items"]) == 1
    assert data["items"][0]["available"] is False
    assert data["items"][0]["subtotal"] == 0

    assert float(data["total"]) == 0


# ============================================================
# UPDATE
# ============================================================


def test_update_cart_item(
    client,
    customer_headers,
    cart_item,
    mock_product,
):

    with patch(
        "app.routers.cart.get_product",
        return_value=mock_product,
    ):

        response = client.put(
            f"/api/cart/items/{cart_item.id}",
            json={
                "quantity": 5
            },
            headers=customer_headers,
        )

    assert response.status_code == 200
    assert response.json()["quantity"] == 5


def test_update_quantity_exceeds_stock(
    client,
    customer_headers,
    cart_item,
    mock_product,
):

    mock_product["stock_quantity"] = 3

    with patch(
        "app.routers.cart.get_product",
        return_value=mock_product,
    ):

        response = client.put(
            f"/api/cart/items/{cart_item.id}",
            json={
                "quantity": 10
            },
            headers=customer_headers,
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Insufficient stock"


def test_update_quantity_zero(
    client,
    customer_headers,
    cart_item,
):

    response = client.put(
        f"/api/cart/items/{cart_item.id}",
        json={
            "quantity": 0
        },
        headers=customer_headers,
    )

    assert response.status_code == 422


def test_update_nonexistent_cart_item(
    client,
    customer_headers,
    cart,
):

    response = client.put(
        "/api/cart/items/99999",
        json={
            "quantity": 2
        },
        headers=customer_headers,
    )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "Cart item not found"
    )


# ============================================================
# USER ISOLATION
# ============================================================


def test_second_customer_cannot_update_first_users_item(
    client,
    second_customer_headers,
    cart_item,
):

    response = client.put(
        f"/api/cart/items/{cart_item.id}",
        json={
            "quantity": 5
        },
        headers=second_customer_headers,
    )

    # User 2 doesn't have a cart.
    assert response.status_code == 404
    assert response.json()["detail"] == "Cart not found"


def test_second_customer_cannot_delete_first_users_item(
    client,
    second_customer_headers,
    cart_item,
):

    response = client.delete(
        f"/api/cart/items/{cart_item.id}",
        headers=second_customer_headers,
    )

    assert response.status_code == 404


# ============================================================
# DELETE ITEM
# ============================================================


def test_delete_cart_item(
    client,
    customer_headers,
    cart_item,
    db,
):

    item_id = cart_item.id

    response = client.delete(
        f"/api/cart/items/{item_id}",
        headers=customer_headers,
    )

    assert response.status_code == 200

    assert (
        response.json()["message"]
        == "Product removed from cart"
    )

    deleted = (
        db.query(CartItem)
        .filter(CartItem.id == item_id)
        .first()
    )

    assert deleted is None


def test_delete_nonexistent_cart_item(
    client,
    customer_headers,
    cart,
):

    response = client.delete(
        "/api/cart/items/99999",
        headers=customer_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Cart item not found"


# ============================================================
# CLEAR CART
# ============================================================


def test_clear_cart(
    client,
    customer_headers,
    cart_item,
    db,
):

    response = client.delete(
        "/api/cart/",
        headers=customer_headers,
    )

    assert response.status_code == 200

    assert (
        response.json()["message"]
        == "Cart cleared successfully"
    )

    remaining_items = db.query(CartItem).all()

    assert len(remaining_items) == 0


def test_clear_cart_when_no_cart_exists(
    client,
    customer_headers,
):

    response = client.delete(
        "/api/cart/",
        headers=customer_headers,
    )

    assert response.status_code == 200

    assert (
        response.json()["message"]
        == "Cart is already empty"
    )