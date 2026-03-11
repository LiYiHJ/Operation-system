from __future__ import annotations

from flask import Blueprint, render_template

from ecom_v51.services import SettingsService

settings_bp = Blueprint("settings", __name__)
service = SettingsService()


@settings_bp.get("/settings")
def settings_index() -> str:
    info = service.get_overview()
    return render_template("settings/index.html", info=info)
