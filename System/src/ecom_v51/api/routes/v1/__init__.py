from flask import Blueprint

from .batches import batches_bp
from .import_ops import import_bp_v1
from .jobs import jobs_bp
from .registry import registry_bp


v1_bp = Blueprint("api_v1", __name__)
v1_bp.register_blueprint(registry_bp, url_prefix="/registry")
v1_bp.register_blueprint(import_bp_v1, url_prefix="/import")
v1_bp.register_blueprint(batches_bp, url_prefix="/batches")
v1_bp.register_blueprint(jobs_bp, url_prefix="/jobs")
