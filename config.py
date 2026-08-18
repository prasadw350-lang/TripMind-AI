"""Central configuration. All secrets are read from environment variables."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-key")
    
    # Third-party keys (never exposed to the browser)
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "")
    UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY", "")
    OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")

    # Paths
    BASE_DIR = BASE_DIR
    DATA_FILE = BASE_DIR / "data" / "travel_data.csv"
    MODEL_DIR = BASE_DIR / "models"
    DB_PATH = BASE_DIR / "database" / "travel.db"
    DATABASE_URL = os.getenv("DATABASE_URL")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    JSON_SORT_KEYS = False


config = Config()
