from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:postgres123@localhost:5432/river_rose"
    SECRET_KEY: str = "supersecretkey"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    FRONTEND_URL: str = "https://river-rose.vercel.app/"

    MAIL_HOST: str = "smtp.gmail.com"
    MAIL_PORT: int = 587
    MAIL_USERNAME: str = "you@gmail.com"
    MAIL_PASSWORD: str = "your-app-password"
    MAIL_FROM: str = "you@gmail.com"

    ADMIN_EMAIL: str = "25@gmail.com"  # ← single admin account

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()