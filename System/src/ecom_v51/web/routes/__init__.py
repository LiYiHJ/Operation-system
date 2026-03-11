from flask import Flask

from .core import core_bp
from .imports import imports_bp
from .products import products_bp
from .profit import profit_bp
from .reports import reports_bp
from .settings import settings_bp
from .strategies import strategies_bp


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(core_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(profit_bp)
    app.register_blueprint(strategies_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(imports_bp)
    app.register_blueprint(settings_bp)


__all__ = ["register_blueprints"]
