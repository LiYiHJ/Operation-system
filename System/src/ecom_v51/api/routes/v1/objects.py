from __future__ import annotations

from pathlib import Path

from flask import Blueprint, request

from ecom_v51.services.object_assembly_service import ObjectAssemblyService

from .common import fail, ok

objects_bp = Blueprint('api_v1_objects', __name__)
ROOT_DIR = Path(__file__).resolve().parents[5]
object_service = ObjectAssemblyService(ROOT_DIR)


def _get_object_service() -> ObjectAssemblyService:
    return object_service


@objects_bp.route('/assemble', methods=['POST'])
def assemble_objects_v1():
    payload = request.get_json(silent=True) or {}
    batch_ref = str(payload.get('batchRef') or payload.get('batchId') or '').strip()
    operator = str(payload.get('operator') or 'frontend_user').strip() or 'frontend_user'
    if not batch_ref:
        return fail('missing_batch_ref', '缺少 batchRef', status_code=400)
    try:
        data = _get_object_service().assemble_batch(batch_ref, operator=operator)
        return ok(data, status_code=202)
    except FileNotFoundError as exc:
        return fail('object_assembly_source_not_found', '对象装配源文件不存在', details={'reason': str(exc)}, status_code=404)
    except ValueError as exc:
        code = str(exc)
        if code == 'batch_not_found':
            return fail('batch_not_found', '批次不存在', status_code=404)
        if code == 'object_assembly_dataset_not_supported':
            return fail('object_assembly_dataset_not_supported', '当前仅支持 orders 批次对象装配', status_code=409)
        return fail('object_assembly_failed', '对象装配失败', details={'reason': code}, status_code=409)
    except Exception as exc:
        return fail('object_assembly_failed', '对象装配失败', details={'reason': str(exc)}, status_code=500)


@objects_bp.route('/batches/<batch_ref>/summary', methods=['GET'])
def get_object_summary_v1(batch_ref: str):
    try:
        data = _get_object_service().get_batch_object_summary(batch_ref)
        if not data:
            return fail('batch_not_found', '批次不存在', status_code=404)
        return ok(data)
    except Exception as exc:
        return fail('object_summary_failed', '读取对象装配摘要失败', details={'reason': str(exc)}, status_code=500)


@objects_bp.route('/batches/<batch_ref>/details', methods=['GET'])
def get_object_details_v1(batch_ref: str):
    section = str(request.args.get('section') or 'orderLines').strip() or 'orderLines'
    limit = request.args.get('limit', default=50, type=int)
    offset = request.args.get('offset', default=0, type=int)
    try:
        data = _get_object_service().get_batch_object_details(batch_ref, section=section, limit=limit, offset=offset)
        if not data:
            return fail('batch_not_found', '批次不存在', status_code=404)
        return ok(data)
    except ValueError as exc:
        if str(exc) == 'unsupported_object_section':
            return fail('unsupported_object_section', '不支持的对象明细分区', details={'section': section}, status_code=400)
        return fail('object_details_failed', '读取对象明细失败', details={'reason': str(exc)}, status_code=409)
    except Exception as exc:
        return fail('object_details_failed', '读取对象明细失败', details={'reason': str(exc)}, status_code=500)


@objects_bp.route('/batches/<batch_ref>/diagnostics', methods=['GET'])
def get_object_diagnostics_v1(batch_ref: str):
    try:
        data = _get_object_service().get_batch_object_diagnostics(batch_ref)
        if not data:
            return fail('batch_not_found', '批次不存在', status_code=404)
        return ok(data)
    except Exception as exc:
        return fail('object_diagnostics_failed', '读取对象装配诊断失败', details={'reason': str(exc)}, status_code=500)


@objects_bp.route('/batches/<batch_ref>/rollups', methods=['GET'])
def get_object_rollups_v1(batch_ref: str):
    try:
        data = _get_object_service().get_batch_object_rollups(batch_ref)
        if not data:
            return fail('batch_not_found', '批次不存在', status_code=404)
        return ok(data)
    except Exception as exc:
        return fail('object_rollups_failed', '读取对象装配聚合视图失败', details={'reason': str(exc)}, status_code=500)


@objects_bp.route('/batches/<batch_ref>/facts', methods=['GET'])
def get_object_facts_v1(batch_ref: str):
    limit = request.args.get('limit', default=50, type=int)
    offset = request.args.get('offset', default=0, type=int)
    view = str(request.args.get('view') or 'all').strip() or 'all'
    preset = str(request.args.get('preset') or 'debug_full').strip() or 'debug_full'
    try:
        data = _get_object_service().get_batch_object_facts(batch_ref, limit=limit, offset=offset, view=view, preset=preset)
        if not data:
            return fail('batch_not_found', '批次不存在', status_code=404)
        return ok(data)
    except ValueError as exc:
        if str(exc) == 'unsupported_fact_view':
            return fail('unsupported_fact_view', '不支持的事实视图', details={'view': view}, status_code=400)
        if str(exc) == 'unsupported_fact_preset':
            return fail('unsupported_fact_preset', '不支持的事实消费预设', details={'preset': preset}, status_code=400)
        return fail('object_facts_failed', '读取对象事实读面失败', details={'reason': str(exc)}, status_code=409)
    except Exception as exc:
        return fail('object_facts_failed', '读取对象事实读面失败', details={'reason': str(exc)}, status_code=500)


@objects_bp.route('/batches/<batch_ref>/facts/contract', methods=['GET'])
def get_object_fact_contract_v1(batch_ref: str):
    try:
        data = _get_object_service().get_batch_object_fact_contract(batch_ref)
        if not data:
            return fail('batch_not_found', '批次不存在', status_code=404)
        return ok(data)
    except Exception as exc:
        return fail('object_fact_contract_failed', '读取对象事实契约失败', details={'reason': str(exc)}, status_code=500)
