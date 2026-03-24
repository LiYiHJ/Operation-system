from __future__ import annotations

from pathlib import Path

from flask import Blueprint, request

from ecom_v51.services.economics_config_service import EconomicsConfigService
from ecom_v51.services.economics_intake_service import EconomicsIntakeService

from .common import fail, ok


economics_bp = Blueprint('api_v1_economics', __name__)
ROOT_DIR = Path(__file__).resolve().parents[5]
economics_service = EconomicsIntakeService(ROOT_DIR)
economics_config_service = EconomicsConfigService(ROOT_DIR)


def _get_economics_service() -> EconomicsIntakeService:
    return economics_service


def _get_economics_config_service() -> EconomicsConfigService:
    return economics_config_service


@economics_bp.route('/batches/<batch_ref>/intake', methods=['GET'])
def get_batch_economics_intake_v1(batch_ref: str):
    limit = request.args.get('limit', default=50, type=int)
    offset = request.args.get('offset', default=0, type=int)
    view = str(request.args.get('view') or 'ready').strip() or 'ready'
    try:
        data = _get_economics_service().get_batch_economics_intake(batch_ref, limit=limit, offset=offset, view=view)
        if not data:
            return fail('batch_not_found', '批次不存在', status_code=404)
        return ok(data)
    except ValueError as exc:
        if str(exc) == 'unsupported_fact_view':
            return fail('unsupported_economics_intake_view', '不支持的经济入口视图', details={'view': view}, status_code=400)
        return fail('economics_intake_failed', '读取经济入口摘要失败', details={'reason': str(exc)}, status_code=409)
    except Exception as exc:
        return fail('economics_intake_failed', '读取经济入口摘要失败', details={'reason': str(exc)}, status_code=500)


@economics_bp.route('/batches/<batch_ref>/intake/contract', methods=['GET'])
def get_batch_economics_intake_contract_v1(batch_ref: str):
    try:
        data = _get_economics_service().get_batch_economics_intake_contract(batch_ref)
        if not data:
            return fail('batch_not_found', '批次不存在', status_code=404)
        return ok(data)
    except Exception as exc:
        return fail('economics_intake_contract_failed', '读取经济入口契约失败', details={'reason': str(exc)}, status_code=500)


@economics_bp.route('/batches/<batch_ref>/core', methods=['GET'])
def get_batch_economics_core_v1(batch_ref: str):
    limit = request.args.get('limit', default=50, type=int)
    offset = request.args.get('offset', default=0, type=int)
    view = str(request.args.get('view') or 'all').strip() or 'all'
    try:
        data = _get_economics_service().get_batch_economics_core(batch_ref, limit=limit, offset=offset, view=view)
        if not data:
            return fail('batch_not_found', '批次不存在', status_code=404)
        return ok(data)
    except ValueError as exc:
        if str(exc) == 'unsupported_fact_view':
            return fail('unsupported_economics_core_view', '不支持的经济核心视图', details={'view': view}, status_code=400)
        return fail('economics_core_failed', '读取经济核心摘要失败', details={'reason': str(exc)}, status_code=409)
    except Exception as exc:
        return fail('economics_core_failed', '读取经济核心摘要失败', details={'reason': str(exc)}, status_code=500)


@economics_bp.route('/batches/<batch_ref>/core/contract', methods=['GET'])
def get_batch_economics_core_contract_v1(batch_ref: str):
    try:
        data = _get_economics_service().get_batch_economics_core_contract(batch_ref)
        if not data:
            return fail('batch_not_found', '批次不存在', status_code=404)
        return ok(data)
    except Exception as exc:
        return fail('economics_core_contract_failed', '读取经济核心契约失败', details={'reason': str(exc)}, status_code=500)


