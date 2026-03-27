# app/routers/admin.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.database import get_db
from app import models, schemas
from app.routers.auth import get_current_admin_user, get_current_user

router = APIRouter()

# ==================== AUTH CHECK ====================

@router.get("/check")
def check_admin(
    current_user: models.User = Depends(get_current_user)
):
    """Check if current user is admin"""
    return {"isAdmin": current_user.is_admin}

# ==================== DASHBOARD STATISTICS ====================

@router.get("/dashboard-stats")
def get_dashboard_stats(
    current_admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics (Admin only)"""
    total_users = db.query(models.User).count()
    total_products = db.query(models.Product).count()
    total_orders = db.query(models.Order).count()
    pending_orders = db.query(models.Order).filter(
        models.Order.status == "pending"
    ).count()
    
    # Calculate total revenue (exclude cancelled orders)
    orders = db.query(models.Order).filter(
        models.Order.status != "cancelled"
    ).all()
    total_revenue = sum([order.total_price for order in orders]) if orders else 0
    
    # Get recent orders (last 5)
    recent_orders = db.query(models.Order).order_by(
        models.Order.created_at.desc()
    ).limit(5).all()
    
    return {
        "total_users": total_users,
        "total_products": total_products,
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "total_revenue": total_revenue,
        "recent_orders": [
            {
                "id": order.id,
                "total_price": order.total_price,
                "status": order.status,
                "created_at": order.created_at,
                "delivery_name": order.delivery_name
            }
            for order in recent_orders
        ]
    }

# ==================== USER MANAGEMENT ====================

@router.get("/users", response_model=List[schemas.UserOut])
def get_all_users(
    current_admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all users (Admin only)"""
    users = db.query(models.User).all()
    return users

@router.get("/users/{user_id}")
def get_user_details(
    user_id: int,
    current_admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get detailed user information (Admin only)"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user orders
    orders = db.query(models.Order).filter(models.Order.user_id == user_id).all()
    
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "is_admin": user.is_admin,
        "created_at": user.created_at,
        "last_login": user.last_login,
        "orders_count": len(orders),
        "total_spent": sum([order.total_price for order in orders if order.status != "cancelled"]),
        "orders": [
            {
                "id": order.id,
                "total_price": order.total_price,
                "status": order.status,
                "created_at": order.created_at
            }
            for order in orders
        ]
    }

@router.put("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    role_data: schemas.AdminUserUpdate,
    current_admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update user role (make admin or remove admin) (Admin only)"""
    # Prevent admin from modifying their own role
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot modify your own admin status"
        )
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_admin = role_data.is_admin
    db.commit()
    
    return {
        "message": f"User {user.email} admin status updated to {user.is_admin}",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "is_admin": user.is_admin
        }
    }

@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    current_admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete a user (Admin only)"""
    # Prevent admin from deleting their own account
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete your own account"
        )
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_email = user.email
    
    db.delete(user)
    db.commit()
    
    return {"message": f"User {user_email} deleted successfully"}

# ==================== PRODUCT MANAGEMENT ====================

@router.post("/products", response_model=schemas.ProductOut)
def create_product(
    product: schemas.ProductCreate,
    current_admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new product (Admin only)"""
    db_product = models.Product(
        name=product.name,
        price=product.price,
        description=product.description,
        category=product.category,
        image=product.image,
        stock=product.stock or 0,
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@router.put("/products/{product_id}", response_model=schemas.ProductOut)
def update_product(
    product_id: int,
    product: schemas.ProductCreate,
    current_admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update a product (Admin only)"""
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db_product.name = product.name
    db_product.price = product.price
    db_product.description = product.description
    db_product.category = product.category
    db_product.image = product.image
    db_product.stock = product.stock or 0
    
    db.commit()
    db.refresh(db_product)
    return db_product

@router.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    current_admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete a product (Admin only)"""
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db.delete(db_product)
    db.commit()
    return {"message": "Product deleted successfully"}

# ==================== ORDER MANAGEMENT ====================

@router.get("/orders")
def get_all_orders(
    current_admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all orders (Admin only)"""
    orders = db.query(models.Order).order_by(models.Order.created_at.desc()).all()
    
    return [
        {
            "id": order.id,
            "user_id": order.user_id,
            "total_price": order.total_price,
            "status": order.status,
            "delivery_name": order.delivery_name,
            "delivery_address": order.delivery_address,
            "delivery_phone": order.delivery_phone,
            "mpesa_code": order.mpesa_code,
            "created_at": order.created_at,
            "updated_at": order.updated_at,
            "items": [
                {
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price
                }
                for item in order.items
            ]
        }
        for order in orders
    ]

@router.put("/orders/{order_id}/status")
def update_order_status(
    order_id: int,
    status_update: schemas.OrderStatusUpdate,
    current_admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update order status (Admin only)"""
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order.status = status_update.status
    order.updated_at = datetime.utcnow()
    db.commit()
    
    return {
        "message": f"Order #{order_id} status updated to {status_update.status}",
        "order": {
            "id": order.id,
            "status": order.status,
            "updated_at": order.updated_at
        }
    }

# ==================== REVIEW MANAGEMENT ====================

@router.get("/reviews")
def get_all_reviews(
    current_admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all reviews (Admin only)"""
    reviews = db.query(models.Review).order_by(models.Review.created_at.desc()).all()
    return reviews

@router.delete("/reviews/{review_id}")
def delete_review(
    review_id: int,
    current_admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete a review (Admin only)"""
    review = db.query(models.Review).filter(models.Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    db.delete(review)
    db.commit()
    return {"message": "Review deleted successfully"}

# ==================== COMMUNITY POST MANAGEMENT ====================

@router.get("/community")
def get_all_community_posts(
    current_admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all community posts (Admin only)"""
    posts = db.query(models.CommunityPost).order_by(models.CommunityPost.created_at.desc()).all()
    return posts

@router.delete("/community/{post_id}")
def delete_community_post(
    post_id: int,
    current_admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete a community post (Admin only)"""
    post = db.query(models.CommunityPost).filter(models.CommunityPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    db.delete(post)
    db.commit()
    return {"message": "Post deleted successfully"}