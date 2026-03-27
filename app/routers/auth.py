# app/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import bcrypt
from jose import jwt, JWTError
from datetime import datetime, timedelta
from app.database import get_db
from app import models, schemas
from app.config import settings

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password[:72].encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain[:72].encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def get_current_user_from_token(token: str, db: Session) -> models.User:
    """Same as get_current_user but accepts a raw token string — used for optional auth."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    return get_current_user_from_token(token=token, db=db)


# ==================== ADD THESE FUNCTIONS ====================

def get_current_admin_user(current_user: models.User = Depends(get_current_user)):
    """Dependency to ensure current user is admin"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


# ==================== UPDATE EXISTING ENDPOINTS ====================

@router.post("/signup", response_model=schemas.Token)
def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if user.password != user.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")
    if db.query(models.User).filter(models.User.email == user.email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    
    # CREATE REGULAR USER (is_admin = False by default)
    db_user = models.User(
        name=user.name,
        email=user.email,
        password_hash=hash_password(user.password),
        is_admin=False,  # ADD THIS - regular users cannot be admin
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    token = create_access_token({"sub": str(db_user.id)})
    return {"access_token": token}


@router.post("/login", response_model=schemas.Token)
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    if not db_user.password_hash:
        raise HTTPException(
            status_code=403,
            detail="Please set your password first. Check your email for the setup link.",
        )
    if not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    
    # UPDATE LAST LOGIN (ADD THIS)
    db_user.last_login = datetime.utcnow()
    db.commit()
    
    token = create_access_token({"sub": str(db_user.id)})
    return {"access_token": token}


@router.post("/set-password", response_model=schemas.Token)
def set_password(payload: schemas.SetPassword, db: Session = Depends(get_db)):
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    user = db.query(models.User).filter(
        models.User.set_password_token == payload.token
    ).first()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired link. Please contact support.")

    if user.set_password_token_exp < datetime.utcnow():
        raise HTTPException(status_code=400, detail="This link has expired. Please place a new order or contact support.")

    user.password_hash = hash_password(payload.password)
    user.set_password_token = None
    user.set_password_token_exp = None
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token}


@router.get("/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(get_current_user)):
    """Get current user info (includes is_admin flag)"""
    return current_user


# ==================== ADD NEW ADMIN ENDPOINTS ====================

@router.get("/admin/check")
def check_admin(current_user: models.User = Depends(get_current_user)):
    """Check if current user is admin"""
    return {"isAdmin": current_user.is_admin}


@router.get("/admin/users", response_model=list[schemas.UserOut])
def get_all_users(
    current_admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """ADMIN ONLY: Get all users"""
    users = db.query(models.User).all()
    return users


@router.put("/admin/users/{user_id}/role")
def update_user_role(
    user_id: int,
    role_data: schemas.AdminUserUpdate,
    current_admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """ADMIN ONLY: Update user role (make admin or remove admin)"""
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


@router.delete("/admin/users/{user_id}")
def delete_user(
    user_id: int,
    current_admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """ADMIN ONLY: Delete a user"""
    # Prevent admin from deleting their own account
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete your own account"
        )
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Store user info for response
    user_email = user.email
    
    db.delete(user)
    db.commit()
    
    return {"message": f"User {user_email} deleted successfully"}


@router.get("/admin/dashboard-stats")
def get_dashboard_stats(
    current_admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """ADMIN ONLY: Get dashboard statistics"""
    from app import models
    
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
                "created_at": order.created_at
            }
            for order in recent_orders
        ]
    }


@router.get("/admin/user/{user_id}")
def get_user_details(
    user_id: int,
    current_admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """ADMIN ONLY: Get detailed user information"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user orders
    orders = db.query(models.Order).filter(
        models.Order.user_id == user_id
    ).all()
    
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