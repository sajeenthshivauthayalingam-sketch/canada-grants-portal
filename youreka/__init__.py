from flask import Flask, request, session, g
from .extensions import db, babel
from .models import Region
from .grants import bp as grants_bp
from .email_utils import send_deadline_reminders
from .scraping.tasks import run_scrape
import config as app_config
from youreka.scraping.otf import scrape_otf
from flask_babel import gettext as _, gettext, ngettext
from .scraping.gov import scrape_ontario

def create_app(config_name="DevConfig"):
    import os
    # ---------------------------------------------------------
    # DO NOT OVERRIDE root_path !!! 
    # Flask will automatically use the "youreka/" directory
    # ---------------------------------------------------------
    app = Flask(__name__, instance_relative_config=True)

    # ---------------------------------------------------------
    # Load config
    # ---------------------------------------------------------
    app.config.from_object(getattr(app_config, config_name))
    app.config.from_pyfile("config.py", silent=True)

    app.config["BABEL_TRANSLATION_DIRECTORIES"] = os.path.join(
        os.path.dirname(__file__),
        "..",
        "translations"
    )


    # ---------------------------------------------------------
    # Locale selector
    # ---------------------------------------------------------
    def select_locale():
        # 1. URL override
        lang = request.args.get("lang")
        if lang in app.config["LANGUAGES"]:
            session["lang"] = lang
            session.permanent = True
            return lang

        # 2. If visiting "/" with NO lang= param → reset to English
        if "lang" not in request.args:
            session["lang"] = "en"
            return "en"

        # 3. Session fallback
        lang = session.get("lang")
        if lang in app.config["LANGUAGES"]:
            return lang

        # 4. Default
        return app.config["BABEL_DEFAULT_LOCALE"]


    # ---------------------------------------------------------
    # Initialize DB + Babel
    # ---------------------------------------------------------
    db.init_app(app)
    babel.init_app(app, locale_selector=select_locale)

    # DO NOT add jinja2.ext.i18n — Flask-Babel already handles it

    @app.before_request
    def before_request():
        g.lang = select_locale()

    @app.context_processor
    def inject_lang():
        return {"current_lang": session.get("lang", "en")}

    # ---------------------------------------------------------
    # Blueprints
    # ---------------------------------------------------------
    app.register_blueprint(grants_bp, url_prefix="/")

    # ---------------------------------------------------------
    # DB setup
    # ---------------------------------------------------------
    with app.app_context():
        db.create_all()
        seed_regions_if_empty()

    register_cli(app)
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
    db.session.add_all(Region(**r) for r in regions)
    db.session.commit()


def register_cli(app):
    @app.cli.command("send-reminders")
    def send_reminders_cmd():
        with app.app_context():
            send_deadline_reminders()

    @app.cli.command("scrape-grants")
    def scrape_grants_cmd():
        with app.app_context():
            run_scrape()

    @app.cli.command("scrape-otf")
    def scrape_otf_cmd():
        scrape_otf()

    @app.cli.command("scrape-ontario")
    def scrape_ontario_cmd():
        scrape_ontario()