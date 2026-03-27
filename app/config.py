# app/config.py
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:guirassy@localhost:5432/river_rose"
    
    # JWT Settings
    SECRET_KEY: str = "riverrose2025secretkey"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # Admin Credentials
    ADMIN_EMAIL: str = "admin@riverrose.com"
    ADMIN_PASSWORD: str = "Admin@123"
    ADMIN_NAME: str = "River Rose Admin"
    
    # Frontend URL
    FRONTEND_URL: str = "https://river-rose.vercel.app/"
    
    # Email Settings (optional for now)
    MAIL_HOST: str = "smtp.gmail.com"
    MAIL_PORT: int = 587
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = ""
    
    # App Settings
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()