import logging

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect

from app.models import db
from config import Config

logger = logging.getLogger(__name__)


def _migrate_buyer_leads_schema(app):
    """One-off fixup: buyer_leads was first shipped with a single 'name'
    column; it's now first_name/last_name. Only ever held test data, so
    drop and let create_all rebuild it with the current schema."""
    inspector = inspect(db.engine)
    if "buyer_leads" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("buyer_leads")}
    if "name" in columns and "first_name" not in columns:
        logger.info("Migrating buyer_leads table to first_name/last_name schema")
        db.session.execute(db.text("DROP TABLE buyer_leads"))
        db.session.commit()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    with app.app_context():
        _migrate_buyer_leads_schema(app)
        db.create_all()

    from app.routes import bp

    app.register_blueprint(bp)

    return app
