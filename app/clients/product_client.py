import httpx

from fastapi import HTTPException, status

from app.config import settings


def get_product(product_id: int):

    url = (
        f"{settings.PRODUCT_SERVICE_URL}"
        f"/api/products/{product_id}"
    )

    try:

        response = httpx.get(
            url,
            timeout=5.0
        )

    except httpx.RequestError:

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Product service is unavailable"
        )

    if response.status_code == 404:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    if response.status_code != 200:

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to communicate with Product Service"
        )

    return response.json()