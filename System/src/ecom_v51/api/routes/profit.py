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
            mode=data['mode'],
            target_value=data['targetValue'],
            sale_price=data['salePrice'],
            list_price=data['listPrice'],
            variable_rate_total=data['variableRateTotal'],
            fixed_cost_total=data['fixedCostTotal'],
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
        # TODO: 实现利润模拟
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
