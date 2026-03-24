import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./panama_booking.db")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "panama-canal-secret-key")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION_MINUTES: int = int(os.getenv("JWT_EXPIRATION_MINUTES", "480"))
    CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000"]

settings = Settings()
