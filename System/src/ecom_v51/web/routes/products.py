from __future__ import annotations

from flask import Blueprint, render_template, request

from ecom_v51.services import ProductService

products_bp = Blueprint("products", __name__)
service = ProductService()


@products_bp.get("/products")
def product_list() -> str:
    q = request.args.get("q", "")
    rows = service.list_products(q)
    return render_template("products/list.html", rows=rows, q=q)


@products_bp.get("/products/<sku>")
def product_detail(sku: str) -> str:
    report = service.get_war_room(sku)
    return render_template("products/detail.html", sku=sku, report=report)
