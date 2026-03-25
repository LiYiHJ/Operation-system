from flask import Blueprint

from .actions import actions_bp
from .batches import batches_bp
from .economics import economics_bp
from .import_ops import import_bp_v1
from .jobs import jobs_bp
from .objects import objects_bp
from .registry import registry_bp


v1_bp = Blueprint("api_v1", __name__)
v1_bp.register_blueprint(registry_bp, url_prefix="/registry")
v1_bp.register_blueprint(import_bp_v1, url_prefix="/import")
v1_bp.register_blueprint(batches_bp, url_prefix="/batches")
v1_bp.register_blueprint(jobs_bp, url_prefix="/jobs")
v1_bp.register_blueprint(objects_bp, url_prefix="/objects")
v1_bp.register_blueprint(economics_bp, url_prefix="/economics")
v1_bp.register_blueprint(actions_bp, url_prefix="/actions")
