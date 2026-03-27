# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings
import bcrypt
from datetime import datetime

# Database engine configuration
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,      # tests connection before using it
    pool_recycle=300,        # recycles connections every 5 mins
    pool_size=5,
    max_overflow=10,
    connect_args={
        "connect_timeout": 10,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()        # commit if everything went fine
    except Exception:
        db.rollback()      # roll back cleanly on any error
        raise              # re-raise so FastAPI returns the correct HTTP error
    finally:
        db.close()

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password[:72].encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def create_default_admin():
    """Create default admin account if it doesn't exist"""
    from app import models  # Import here to avoid circular imports
    
    db = SessionLocal()
    try:
        # Get admin credentials from settings
        admin_email = settings.ADMIN_EMAIL
        admin_password = settings.ADMIN_PASSWORD
        admin_name = settings.ADMIN_NAME
        
        # Check if admin already exists
        existing_admin = db.query(models.User).filter(
            models.User.email == admin_email
        ).first()
        
        if existing_admin:
            # If user exists but is not admin, upgrade to admin
            if not existing_admin.is_admin:
                existing_admin.is_admin = True
                existing_admin.name = admin_name
                db.commit()
                print(f"✅ Upgraded existing user {admin_email} to admin role")
            else:
                print(f"✓ Admin account already exists: {admin_email}")
            return
        
        # Create new admin account
        admin_user = models.User(
            name=admin_name,
            email=admin_email,
            password_hash=hash_password(admin_password),
            is_admin=True,
            created_at=datetime.utcnow(),
        )
        db.add(admin_user)
        db.commit()
        
        print("=" * 60)
        print("✅ DEFAULT ADMIN ACCOUNT CREATED SUCCESSFULLY!")
        print(f"   Email: {admin_email}")
        print(f"   Password: {admin_password}")
        print(f"   Name: {admin_name}")
        print("   ⚠️  IMPORTANT: Please change this password after first login!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error creating admin account: {e}")
        db.rollback()
    finally:
        db.close()

def init_db():
    """Initialize database - create tables and default admin"""
    from app import models  # Import here to avoid circular imports
    
    print("📦 Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")
    
    print("👤 Creating default admin account...")
    create_default_admin()