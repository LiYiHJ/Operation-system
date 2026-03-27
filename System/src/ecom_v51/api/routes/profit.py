"""
利润计算API路由
"""

from flask import Blueprint, jsonify, request
from ecom_v51.services import ProfitService

profit_bp = Blueprint('profit', __name__)


@profit_bp.route('/solve', methods=['POST'])
def solve():
    """
    利润求解
    前端调用: profitAPI.solve(data)
    """
    try:
        data = request.get_json()

        service = ProfitService()
        result = service.solve(
            mode=data.get('mode', 'current'),
            target_value=float(data.get('targetValue') or 0),
            sale_price=float(data.get('salePrice') or 0),
            list_price=float(data.get('listPrice') or 0),
            variable_rate_total=float(data.get('variableRateTotal') or 0),
            fixed_cost_total=float(data.get('fixedCostTotal') or 0),
            algorithm_profile=data.get('algorithmProfile', 'ozon_daily_profit'),
            layered_params=data.get('layeredParams'),
            scenarios=data.get('scenarios'),
        )

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@profit_bp.route('/simulate', methods=['POST'])
def simulate():
    """
    利润模拟
    """
    try:
        data = request.get_json()

        service = ProfitService()
        result = service.simulate_matrix(
            sale_price=float(data.get('salePrice') or 0),
            list_price=float(data.get('listPrice') or 0),
            variable_rate_total=float(data.get('variableRateTotal') or 0),
            fixed_cost_total=float(data.get('fixedCostTotal') or 0),
            algorithm_profile=data.get('algorithmProfile', 'ozon_daily_profit'),
            layered_params=data.get('layeredParams'),
            discount_ratios=data.get('discountRatios'),
            scenarios=data.get('scenarios'),
        )

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@profit_bp.route('/profiles', methods=['GET'])
def profiles():
    """获取可用利润算法 profile 列表"""
    try:
        service = ProfitService()
        return jsonify({'profiles': service.get_profiles(), 'param_layers': service.get_default_params()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@profit_bp.route('/snapshots', methods=['GET'])
def list_snapshots():
    """读取利润快照"""
    try:
        service = ProfitService()
        shop_id = int(request.args.get('shopId', 1))
        limit = int(request.args.get('limit', 20))
        return jsonify({'snapshots': service.list_snapshots(shop_id=shop_id, limit=limit)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@profit_bp.route('/snapshots', methods=['POST'])
def save_snapshot():
    """保存利润快照"""
    try:
        data = request.get_json() or {}
        service = ProfitService()
        result = service.save_snapshot(
            shop_id=int(data.get('shopId', 1)),
            snapshot_name=str(data.get('snapshotName', '未命名快照')),
            algorithm_profile=str(data.get('algorithmProfile', 'ozon_daily_profit')),
            payload=data.get('payload') or {},
            result=data.get('result') or {},
            operator=str(data.get('operator', 'profit_ui')),
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@profit_bp.route('/templates', methods=['GET'])
def list_templates():
    """读取利润模板"""
    try:
        service = ProfitService()
        shop_id = int(request.args.get('shopId', 1))
        limit = int(request.args.get('limit', 20))
        return jsonify({'templates': service.list_templates(shop_id=shop_id, limit=limit)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@profit_bp.route('/templates', methods=['POST'])
def save_template():
    """保存利润模板"""
    try:
        data = request.get_json() or {}
        service = ProfitService()
        result = service.save_template(
            shop_id=int(data.get('shopId', 1)),
            template_name=str(data.get('templateName', '未命名模板')),
            algorithm_profile=str(data.get('algorithmProfile', 'ozon_daily_profit')),
            layered_params=data.get('layeredParams') or {},
            scenarios=data.get('scenarios') or [],
            operator=str(data.get('operator', 'profit_ui')),
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
