from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import secrets

from app.database import get_db
from app import models, schemas
from app.routers.auth import get_current_user, get_current_user_from_token
from app.email import send_set_password_email
from app.config import settings

router = APIRouter()


# ── Admin helper ──────────────────────────────────────────────────────────────

def require_admin(current_user: models.User = Depends(get_current_user)):
    """Raises 403 if the current user is not the designated admin."""
    if current_user.email != settings.ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Admins only.")
    return current_user


# ── Optional user (for guest checkout) ───────────────────────────────────────

def get_optional_user(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[models.User]:
    """Returns the logged-in user if token is valid, otherwise None (guest)."""
    try:
        token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        if not token:
            return None
        return get_current_user_from_token(token=token, db=db)
    except Exception:
        return None


# ── Create order ──────────────────────────────────────────────────────────────

@router.post("/", response_model=schemas.OrderOut)
def create_order(
    order_data: schemas.OrderCreate,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_user),
):
    if not order_data.items:
        raise HTTPException(status_code=400, detail="Cart is empty.")

    # ── Guest flow ────────────────────────────────────────────────────────
    if not current_user:
        missing = [
            field for field in ("delivery_name", "delivery_phone", "delivery_address", "delivery_email")
            if not getattr(order_data, field, None)
        ]
        if missing:
            raise HTTPException(
                status_code=422,
                detail=f"Please fill in: {', '.join(missing)}."
            )

        existing = db.query(models.User).filter(
            models.User.email == order_data.delivery_email
        ).first()

        if existing:
            # Attach order to existing account
            current_user = existing
        else:
            # Create passwordless guest account
            token       = secrets.token_urlsafe(48)
            token_exp   = datetime.utcnow() + timedelta(hours=48)
            new_user    = models.User(
                name                   = order_data.delivery_name,
                email                  = order_data.delivery_email,
                password_hash          = None,
                set_password_token     = token,
                set_password_token_exp = token_exp,
            )
            db.add(new_user)
            db.flush()
            current_user = new_user

            try:
                send_set_password_email(
                    to_email=order_data.delivery_email,
                    name=order_data.delivery_name,
                    token=token,
                )
            except Exception:
                pass  # don't block order if email fails

    # ── Logged-in user: require delivery details if not provided ──────────
    else:
        missing = [
            field for field in ("delivery_name", "delivery_phone", "delivery_address")
            if not getattr(order_data, field, None)
        ]
        if missing:
            raise HTTPException(
                status_code=422,
                detail=f"Please fill in: {', '.join(missing)}."
            )

    # ── Build order ───────────────────────────────────────────────────────
    total       = 0.0
    order_items = []

    for item in order_data.items:
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found.")
        if product.stock < item.quantity:
            raise HTTPException(status_code=400, detail=f"Not enough stock for {product.name}.")

        unit_price = product.price
        total     += unit_price * item.quantity
        order_items.append(
            models.OrderItem(
                product_id=product.id,
                quantity=item.quantity,
                unit_price=unit_price,
            )
        )
        product.stock -= item.quantity

    order = models.Order(
        user_id          = current_user.id if current_user else None,
        total_price      = round(total, 2),
        status           = "pending",
        delivery_name    = order_data.delivery_name,
        delivery_phone   = order_data.delivery_phone,
        delivery_address = order_data.delivery_address,
        delivery_notes   = order_data.delivery_notes,
    )
    db.add(order)
    db.flush()

    for oi in order_items:
        oi.order_id = order.id
        db.add(oi)

    db.commit()
    db.refresh(order)
    return order


# ── Get orders ────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[schemas.OrderOut])
def get_orders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Admin sees all orders; regular users see only their own
    if current_user.email == settings.ADMIN_EMAIL:
        return (
            db.query(models.Order)
            .order_by(models.Order.created_at.desc())
            .all()
        )
    return (
        db.query(models.Order)
        .filter(models.Order.user_id == current_user.id)
        .order_by(models.Order.created_at.desc())
        .all()
    )


# ── Get single order ──────────────────────────────────────────────────────────

@router.get("/{order_id}", response_model=schemas.OrderOut)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = db.query(models.Order).filter(models.Order.id == order_id)
    if current_user.email != settings.ADMIN_EMAIL:
        query = query.filter(models.Order.user_id == current_user.id)

    order = query.first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    return order


# ── Update order status (admin only) ─────────────────────────────────────────

@router.patch("/{order_id}/status")
def update_order_status(
    order_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    order.status = payload.get("status", order.status)
    db.commit()
    db.refresh(order)
    return order