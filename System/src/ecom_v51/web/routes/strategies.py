from __future__ import annotations

from flask import Blueprint, render_template, request

from ecom_v51.services import StrategyTaskService

strategies_bp = Blueprint("strategies", __name__)
service = StrategyTaskService()


@strategies_bp.get("/strategies")
def strategies_index() -> str:
    priority = request.args.get("priority", "")
    status = request.args.get("status", "")
    rows = service.list_tasks(priority=priority, status=status)
    return render_template(
        "strategies/index.html",
        rows=rows,
        priority=priority,
        status=status,
    )
