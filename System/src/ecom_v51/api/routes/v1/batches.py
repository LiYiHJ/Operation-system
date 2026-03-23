from __future__ import annotations

from pathlib import Path

from flask import Blueprint, request

from ecom_v51.services.batch_service import BatchService
from ecom_v51.services.runtime_query_service import RuntimeQueryService

from .common import fail, ok

batches_bp = Blueprint("api_v1_batches", __name__)
ROOT_DIR = Path(__file__).resolve().parents[5]
batch_service = BatchService(ROOT_DIR)
runtime_query_service = RuntimeQueryService(ROOT_DIR)


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
        dataset_kind = str(request.args.get('datasetKind') or '').strip().lower() or None
        importability_status = str(request.args.get('importabilityStatus') or '').strip().lower() or None
        source_mode = str(request.args.get('sourceMode') or '').strip().lower() or None
        data = batch_service.list_recent_batches(limit=limit)
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
            'datasetKind': dataset_kind,
            'importabilityStatus': importability_status,
            'sourceMode': source_mode,
        }
        return ok(payload)
    except Exception as exc:
        return fail('batch_list_failed', '读取批次列表失败', details={'reason': str(exc)}, status_code=500)


@batches_bp.route('/<batch_ref>', methods=['GET'])
def get_batch_detail_v1(batch_ref: str):
    try:
        data = batch_service.get_batch_detail(batch_ref)
        if not data:
            return fail('batch_not_found', '批次不存在', status_code=404)
        return ok(data)
    except Exception as exc:
        return fail('batch_detail_failed', '读取批次详情失败', details={'reason': str(exc)}, status_code=500)


@batches_bp.route('/<batch_ref>/timeline', methods=['GET'])
def get_batch_timeline_v1(batch_ref: str):
    try:
        data = batch_service.get_batch_timeline(batch_ref)
        if not data:
            return fail('batch_not_found', '批次不存在', status_code=404)
        return ok(data)
    except Exception as exc:
        return fail('batch_timeline_failed', '读取批次时间线失败', details={'reason': str(exc)}, status_code=500)


@batches_bp.route('/<batch_ref>/quarantine-summary', methods=['GET'])
def get_quarantine_summary_v1(batch_ref: str):
    try:
        data = batch_service.get_batch_quarantine_summary(batch_ref)
        if not data:
            return fail('batch_not_found', '批次不存在', status_code=404)
        return ok(data)
    except Exception as exc:
        return fail('batch_quarantine_failed', '读取隔离摘要失败', details={'reason': str(exc)}, status_code=500)


@batches_bp.route('/<batch_ref>/raw-records', methods=['GET'])
def get_raw_records_v1(batch_ref: str):
    try:
        limit = int(request.args.get('limit') or 50)
        data = runtime_query_service.get_batch_raw_records(batch_ref, limit=limit)
        if not data:
            return fail('batch_not_found', '批次不存在', status_code=404)
        return ok(data)
    except Exception as exc:
        return fail('batch_raw_records_failed', '读取原始记录失败', details={'reason': str(exc)}, status_code=500)

@batches_bp.route('/<batch_ref>/replay', methods=['POST'])
def replay_batch_v1(batch_ref: str):
    try:
        payload = request.get_json(silent=True) or {}
        trace_id = payload.get('traceId')
        idempotency_key = payload.get('idempotencyKey')
        operator = payload.get('operator') or 'p2a_runtime_report'

        data = batch_service.replay_batch(
            batch_ref=batch_ref,
            trace_id=trace_id,
            idempotency_key=idempotency_key,
            operator=operator,
        )
        return ok(data, status_code=202)
    except Exception as exc:
        return fail(
            'batch_replay_failed',
            '批次重放失败',
            details={'reason': str(exc)},
            status_code=500,
        )