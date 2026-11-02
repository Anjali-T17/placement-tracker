"""Application settings. Values come from environment variables / the .env file."""
import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "5001"))  # 5001 because macOS uses 5000 for AirPlay
    CORS_ORIGINS = [
        o.strip()
        for o in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5500,http://127.0.0.1:5500,http://localhost:5000,http://127.0.0.1:5000,http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000,http://127.0.0.1:3000,http://localhost:5001,http://127.0.0.1:5001,null",
        ).split(",")
        if o.strip()
    ]

    # Database configuration
    DB_TYPE = os.getenv("DB_TYPE", "sqlite").lower()
    DATABASE_PATH = os.getenv("DATABASE_PATH", "placement.db")

    # Optional MySQL configuration (if DB_TYPE=mysql)
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "admin")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
    DB_NAME = os.getenv("DB_NAME", "placement")
