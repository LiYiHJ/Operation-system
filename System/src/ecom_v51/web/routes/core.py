from __future__ import annotations

from flask import Blueprint, jsonify, render_template

from ecom_v51.services import DashboardService

core_bp = Blueprint("core", __name__)


@core_bp.get("/")
def dashboard() -> str:
    overview = DashboardService().overview()
    return render_template("dashboard.html", overview=overview)


@core_bp.get("/health")
def health() -> tuple[object, int]:
    return jsonify({"status": "ok", "service": "ecom_v51_web"}), 200
