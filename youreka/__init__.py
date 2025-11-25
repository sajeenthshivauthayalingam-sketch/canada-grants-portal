from flask import Flask, request
from flask_babel import lazy_gettext as _
from .extensions import db, babel
from .models import Region
from .grants import bp as grants_bp
from .email_utils import send_deadline_reminders
from .scraping.tasks import run_scrape
import config as app_config

def create_app(config_name="DevConfig"):
    app = Flask(__name__, instance_relative_config=True)

    # Config
    app.config.from_object(getattr(app_config, config_name))
    app.config.from_pyfile("config.py", silent=True)

    # Locale selector function for Babel
    def select_locale():
        # ?lang=en or ?lang=fr
        lang = request.args.get("lang")
        if lang in app.config.get("LANGUAGES", []):
            return lang
        return app.config.get("BABEL_DEFAULT_LOCALE", "en")

    # Extensions
    db.init_app(app)
    babel.init_app(app, locale_selector=select_locale)

    # Blueprints
    app.register_blueprint(grants_bp, url_prefix="/")

    # CLI commands
    register_cli(app)

    # Ensure DB exists + seed regions
    with app.app_context():
        db.create_all()
        seed_regions_if_empty()

    return app


def seed_regions_if_empty():
    if Region.query.count() > 0:
        return

    regions = [
        {"name_en": "National", "name_fr": "National", "province": None, "city": None},
        {"name_en": "Vancouver", "name_fr": "Vancouver", "province": "BC", "city": "Vancouver"},
        {"name_en": "Montreal", "name_fr": "Montréal", "province": "QC", "city": "Montreal"},
        {"name_en": "Calgary", "name_fr": "Calgary", "province": "AB", "city": "Calgary"},
        {"name_en": "Edmonton", "name_fr": "Edmonton", "province": "AB", "city": "Edmonton"},
        {"name_en": "Kingston", "name_fr": "Kingston", "province": "ON", "city": "Kingston"},
        {"name_en": "Toronto", "name_fr": "Toronto", "province": "ON", "city": "Toronto"},
        {"name_en": "Windsor", "name_fr": "Windsor", "province": "ON", "city": "Windsor"},
        {"name_en": "French Expansion", "name_fr": "Expansion francophone", "province": None, "city": None},
    ]

    from .extensions import db as _db

    region_objs = [Region(**r) for r in regions]
    _db.session.add_all(region_objs)
    _db.session.commit()


def register_cli(app: Flask):
    @app.cli.command("send-reminders")
    def send_reminders_cmd():
        """Send upcoming deadline email reminders (stub)."""
        with app.app_context():
            send_deadline_reminders()

    @app.cli.command("scrape-grants")
    def scrape_grants_cmd():
        """Run scraping task to import new grants."""
        with app.app_context():
            run_scrape()
