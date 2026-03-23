from __future__ import annotations

from pathlib import Path

from flask import Blueprint

from ecom_v51.services.runtime_query_service import RuntimeQueryService

from .common import fail, ok

jobs_bp = Blueprint("api_v1_jobs", __name__)
ROOT_DIR = Path(__file__).resolve().parents[5]
runtime_query_service = RuntimeQueryService(ROOT_DIR)


@jobs_bp.route('/<job_ref>', methods=['GET'])
def get_job_v1(job_ref: str):
    try:
        payload = runtime_query_service.get_job_detail(job_ref)
        if not payload:
            return fail('job_not_found', '作业不存在', status_code=404)
        return ok(payload)
    except Exception as exc:
        return fail('job_detail_failed', '读取作业详情失败', details={'reason': str(exc)}, status_code=500)


@jobs_bp.route('/<job_ref>/events', methods=['GET'])
def get_job_events_v1(job_ref: str):
    try:
        payload = runtime_query_service.get_job_events(job_ref)
        if not payload:
            return fail('job_not_found', '作业不存在', status_code=404)
        return ok(payload)
    except Exception as exc:
        return fail('job_events_failed', '读取作业事件失败', details={'reason': str(exc)}, status_code=500)
