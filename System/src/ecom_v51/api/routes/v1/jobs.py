from __future__ import annotations

from pathlib import Path

from flask import Blueprint

from ecom_v51.api.routes import import_route
from ecom_v51.services.batch_runtime_service import BatchRuntimeService
from ecom_v51.services.runtime_query_service import RuntimeQueryService

from .common import fail, ok

jobs_bp = Blueprint("api_v1_jobs", __name__)
ROOT_DIR = Path(__file__).resolve().parents[5]
runtime_query_service = RuntimeQueryService(ROOT_DIR)


def _get_runtime_service() -> BatchRuntimeService:
    return BatchRuntimeService(
        root_dir=ROOT_DIR,
        import_service=import_route.import_service,
        workspace_service=import_route.batch_workspace,
        batch_service=import_route._get_batch_service(),
    )


def _get_query_service() -> RuntimeQueryService:
    return runtime_query_service


@jobs_bp.route('/<job_ref>', methods=['GET'])
def get_job_v1(job_ref: str):
    try:
        payload = _get_query_service().get_job_detail(job_ref)
        if not payload:
            runtime = _get_runtime_service()
            payload = runtime.get_job(job_ref) if hasattr(runtime, 'get_job') else None
        if not payload:
            return fail('job_not_found', '作业不存在', status_code=404)
        return ok(payload)
    except Exception as exc:
        return fail('job_detail_failed', '读取作业详情失败', details={'reason': str(exc)}, status_code=500)


@jobs_bp.route('/<job_ref>/events', methods=['GET'])
def get_job_events_v1(job_ref: str):
    try:
        payload = _get_query_service().get_job_events(job_ref)
        if not payload:
            runtime = _get_runtime_service()
            if hasattr(runtime, 'get_job_events'):
                payload = runtime.get_job_events(job_ref)
            elif hasattr(runtime, 'get_job'):
                job = runtime.get_job(job_ref)
                if job:
                    timeline = list(job.get('timeline') or [])
                    payload = {
                        'jobId': job.get('jobId'),
                        'jobCode': job.get('jobCode'),
                        'batchId': job.get('batchId'),
                        'contractVersion': job.get('contractVersion') or 'p2a.v1',
                        'events': timeline,
                        'total': len(timeline),
                    }
        if not payload:
            return fail('job_not_found', '作业不存在', status_code=404)
        return ok(payload)
    except Exception as exc:
        return fail('job_events_failed', '读取作业事件失败', details={'reason': str(exc)}, status_code=500)
