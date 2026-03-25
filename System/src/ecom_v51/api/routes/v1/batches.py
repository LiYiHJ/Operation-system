from __future__ import annotations

from pathlib import Path

from flask import Blueprint, request

from ecom_v51.services.batch_runtime_service import BatchRuntimeService
from ecom_v51.services.batch_service import BatchService
from ecom_v51.services.runtime_query_service import RuntimeQueryService
from ecom_v51.api.routes import import_route

from .common import fail, get_trace_id, ok

batches_bp = Blueprint("api_v1_batches", __name__)
ROOT_DIR = Path(__file__).resolve().parents[5]
batch_service = BatchService(ROOT_DIR)
runtime_query_service = RuntimeQueryService(ROOT_DIR)


def _get_batch_service() -> BatchService:
    return batch_service


def _get_query_service() -> RuntimeQueryService:
    return runtime_query_service


def _get_runtime_service() -> BatchRuntimeService:
    return BatchRuntimeService(
        root_dir=ROOT_DIR,
        import_service=import_route.import_service,
        workspace_service=import_route.batch_workspace,
        batch_service=import_route._get_batch_service(),
    )


def _filter_items(items, dataset_kind: str | None, importability_status: str | None, source_mode: str | None):
    out = list(items or [])
    if dataset_kind:
        out = [item for item in out if str(item.get('datasetKind') or '').strip().lower() == dataset_kind]
    if importability_status:
        out = [item for item in out if str(item.get('importabilityStatus') or '').strip().lower() == importability_status]
    if source_mode:
        out = [item for item in out if str(item.get('sourceMode') or '').strip().lower() == source_mode]
    return out


@batches_bp.route('', methods=['GET'])
def list_batches_v1():
    try:
        limit = int(request.args.get('limit') or 20)
        try:
            shop_id = int(request.args.get('shopId') or 0) or None
        except Exception:
            shop_id = None
        dataset_kind = str(request.args.get('datasetKind') or '').strip().lower() or None
        status = str(request.args.get('status') or '').strip().lower() or None
        importability_status = str(request.args.get('importabilityStatus') or '').strip().lower() or None
        source_mode = str(request.args.get('sourceMode') or '').strip().lower() or None
        service = _get_batch_service()
        try:
            data = service.list_recent_batches(
                limit=limit,
                shop_id=shop_id,
                dataset_kind=dataset_kind,
                status=status,
            )
        except TypeError:
            data = service.list_recent_batches(limit=limit)
        filtered_items = _filter_items(
            data.get('items') or [],
            dataset_kind=dataset_kind,
            importability_status=importability_status,
            source_mode=source_mode,
        )
        payload = dict(data or {})
        payload['items'] = filtered_items[: max(limit, 1)]
        payload['total'] = len(filtered_items)
        payload['filters'] = {
            'shopId': shop_id,
            'datasetKind': dataset_kind,
            'status': status,
            'importabilityStatus': importability_status,
            'sourceMode': source_mode,
        }
        return ok(payload)
    except Exception as exc:
        return fail('batch_list_failed', '读取批次列表失败', details={'reason': str(exc)}, status_code=500)


@batches_bp.route('/<batch_ref>', methods=['GET'])
def get_batch_detail_v1(batch_ref: str):
    try:
        data = _get_batch_service().get_batch_detail(batch_ref)
        if not data:
            return fail('batch_not_found', '批次不存在', status_code=404)
        return ok(data)
    except Exception as exc:
        return fail('batch_detail_failed', '读取批次详情失败', details={'reason': str(exc)}, status_code=500)


@batches_bp.route('/<batch_ref>/timeline', methods=['GET'])
def get_batch_timeline_v1(batch_ref: str):
    try:
        data = _get_batch_service().get_batch_timeline(batch_ref)
        if not data:
            return fail('batch_not_found', '批次不存在', status_code=404)
        return ok(data)
    except Exception as exc:
        return fail('batch_timeline_failed', '读取批次时间线失败', details={'reason': str(exc)}, status_code=500)


@batches_bp.route('/<batch_ref>/quarantine-summary', methods=['GET'])
def get_quarantine_summary_v1(batch_ref: str):
    try:
        data = _get_batch_service().get_batch_quarantine_summary(batch_ref)
        if not data:
            return fail('batch_not_found', '批次不存在', status_code=404)
        return ok(data)
    except Exception as exc:
        return fail('batch_quarantine_failed', '读取隔离摘要失败', details={'reason': str(exc)}, status_code=500)


@batches_bp.route('/<batch_ref>/raw-records', methods=['GET'])
def get_raw_records_v1(batch_ref: str):
    try:
        limit = int(request.args.get('limit') or 50)
        data = _get_query_service().get_batch_raw_records(batch_ref, limit=limit)
        if not data:
            return fail('batch_not_found', '批次不存在', status_code=404)
        return ok(data)
    except Exception as exc:
        return fail('batch_raw_records_failed', '读取原始记录失败', details={'reason': str(exc)}, status_code=500)


@batches_bp.route('/<batch_ref>/confirm', methods=['POST'])
def confirm_batch_v1(batch_ref: str):
    trace_id = get_trace_id()
    payload = request.get_json(silent=True) or {}
    idempotency_key = str(request.headers.get('Idempotency-Key') or request.headers.get('IdempotencyKey') or payload.get('idempotencyKey') or '').strip() or None
    operator = str(payload.get('operator') or 'p2a_runtime_report').strip() or 'p2a_runtime_report'
    gate_mode = str(payload.get('gateMode') or 'manual_continue').strip() or 'manual_continue'
    notes = str(payload.get('notes') or '').strip()
    manual_overrides = payload.get('manualOverrides') or []
    try:
        data = _get_runtime_service().confirm_batch(
            batch_ref=batch_ref,
            operator=operator,
            gate_mode=gate_mode,
            notes=notes,
            trace_id=trace_id,
            idempotency_key=idempotency_key,
            manual_overrides=manual_overrides,
        )
        return ok(data, trace_id=trace_id, status_code=202)
    except Exception as exc:
        return fail(
            'batch_confirm_failed',
            '批次确认失败',
            details={'reason': str(exc)},
            status_code=500,
            trace_id=trace_id,
        )


@batches_bp.route('/<batch_ref>/replay', methods=['POST'])
def replay_batch_v1(batch_ref: str):
    trace_id = get_trace_id()
    payload = request.get_json(silent=True) or {}
    idempotency_key = str(request.headers.get('Idempotency-Key') or request.headers.get('IdempotencyKey') or payload.get('idempotencyKey') or '').strip() or None
    operator = str(payload.get('operator') or 'p2a_runtime_report').strip() or 'p2a_runtime_report'
    notes = str(payload.get('notes') or '').strip()
    try:
        data = _get_runtime_service().replay_batch(
            batch_ref=batch_ref,
            trace_id=trace_id,
            idempotency_key=idempotency_key,
            operator=operator,
            notes=notes,
        )
        return ok(data, trace_id=trace_id, status_code=202)
    except Exception as exc:
        return fail(
            'batch_replay_failed',
            '批次重放失败',
            details={'reason': str(exc)},
            status_code=500,
            trace_id=trace_id,
        )
