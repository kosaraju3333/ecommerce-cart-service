import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.models.cart import Cart, CartItem
from app.routers.cart import router as cart_router


# Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="E-Commerce Cart Service",
    description="Cart microservice for the E-Commerce platform",
    version="1.0.0"
)

frontend_url = os.getenv(
    "FRONTEND_URL",
    "http://localhost:4200"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(cart_router)


@app.get("/")
def root():

    return {
        "service": "cart-service",
        "status": "running"
    }


@app.get("/health")
def health_check():

    return {
        "service": "cart-service",
        "status": "UP"
    }