"""
Dashboard API路由
"""

from flask import Blueprint, jsonify, request
from ecom_v51.services import DashboardService

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/overview', methods=['GET'])
def get_overview():
    """
    获取Dashboard概览数据
    前端调用: dashboardAPI.getOverview()
    """
    try:
        service = DashboardService()
        days = int(request.args.get('days', 7))
        overview = service.overview(days=days)
        return jsonify(overview)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/metrics', methods=['GET'])
def get_metrics():
    """
    获取关键指标
    """
    try:
        service = DashboardService()
        days = int(request.args.get('days', 7))
        overview = service.overview(days=days)
        metrics = {
            'totalRevenue': overview['totalRevenue'],
            'totalOrders': overview['totalOrders'],
            'avgOrderValue': overview['avgOrderValue'],
            'profitMargin': overview['profitMargin'],
        }
        return jsonify(metrics)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
