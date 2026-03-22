from __future__ import annotations

from pathlib import Path

from flask import Blueprint, request

from ecom_v51.services.batch_service import BatchService

from .common import fail, ok

batches_bp = Blueprint("api_v1_batches", __name__)
ROOT_DIR = Path(__file__).resolve().parents[5]
batch_service = BatchService(ROOT_DIR)


@batches_bp.route('', methods=['GET'])
def list_batches_v1():
    try:
        limit = int(request.args.get('limit') or 20)
        data = batch_service.list_recent_batches(limit=limit)
        return ok(data)
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
