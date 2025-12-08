import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR, "grants.db"),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Babel / i18n
    LANGUAGES = ["en", "fr"]
    BABEL_DEFAULT_LOCALE = "en"
    BABEL_DEFAULT_TIMEZONE = "UTC"
    BABEL_TRANSLATION_DIRECTORIES = "./translations"

    # Email reminder settings (stub – plug real SMTP later)
    REMINDER_DAYS = 7  # look ahead this many days for reminders

    # For session lifetime / CSRF etc if needed later
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)


class DevConfig(Config):
    DEBUG = True


class ProdConfig(Config):
    DEBUG = False
