import pytest

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models.cart import Cart, CartItem
from app.config import settings


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


@pytest.fixture()
def db():

    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db):

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def create_token(user_id, username, role="CUSTOMER"):

    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
    }

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


@pytest.fixture()
def customer_headers():

    token = create_token(
        1,
        "customer_test",
    )

    return {
        "Authorization": f"Bearer {token}"
    }


@pytest.fixture()
def second_customer_headers():

    token = create_token(
        2,
        "customer_two",
    )

    return {
        "Authorization": f"Bearer {token}"
    }


@pytest.fixture()
def cart(db):

    cart = Cart(user_id=1)

    db.add(cart)
    db.commit()
    db.refresh(cart)

    return cart


@pytest.fixture()
def cart_item(db, cart):

    item = CartItem(
        cart_id=cart.id,
        product_id=1,
        quantity=2,
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return item


@pytest.fixture()
def mock_product():

    return {
        "id": 1,
        "name": "iPhone Test",
        "description": "Test phone",
        "price": "79999.00",
        "sku": "IPHONE-001",
        "category": "Smartphones",
        "image_url": "/images/iphone.jpg",
        "rating": 4.5,
        "stock_quantity": 25,
        "is_active": True,
    }