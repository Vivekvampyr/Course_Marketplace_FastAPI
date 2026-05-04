from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str

    RAZORPAY_KEY_ID: str
    RAZORPAY_KEY_SECRET: str

    GEMINI_API_KEY: str
    UPLOAD_DIR: str = "uploads"

    class Config:
        env_file = ".env"

settings = Settings()