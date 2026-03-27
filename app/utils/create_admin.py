# app/utils/create_admin.py
from sqlalchemy.orm import Session
from app import models
import bcrypt
import os
from datetime import datetime

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password[:72].encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def create_default_admin(db: Session):
    """Create default admin account if it doesn't exist"""
    
    # Get admin credentials from environment variables
    admin_email = os.getenv("ADMIN_EMAIL", "admin@riverrose.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "Admin@123")
    admin_name = os.getenv("ADMIN_NAME", "River Rose Admin")
    
    # Check if admin already exists
    existing_admin = db.query(models.User).filter(
        models.User.email == admin_email
    ).first()
    
    if existing_admin:
        # If admin exists but is not marked as admin, update it
        if not existing_admin.is_admin:
            existing_admin.is_admin = True
            existing_admin.name = admin_name
            db.commit()
            print(f"Updated existing user {admin_email} to admin role")
        else:
            print(f"Admin account already exists: {admin_email}")
        return
    
    # Create new admin account
    try:
        admin_user = models.User(
            name=admin_name,
            email=admin_email,
            password_hash=hash_password(admin_password),
            is_admin=True,
            created_at=datetime.utcnow(),
        )
        db.add(admin_user)
        db.commit()
        print(f"✅ Default admin account created successfully!")
        print(f"   Email: {admin_email}")
        print(f"   Password: {admin_password}")
        print("   Please change the password after first login!")
    except Exception as e:
        print(f"❌ Error creating admin account: {e}")
        db.rollback()