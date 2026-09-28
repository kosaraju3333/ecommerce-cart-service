from unittest.mock import patch, Mock

import httpx
import pytest
from fastapi import HTTPException

from app.clients.product_client import get_product


def test_get_product_success():

    mock_response = Mock()

    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": 1,
        "name": "iPhone Test",
        "price": "79999.00",
        "stock_quantity": 25,
        "is_active": True,
    }

    with patch(
        "app.clients.product_client.httpx.get",
        return_value=mock_response,
    ):

        product = get_product(1)

    assert product["id"] == 1
    assert product["name"] == "iPhone Test"


def test_get_product_404():

    mock_response = Mock()
    mock_response.status_code = 404

    with patch(
        "app.clients.product_client.httpx.get",
        return_value=mock_response,
    ):

        with pytest.raises(HTTPException) as exc:

            get_product(99999)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Product not found"


def test_get_product_service_error():

    mock_response = Mock()
    mock_response.status_code = 500

    with patch(
        "app.clients.product_client.httpx.get",
        return_value=mock_response,
    ):

        with pytest.raises(HTTPException) as exc:

            get_product(1)

    assert exc.value.status_code == 502

    assert (
        exc.value.detail
        == "Failed to communicate with Product Service"
    )


def test_get_product_service_unavailable():

    with patch(
        "app.clients.product_client.httpx.get",
        side_effect=httpx.RequestError(
            "Connection failed"
        ),
    ):

        with pytest.raises(HTTPException) as exc:

            get_product(1)

    assert exc.value.status_code == 503

    assert (
        exc.value.detail
        == "Product service is unavailable"
    )