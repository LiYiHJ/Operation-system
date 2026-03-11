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
        overview = service.overview()
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
        # TODO: 从数据库查询真实指标
        metrics = {
            'totalRevenue': 150000,
            'totalOrders': 1200,
            'avgOrderValue': 125,
            'profitMargin': 0.18,
        }
        return jsonify(metrics)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
