from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request

from ecom_v51.services import ProfitService

profit_bp = Blueprint("profit", __name__)
service = ProfitService()


@profit_bp.get("/profit")
def profit_index() -> str:
    data = service.dashboard()
    return render_template("profit/index.html", data=data)


@profit_bp.post("/profit/solve")
def profit_solve() -> tuple[object, int] | str:
    is_api = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    mode = request.form.get("mode", "target_profit")
    target_value = float(request.form.get("target_value", "10"))
    sale_price = float(request.form.get("sale_price", "119"))
    list_price = float(request.form.get("list_price", "129"))
    variable_rate_total = float(request.form.get("variable_rate_total", "0.31"))
    fixed_cost_total = float(request.form.get("fixed_cost_total", "72"))

    result = service.solve(
        mode=mode,
        target_value=target_value,
        sale_price=sale_price,
        list_price=list_price,
        variable_rate_total=variable_rate_total,
        fixed_cost_total=fixed_cost_total,
    )

    if is_api:
        return jsonify(result), 200
    return render_template("profit/index.html", data=result)
