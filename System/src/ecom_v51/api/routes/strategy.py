"""策略任务 API 路由"""

from flask import Blueprint, jsonify, request

from ecom_v51.services import StrategyTaskService
from ecom_v51.db.session import get_session
from ecom_v51.db.models import StrategyTask, DimSku


strategy_bp = Blueprint('strategy', __name__)


@strategy_bp.route('/list', methods=['GET'])
def list_tasks():
    """获取策略任务列表"""
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
    """策略分析"""
    try:
        _data = request.get_json()
        _service = StrategyTaskService()
        return jsonify({'tasks': []})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@strategy_bp.route('/quick-summary', methods=['POST'])
def quick_summary():
    """快速摘要"""
    try:
        _data = request.get_json()
        _service = StrategyTaskService()
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


@strategy_bp.route('/generate/<sku>', methods=['POST'])
def generate_compat(sku: str):
    """兼容旧路径：按 SKU 快速创建策略任务"""
    try:
        payload = request.get_json() or {}
        issue_summary = f"兼容生成策略: {sku}"
        action = str((payload.get('snapshot') or {}).get('recommendedAction') or '请进入决策页确认执行')
        with get_session() as session:
            shop_id = int(payload.get('shopId') or 1)
            sku_row = session.query(DimSku).filter(DimSku.shop_id == shop_id, DimSku.sku == sku).one_or_none()
            task = StrategyTask(
                shop_id=shop_id,
                sku_id=sku_row.id if sku_row else None,
                strategy_type='pricing',
                priority='P1',
                trigger_rule='compat:generate',
                issue_summary=issue_summary,
                recommended_action=action,
                risk_note=f'{{"sourcePage":"compat_generate","sourceReason":"{issue_summary}"}}',
                observation_metrics_json=['compat_generate'],
                status='pending',
                owner='compat_api',
            )
            session.add(task)
            session.flush()
            return jsonify({'tasks': [{'id': task.id, 'sku': sku, 'status': task.status, 'source': 'compat_generate'}]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@strategy_bp.route('/batch', methods=['POST'])
def batch_compat():
    """兼容旧路径：返回当前待处理规模"""
    try:
        service = StrategyTaskService()
        rows = service.list_tasks(status='pending').get('tasks', [])
        task_ids = [int(x.get('id')) for x in rows if str(x.get('id')).isdigit()]
        return jsonify({
            'batchId': f'compat-{len(rows)}',
            'totalTasks': len(rows),
            'summary': {'pending': len(rows)},
            'taskIds': task_ids[:200],
            'compat': True,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@strategy_bp.route('/decision', methods=['POST'])
def decision_compat():
    """兼容旧路径：转发到 decision_preview"""
    try:
        service = StrategyTaskService()
        payload = service.decision_preview(scope='all')
        payload['compat'] = True
        return jsonify(payload)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@strategy_bp.route('/task/<int:task_id>/status', methods=['PUT'])
def update_task_status(task_id: int):
    """兼容旧路径：更新策略任务状态"""
    try:
        data = request.get_json() or {}
        status = str(data.get('status', 'pending'))
        assigned_to = data.get('assignedTo')
        with get_session() as session:
            task = session.query(StrategyTask).filter(StrategyTask.id == task_id).one_or_none()
            if not task:
                return jsonify({'error': 'task not found'}), 404
            task.status = status
            if assigned_to:
                task.owner = str(assigned_to)
            session.flush()
            return jsonify({
                'taskId': task.id,
                'status': task.status,
                'updatedAt': task.updated_at.isoformat() if task.updated_at else None,
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
