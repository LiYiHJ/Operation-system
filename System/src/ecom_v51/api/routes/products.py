"""
产品API路由
"""

from flask import Blueprint, jsonify, request
from ecom_v51.services import ProductService

products_bp = Blueprint('products', __name__)


@products_bp.route('/list', methods=['GET'])
def list_products():
    """
    获取产品列表
    """
    try:
        query = request.args.get('q', '')
        service = ProductService()
        products = service.list_products(query=query)
        return jsonify(products)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@products_bp.route('/<sku>/war-room', methods=['GET'])
def get_war_room(sku: str):
    """
    获取SKU作战室报告
    前端调用: warRoomAPI.getSkuReport(sku)
    """
    try:
        service = ProductService()
        report = service.get_war_room(sku)
        return jsonify(report)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
