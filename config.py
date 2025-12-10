import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


# Common settings for all environments
class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")

    # SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # i18n / Babel
    LANGUAGES = ["en", "fr"]
    BABEL_DEFAULT_LOCALE = "en"
    BABEL_DEFAULT_TIMEZONE = "UTC"
    BABEL_TRANSLATION_DIRECTORIES = "./translations"

    # Email reminder settings (stub)
    REMINDER_DAYS = 7  # look ahead this many days for reminders

    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)


# Local development: use SQLite file
class DevConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "grants.db")


# Production (Render): use DATABASE_URL (Postgres)
class ProdConfig(BaseConfig):
    db_url = os.environ.get("DATABASE_URL")

    # Handle old-style postgres:// URLs if Render gives them
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = db_url or (
        "sqlite:///" + os.path.join(BASE_DIR, "grants.db")
    )