@economics_bp.route('/batches/<batch_ref>/resolve', methods=['GET'])
def get_batch_economics_config_resolve_v1(batch_ref: str):
    limit = request.args.get('limit', default=50, type=int)
    offset = request.args.get('offset', default=0, type=int)
    view = str(request.args.get('view') or 'all').strip() or 'all'
    try:
        data = _get_economics_config_service().get_batch_config_resolve(batch_ref, limit=limit, offset=offset, view=view)
        if not data:
            return fail('batch_not_found', '批次不存在', status_code=404)
        return ok(data)
    except ValueError as exc:
        if str(exc) == 'unsupported_config_resolve_view':
            return fail('unsupported_economics_config_resolve_view', '不支持的经济配置解析视图', details={'view': view}, status_code=400)
        return fail('economics_config_resolve_failed', '读取经济配置解析失败', details={'reason': str(exc)}, status_code=409)
    except Exception as exc:
        return fail('economics_config_resolve_failed', '读取经济配置解析失败', details={'reason': str(exc)}, status_code=500)


@economics_bp.route('/batches/<batch_ref>/resolve/contract', methods=['GET'])
def get_batch_economics_config_resolve_contract_v1(batch_ref: str):
    try:
        data = _get_economics_config_service().get_batch_config_resolve_contract(batch_ref)
        if not data:
            return fail('batch_not_found', '批次不存在', status_code=404)
        return ok(data)
    except Exception as exc:
        return fail('economics_config_resolve_contract_failed', '读取经济配置解析契约失败', details={'reason': str(exc)}, status_code=500)


@economics_bp.route('/batches/<batch_ref>/solve', methods=['GET'])
def get_batch_profit_solve_v1(batch_ref: str):
    limit = request.args.get('limit', default=50, type=int)
    offset = request.args.get('offset', default=0, type=int)
    view = str(request.args.get('view') or 'all').strip() or 'all'
    try:
        data = _get_economics_service().get_batch_profit_solve(batch_ref, limit=limit, offset=offset, view=view)
        if not data:
            return fail('batch_not_found', '批次不存在', status_code=404)
        return ok(data)
    except ValueError as exc:
        if str(exc) == 'unsupported_fact_view':
            return fail('unsupported_profit_solve_view', '不支持的利润求解视图', details={'view': view}, status_code=400)
        return fail('profit_solve_failed', '读取利润求解失败', details={'reason': str(exc)}, status_code=409)
    except Exception as exc:
        return fail('profit_solve_failed', '读取利润求解失败', details={'reason': str(exc)}, status_code=500)


@economics_bp.route('/batches/<batch_ref>/solve/contract', methods=['GET'])
def get_batch_profit_solve_contract_v1(batch_ref: str):
    try:
        data = _get_economics_service().get_batch_profit_solve_contract(batch_ref)
        if not data:
            return fail('batch_not_found', '批次不存在', status_code=404)
        return ok(data)
    except Exception as exc:
        return fail('profit_solve_contract_failed', '读取利润求解契约失败', details={'reason': str(exc)}, status_code=500)


@economics_bp.route('/pricing/recommend', methods=['POST'])
def pricing_recommend_v1():
    payload = request.get_json(silent=True) or {}
    batch_ref = str(payload.get('batchRef') or '').strip()
    strategy_mode = str(payload.get('strategyMode') or 'balanced_profit').strip() or 'balanced_profit'
    constraints = payload.get('constraints') or {}
    limit = int(payload.get('limit') or 50)
    offset = int(payload.get('offset') or 0)
    view = str(payload.get('view') or 'all').strip() or 'all'
    if not batch_ref:
        return fail('batch_ref_required', 'pricing recommend skeleton 当前需要 batchRef', status_code=400)
    try:
        data = _get_economics_service().get_batch_pricing_recommend(
            batch_ref,
            strategy_mode=strategy_mode,
            constraints=constraints,
            limit=limit,
            offset=offset,
            view=view,
        )
        if not data:
            return fail('batch_not_found', '批次不存在', status_code=404)
        return ok(data)
    except ValueError as exc:
        if str(exc) == 'unsupported_fact_view':
            return fail('unsupported_pricing_recommend_view', '不支持的定价建议视图', details={'view': view}, status_code=400)
        return fail('pricing_recommend_failed', '生成定价建议失败', details={'reason': str(exc)}, status_code=409)
    except Exception as exc:
        return fail('pricing_recommend_failed', '生成定价建议失败', details={'reason': str(exc)}, status_code=500)


