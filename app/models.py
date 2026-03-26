from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class User(Base):
    __tablename__ = "users"
    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String(120))
    email         = Column(String(120), unique=True, index=True)
    password_hash = Column(String(256), nullable=True)
    set_password_token    = Column(String(256), nullable=True)
    set_password_token_exp = Column(DateTime,   nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)

    orders  = relationship("Order",  back_populates="user")
    reviews = relationship("Review", back_populates="user")


class Product(Base):
    __tablename__ = "products"
    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(150))
    price       = Column(Float)
    description = Column(Text,        nullable=True)
    category    = Column(String(100), nullable=True)
    image       = Column(String(500), nullable=True)
    stock       = Column(Integer, default=0)
    created_at  = Column(DateTime, default=datetime.utcnow)

    order_items = relationship("OrderItem", back_populates="product")
    reviews     = relationship("Review",    back_populates="product")


class Order(Base):
    __tablename__ = "orders"
    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=True)
    total_price = Column(Float)
    # UPDATE THIS LINE - add all possible statuses
    status      = Column(String, default="pending")
    created_at  = Column(DateTime, default=datetime.utcnow)

    # ── Delivery ───────────────────────────────
    delivery_name    = Column(String(120), nullable=True)
    delivery_phone   = Column(String(20),  nullable=True)
    delivery_email   = Column(String(140), nullable=True)
    delivery_address = Column(String(255), nullable=True)
    delivery_notes   = Column(String(500), nullable=True)

    # ── M-Pesa ─────────────────────────────────
    mpesa_code          = Column(String(50),  nullable=True)
    payment_phone       = Column(String(20),  nullable=True)
    checkout_request_id = Column(String(100), nullable=True)

    user  = relationship("User",      back_populates="orders")
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"
    id         = Column(Integer, primary_key=True, index=True)
    order_id   = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity   = Column(Integer, default=1)
    unit_price = Column(Float)

    order   = relationship("Order",   back_populates="items")
    product = relationship("Product", back_populates="order_items")


class Review(Base):
    __tablename__ = "reviews"
    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"),    nullable=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    name       = Column(String(120))
    comment    = Column(Text)
    rating     = Column(Integer, default=5)
    created_at = Column(DateTime, default=datetime.utcnow)

    user    = relationship("User",    back_populates="reviews")
    product = relationship("Product", back_populates="reviews")


class CommunityPost(Base):
    __tablename__ = "community_posts"
    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(120), nullable=False)
    text       = Column(Text,        nullable=False)
    likes      = Column(Integer, default=0)
    tag        = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)