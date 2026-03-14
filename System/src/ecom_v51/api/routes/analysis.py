"""
专题分析与动作回流 API
"""

from flask import Blueprint, jsonify, request

from ecom_v51.services.analysis_service import AnalysisService

analysis_bp = Blueprint('analysis', __name__)


@analysis_bp.route('/abc', methods=['GET'])
def abc_analysis():
    try:
        service = AnalysisService(
            shop_id=int(request.args.get('shopId', 1)),
            days=int(request.args.get('days', 7)),
        )
        return jsonify(service.abc_analysis())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@analysis_bp.route('/price-cockpit', methods=['GET'])
def price_cockpit():
    try:
        service = AnalysisService(
            shop_id=int(request.args.get('shopId', 1)),
            days=int(request.args.get('days', 7)),
        )
        return jsonify(service.price_cockpit(view=request.args.get('view', 'daily')))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@analysis_bp.route('/price', methods=['GET'])
def price_compat():
    """兼容旧路径：/analysis/price -> /analysis/price-cockpit"""
    try:
        service = AnalysisService(
            shop_id=int(request.args.get('shopId', request.args.get('shop_id', 1))),
            days=int(request.args.get('days', 7)),
        )
        return jsonify(service.price_cockpit(view=request.args.get('view', 'daily')))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@analysis_bp.route('/funnel', methods=['GET'])
def funnel_analysis():
    try:
        service = AnalysisService(
            shop_id=int(request.args.get('shopId', 1)),
            days=int(request.args.get('days', 7)),
        )
        return jsonify(service.funnel_analysis())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@analysis_bp.route('/inventory', methods=['GET'])
def inventory_analysis():
    try:
        service = AnalysisService(
            shop_id=int(request.args.get('shopId', 1)),
            days=int(request.args.get('days', 7)),
        )
        return jsonify(service.inventory_analysis())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@analysis_bp.route('/ads', methods=['GET'])
def ads_analysis():
    try:
        service = AnalysisService(
            shop_id=int(request.args.get('shopId', 1)),
            days=int(request.args.get('days', 7)),
        )
        return jsonify(service.ads_analysis())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@analysis_bp.route('/action-to-strategy', methods=['POST'])
def action_to_strategy():
    try:
        payload = request.get_json() or {}
        service = AnalysisService(
            shop_id=int(payload.get('shopId', 1)),
            days=int(payload.get('days', 7)),
        )
        result = service.push_action_to_strategy(
            source_page=str(payload.get('sourcePage', 'analysis')),
            sku=str(payload.get('sku', '')),
            issue_summary=str(payload.get('issueSummary', '专题分析建议动作')),
            recommended_action=str(payload.get('recommendedAction', '请在策略清单确认后执行')),
            strategy_type=str(payload.get('strategyType', 'pricing')),
            priority=str(payload.get('priority', 'P1')),
            operator=str(payload.get('operator', 'analysis_ui')),
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500