"""
策略任务API路由
"""

from flask import Blueprint, jsonify, request
from ecom_v51.services import StrategyTaskService

strategy_bp = Blueprint('strategy', __name__)


@strategy_bp.route('/list', methods=['GET'])
def list_tasks():
    """
    获取策略任务列表
    前端调用: strategyAPI.getList()
    """
    try:
        priority = request.args.get('priority', '')
        status = request.args.get('status', '')
        
        service = StrategyTaskService()
        tasks = service.list_tasks(priority=priority, status=status)
        
        return jsonify(tasks)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@strategy_bp.route('/analyze', methods=['POST'])
def analyze():
    """
    策略分析
    前端调用: strategyAPI.analyze(data, shopName)
    """
    try:
        data = request.get_json()
        
        service = StrategyTaskService()
        # TODO: 批量分析
        
        return jsonify({'tasks': []})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@strategy_bp.route('/quick-summary', methods=['POST'])
def quick_summary():
    """
    快速摘要
    前端调用: strategyAPI.getQuickSummary(data)
    """
    try:
        data = request.get_json()
        
        service = StrategyTaskService()
        # TODO: 生成快速摘要
        
        return jsonify({'summary': {}})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@strategy_bp.route('/decision/preview', methods=['GET'])
def decision_preview():
    """组合决策预演"""
    try:
        scope = request.args.get('scope', 'all')
        service = StrategyTaskService()
        return jsonify(service.decision_preview(scope=scope))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@strategy_bp.route('/decision/confirm', methods=['POST'])
def decision_confirm():
    """人工确认并回写策略任务"""
    try:
        data = request.get_json() or {}
        task_ids = data.get('taskIds') or []
        operator = data.get('operator', 'planner')
        service = StrategyTaskService()
        return jsonify(service.decision_confirm(selected_task_ids=task_ids, operator=operator))
    except Exception as e:
        return jsonify({'error': str(e)}), 500
