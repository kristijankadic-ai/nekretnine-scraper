import logging

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from app.models import db
from config import Config

logger = logging.getLogger(__name__)


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    with app.app_context():
        db.create_all()

    from app.routes import bp

    app.register_blueprint(bp)

    return app
