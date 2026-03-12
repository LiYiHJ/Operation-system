from __future__ import annotations

from flask import Blueprint, jsonify, request

from ecom_v51.services.integration_service import IntegrationService

integration_bp = Blueprint('integration', __name__)


@integration_bp.route('/domains', methods=['GET'])
def list_domains():
    svc = IntegrationService(shop_id=int(request.args.get('shopId', 1)))
    return jsonify({'rows': svc.list_domain_scopes()})


@integration_bp.route('/data-source', methods=['GET'])
def get_data_source():
    provider = request.args.get('provider', 'ozon')
    svc = IntegrationService(shop_id=int(request.args.get('shopId', 1)))
    return jsonify(svc.get_data_source_config(provider=provider))


@integration_bp.route('/data-source', methods=['POST'])
def save_data_source():
    payload = request.get_json() or {}
    svc = IntegrationService(shop_id=int(payload.get('shopId') or 1))
    return jsonify(svc.save_data_source_config(payload))


@integration_bp.route('/permission-check', methods=['POST'])
def permission_check():
    payload = request.get_json() or {}
    svc = IntegrationService(shop_id=int(payload.get('shopId') or 1))
    return jsonify(svc.check_permissions(provider=payload.get('provider', 'ozon')))


@integration_bp.route('/sync-once', methods=['POST'])
def sync_once():
    payload = request.get_json() or {}
    svc = IntegrationService(shop_id=int(payload.get('shopId') or 1))
    return jsonify(svc.run_sync_once(
        provider=payload.get('provider', 'ozon'),
        trigger_mode='manual',
        scopes=payload.get('scopes') or None,
    ))


@integration_bp.route('/pricing-autofill', methods=['GET'])
def pricing_autofill():
    svc = IntegrationService(shop_id=int(request.args.get('shopId', 1)))
    return jsonify(svc.get_pricing_autofill(provider=request.args.get('provider', 'ozon')))


@integration_bp.route('/sync-logs', methods=['GET'])
def sync_logs():
    svc = IntegrationService(shop_id=int(request.args.get('shopId', 1)))
    return jsonify({'rows': svc.list_sync_logs(limit=int(request.args.get('limit', 20)))})


@integration_bp.route('/import-logs', methods=['GET'])
def import_logs():
    svc = IntegrationService(shop_id=int(request.args.get('shopId', 1)))
    return jsonify({'rows': svc.list_import_logs(limit=int(request.args.get('limit', 20)))})


@integration_bp.route('/push-sales', methods=['POST'])
def push_sales():
    payload = request.get_json() or {}
    svc = IntegrationService(shop_id=int(payload.get('shopId') or 1))
    result = svc.push_to_sales_backend(
        payload=payload.get('payload') or payload,
        target_url=payload.get('targetUrl'),
        strategy_task_id=payload.get('strategyTaskId'),
        execution_log_id=payload.get('executionLogId'),
    )
    return jsonify(result)


@integration_bp.route('/push-logs', methods=['GET'])
def push_logs():
    svc = IntegrationService(shop_id=int(request.args.get('shopId', 1)))
    return jsonify({'rows': svc.list_push_logs(limit=int(request.args.get('limit', 20)))})


@integration_bp.route('/mock/sales-backend', methods=['POST'])
def mock_sales_backend():
    payload = request.get_json() or {}
    return jsonify({'status': 'accepted', 'received': payload, 'message': 'mock sales backend ok'})


@integration_bp.route('/mock/ozon/<scope_key>', methods=['POST'])
def mock_ozon_scope(scope_key: str):
    sample = {
        'product_catalog': {'rows': [{'sku': 'SKU-1001', 'list_price': 139, 'sale_price': 119}]},
        'orders_fulfillment': {'rows': [{'sku': 'SKU-1001', 'fulfillment_mode': 'FBO', 'warehouse': '义乌仓'}]},
        'promotion_pricing': {'rows': [{'sku': 'SKU-1001', 'action_price': 105, 'want_discount_price': 101}]},
        'service_after_sales': {'rows': [{'sku': 'SKU-1001', 'return_rate': 0.03, 'cancel_rate': 0.02, 'rating': 4.2}]},
        'reporting_analytics': {'rows': [{'sku': 'SKU-1001', 'ads_rate_7d': 0.065, 'margin_15d': 0.11}]},
    }
    return jsonify(sample.get(scope_key, {'rows': []}))
