from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# ── Auth ──────────────────────────────────────────────
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    confirm_password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class SetPassword(BaseModel):
    token: str
    password: str
    confirm_password: str


# ── Products ──────────────────────────────────────────
class ProductCreate(BaseModel):
    name: str
    price: float
    description: Optional[str] = None
    category: Optional[str] = None
    image: Optional[str] = None
    stock: Optional[int] = 0

class ProductOut(BaseModel):
    id: int
    name: str
    price: float
    description: Optional[str]
    category: Optional[str]
    image: Optional[str]
    stock: int
    created_at: datetime

    class Config:
        from_attributes = True


# ── Orders ────────────────────────────────────────────
class OrderItemIn(BaseModel):
    product_id: int
    quantity:   int

class OrderCreate(BaseModel):
    items:            List[OrderItemIn]
    delivery_name:    str                # required for all
    delivery_email:   EmailStr           # required — used to create/match guest account
    delivery_phone:   str                # required for all
    delivery_address: str                # required for all
    delivery_notes:   Optional[str] = None

class OrderItemOut(BaseModel):
    product_id: int
    quantity:   int
    unit_price: float

    class Config:
        from_attributes = True

class OrderOut(BaseModel):
    id:               int
    total_price:      float
    status:           str
    created_at:       datetime
    items:            List[OrderItemOut]

    # Delivery
    delivery_name:    Optional[str] = None
    delivery_phone:   Optional[str] = None
    delivery_email: Optional[EmailStr] = None
    delivery_address: Optional[str] = None
    delivery_notes:   Optional[str] = None

    # M-Pesa
    mpesa_code:           Optional[str] = None
    payment_phone:        Optional[str] = None
    checkout_request_id:  Optional[str] = None

    class Config:
        from_attributes = True


# ── Reviews ───────────────────────────────────────────
class ReviewCreate(BaseModel):
    name:       str
    comment:    str
    rating:     int = 5
    product_id: Optional[int] = None

class ReviewOut(BaseModel):
    id:         int
    name:       str
    comment:    str
    rating:     int
    created_at: datetime

    class Config:
        from_attributes = True


# ── Community Posts ───────────────────────────────────
class CommunityPostCreate(BaseModel):
    name: str
    text: str
    tag:  Optional[str] = None

class CommunityPostOut(BaseModel):
    id:         int
    name:       str
    text:       str
    likes:      int
    tag:        Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True