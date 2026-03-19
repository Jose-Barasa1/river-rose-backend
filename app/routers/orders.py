from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import models, schemas
from app.routers.auth import get_current_user

router = APIRouter()


@router.post("/", response_model=schemas.OrderOut)
def create_order(
    order_data: schemas.OrderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not order_data.items:
        raise HTTPException(status_code=400, detail="Cart is empty.")

    total = 0.0
    order_items = []

    for item in order_data.items:
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found.")
        if product.stock < item.quantity:
            raise HTTPException(status_code=400, detail=f"Not enough stock for {product.name}.")

        unit_price = product.price
        total += unit_price * item.quantity
        order_items.append(
            models.OrderItem(
                product_id=product.id,
                quantity=item.quantity,
                unit_price=unit_price,
            )
        )
        product.stock -= item.quantity

    order = models.Order(
        user_id          = current_user.id,
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


@router.get("/", response_model=List[schemas.OrderOut])
def get_my_orders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.Order)
        .filter(models.Order.user_id == current_user.id)
        .order_by(models.Order.created_at.desc())
        .all()
    )


@router.get("/{order_id}", response_model=schemas.OrderOut)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    order = db.query(models.Order).filter(
        models.Order.id == order_id,
        models.Order.user_id == current_user.id,
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    return order


@router.patch("/{order_id}/status")
def update_order_status(
    order_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Admin — update order status."""
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    order.status = payload.get("status", order.status)
    db.commit()
    db.refresh(order)
    return order