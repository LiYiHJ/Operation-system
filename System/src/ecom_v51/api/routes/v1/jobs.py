from __future__ import annotations

from flask import Blueprint

from .common import fail, ok

jobs_bp = Blueprint("api_v1_jobs", __name__)


@jobs_bp.route('/<job_id>', methods=['GET'])
def get_job_v1(job_id: str):
    payload = {
        'jobId': job_id,
        'status': 'pending_contract',
        'message': 'P0a 第一轮仅建立 /api/v1/jobs 占位接口，异步作业主链将在后续轮次接入。',
    }
    return ok(payload)
