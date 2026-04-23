import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

class Settings:
    APP_NAME = os.getenv("APP_NAME", "App Empresarial")
    APP_ENV = os.getenv("APP_ENV", "production").lower()
    APP_DEBUG = os.getenv("APP_DEBUG", "false").lower() == "true"

    SECRET_KEY = os.getenv("SECRET_KEY", "cambia-esto-en-produccion")
    SESSION_SECRET = os.getenv("SESSION_SECRET", SECRET_KEY)

    DATABASE_URL = os.getenv("DATABASE_URL", "")
    if not DATABASE_URL:
        raise RuntimeError("Falta DATABASE_URL en el archivo .env")

    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASS = os.getenv("SMTP_PASS", "")
    SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)

    RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "100/minute")
    SESSION_HTTPS_ONLY = os.getenv("SESSION_HTTPS_ONLY", "true").lower() == "true"

    @property
    def is_production(self):
        return self.APP_ENV == "production"

settings = Settings()