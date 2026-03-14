"""广告兼容 API 路由（收口到 analysis/ads）"""

from flask import Blueprint, jsonify, request

from ecom_v51.services.analysis_service import AnalysisService

ads_bp = Blueprint('ads', __name__)


@ads_bp.route('/campaigns', methods=['GET'])
def campaigns():
    """兼容旧前端路径，返回广告分析行作为campaign列表"""
    try:
        service = AnalysisService(
            shop_id=int(request.args.get('shop_id', request.args.get('shopId', 1))),
            days=int(request.args.get('days', 7)),
        )
        payload = service.ads_analysis()
        return jsonify({'data': payload.get('rows', [])})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ads_bp.route('/campaign/<campaign_id>', methods=['PUT'])
def update_campaign(campaign_id: str):
    """兼容旧前端路径：当前仅回显请求，提示已迁移到 analysis/ads + strategy"""
    try:
        data = request.get_json() or {}
        return jsonify({
            'campaignId': campaign_id,
            'status': 'accepted',
            'message': 'ads旧路径兼容中，建议改用analysis/ads与strategy闭环',
            'changes': data,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500