@economics_bp.route('/pricing/recommend/contract', methods=['GET'])
def pricing_recommend_contract_v1():
    batch_ref = str(request.args.get('batchRef') or '').strip()
    strategy_mode = str(request.args.get('strategyMode') or 'balanced_profit').strip() or 'balanced_profit'
    if not batch_ref:
        return fail('batch_ref_required', 'pricing recommend contract 当前需要 batchRef', status_code=400)
    try:
        data = _get_economics_service().get_batch_pricing_recommend_contract(batch_ref, strategy_mode=strategy_mode)
        if not data:
            return fail('batch_not_found', '批次不存在', status_code=404)
        return ok(data)
    except Exception as exc:
        return fail('pricing_recommend_contract_failed', '读取定价建议契约失败', details={'reason': str(exc)}, status_code=500)


@economics_bp.route('/config/contract', methods=['GET'])
def get_economics_config_contract_v1():
    try:
        return ok(_get_economics_config_service().get_config_contract())
    except Exception as exc:
        return fail('economics_config_contract_failed', '读取经济配置契约失败', details={'reason': str(exc)}, status_code=500)


@economics_bp.route('/config/cost-components', methods=['GET', 'POST'])
def economics_cost_components_v1():
    try:
        if request.method == 'POST':
            payload = request.get_json(silent=True) or {}
            return ok(_get_economics_config_service().upsert_cost_component(payload))
        active_only = request.args.get('activeOnly', default=1, type=int) != 0
        return ok(_get_economics_config_service().list_cost_components(active_only=active_only))
    except ValueError as exc:
        return fail('economics_cost_component_invalid', '成本组件参数非法', details={'reason': str(exc)}, status_code=400)
    except Exception as exc:
        return fail('economics_cost_component_failed', '读取或写入成本组件失败', details={'reason': str(exc)}, status_code=500)


@economics_bp.route('/config/profit-profiles', methods=['GET', 'POST'])
def economics_profit_profiles_v1():
    try:
        if request.method == 'POST':
            payload = request.get_json(silent=True) or {}
            return ok(_get_economics_config_service().upsert_profit_profile(payload))
        active_only = request.args.get('activeOnly', default=1, type=int) != 0
        return ok(_get_economics_config_service().list_profit_profiles(active_only=active_only))
    except ValueError as exc:
        return fail('economics_profit_profile_invalid', '利润口径参数非法', details={'reason': str(exc)}, status_code=400)
    except Exception as exc:
        return fail('economics_profit_profile_failed', '读取或写入口径配置失败', details={'reason': str(exc)}, status_code=500)


@economics_bp.route('/config/sku-cost-cards', methods=['GET', 'POST'])
def economics_sku_cost_cards_v1():
    try:
        if request.method == 'POST':
            payload = request.get_json(silent=True) or {}
            return ok(_get_economics_config_service().upsert_sku_cost_card(payload))
        shop_id = request.args.get('shopId', type=int)
        canonical_sku = (request.args.get('canonicalSku') or '').strip() or None
        profile_code = (request.args.get('profileCode') or '').strip() or None
        active_only = request.args.get('activeOnly', default=1, type=int) != 0
        return ok(
            _get_economics_config_service().list_sku_cost_cards(
                shop_id=shop_id,
                canonical_sku=canonical_sku,
                profile_code=profile_code,
                active_only=active_only,
            )
        )
    except ValueError as exc:
        return fail('economics_cost_card_invalid', 'SKU 成本卡参数非法', details={'reason': str(exc)}, status_code=400)
    except Exception as exc:
        return fail('economics_cost_card_failed', '读取或写入 SKU 成本卡失败', details={'reason': str(exc)}, status_code=500)
