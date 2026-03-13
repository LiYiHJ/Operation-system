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


@dashboard_bp.route('/top-skus', methods=['GET'])
def get_top_skus():
    """兼容旧路径：返回Top SKU"""
    try:
        service = DashboardService()
        days = int(request.args.get('days', 7))
        limit = int(request.args.get('limit', 5))
        overview = service.overview(days=days)
        rows = (overview.get('topSkus') or [])[:max(limit, 1)]
        return jsonify({'data': rows})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/alerts', methods=['GET'])
def get_alerts():
    """兼容旧路径：返回告警"""
    try:
        service = DashboardService()
        days = int(request.args.get('days', 7))
        limit = int(request.args.get('limit', 8))
        overview = service.overview(days=days)
        rows = (overview.get('alerts') or [])[:max(limit, 1)]
        summary = {
            'P0': len([x for x in rows if x.get('type') == 'P0']),
            'P1': len([x for x in rows if x.get('type') == 'P1']),
            'P2': len([x for x in rows if x.get('type') == 'P2']),
            'P3': len([x for x in rows if x.get('type') == 'P3']),
        }
        return jsonify({'data': rows, 'summary': summary})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/trends', methods=['GET'])
def get_trends():
    """兼容旧路径：返回趋势"""
    try:
        service = DashboardService()
        days = int(request.args.get('days', 7))
        overview = service.overview(days=days)
        return jsonify(overview.get('trends') or {'dates': [], 'revenue': [], 'orders': []})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/shop-health', methods=['GET'])
def get_shop_health():
    """兼容旧路径：返回店铺健康度（基于overview派生）"""
    try:
        service = DashboardService()
        days = int(request.args.get('days', 7))
        overview = service.overview(days=days)
        health = [{
            'shopId': 1,
            'shopName': 'Default Shop',
            'rating': float(overview.get('avgRating') or 0),
            'delayRate': 0.0,
            'priceCompetitiveness': {'green': max(int(overview.get('totalProducts') or 0) - int(len(overview.get('alerts') or [])), 0), 'red': int(len(overview.get('alerts') or []))},
            'totalOrders': int(overview.get('totalOrders') or 0),
            'totalProducts': int(overview.get('totalProducts') or 0),
        }]
        return jsonify({'data': health})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
