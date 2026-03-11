from __future__ import annotations

from flask import Blueprint, render_template, request

from ecom_v51.services import ReportService

reports_bp = Blueprint("reports", __name__)
service = ReportService()


@reports_bp.get("/reports")
def reports_index() -> str:
    report_type = request.args.get("type", "")
    rows = service.list_reports(report_type)
    return render_template("reports/index.html", rows=rows, report_type=report_type)


@reports_bp.get("/reports/<int:report_id>")
def report_detail(report_id: int) -> str:
    report = service.get_report(report_id)
    return render_template("reports/detail.html", report=report)
