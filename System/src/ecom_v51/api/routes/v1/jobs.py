from __future__ import annotations

from pathlib import Path

from flask import Blueprint, request

from ecom_v51.api.routes import import_route
from ecom_v51.services.action_queue_service import ActionQueueService
from ecom_v51.services.batch_runtime_service import BatchRuntimeService
from ecom_v51.services.runtime_query_service import RuntimeQueryService

from .common import fail, get_trace_id, ok

jobs_bp = Blueprint("api_v1_jobs", __name__)
ROOT_DIR = Path(__file__).resolve().parents[5]
runtime_query_service = RuntimeQueryService(ROOT_DIR)
action_queue_service = ActionQueueService()


def _get_runtime_service() -> BatchRuntimeService:
    return BatchRuntimeService(
        root_dir=ROOT_DIR,
        import_service=import_route.import_service,
        workspace_service=import_route.batch_workspace,
        batch_service=import_route._get_batch_service(),
    )


def _get_query_service() -> RuntimeQueryService:
    return runtime_query_service


def _get_action_queue_service() -> ActionQueueService:
    return action_queue_service


def _errors_payload(errors: list[dict]) -> dict:
    return {'sources': errors}


@jobs_bp.route('/<job_ref>', methods=['GET'])
def get_job_v1(job_ref: str):
    errors: list[dict] = []
    payload = None

    try:
        payload = _get_query_service().get_job_detail(job_ref)
    except Exception as exc:
        errors.append({'source': 'runtime_query_service', 'reason': str(exc)})

    if not payload:
        try:
            runtime = _get_runtime_service()
            payload = runtime.get_job(job_ref) if hasattr(runtime, 'get_job') else None
        except Exception as exc:
            errors.append({'source': 'batch_runtime_service', 'reason': str(exc)})

    if not payload:
        try:
            payload = _get_action_queue_service().get_job_detail(job_ref)
        except Exception as exc:
            errors.append({'source': 'action_queue_service', 'reason': str(exc)})

    if payload:
        return ok(payload)
    if errors:
        return fail('job_detail_failed', '读取作业详情失败', details=_errors_payload(errors), status_code=500)
    return fail('job_not_found', '作业不存在', status_code=404)


@jobs_bp.route('/<job_ref>/events', methods=['GET'])
def get_job_events_v1(job_ref: str):
    errors: list[dict] = []
    payload = None

    try:
        payload = _get_query_service().get_job_events(job_ref)
    except Exception as exc:
        errors.append({'source': 'runtime_query_service', 'reason': str(exc)})

    if not payload:
        try:
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
        except Exception as exc:
            errors.append({'source': 'batch_runtime_service', 'reason': str(exc)})

    if not payload:
        try:
            payload = _get_action_queue_service().get_job_events(job_ref)
        except Exception as exc:
            errors.append({'source': 'action_queue_service', 'reason': str(exc)})

    if payload:
        return ok(payload)
    if errors:
        return fail('job_events_failed', '读取作业事件失败', details=_errors_payload(errors), status_code=500)
    return fail('job_not_found', '作业不存在', status_code=404)


def _job_command_payload() -> tuple[str, str | None, str | None, str, str | None]:
    trace_id = get_trace_id()
    payload = request.get_json(silent=True) or {}
    operator = str(payload.get('operator') or 'system').strip() or 'system'
    reason = str(payload.get('reason') or '').strip() or None
    note = str(payload.get('note') or '').strip() or None
    idempotency_key = str(request.headers.get('Idempotency-Key') or request.headers.get('IdempotencyKey') or payload.get('idempotencyKey') or '').strip() or None
    return operator, reason, note, trace_id, idempotency_key


@jobs_bp.route('/<job_ref>/heartbeat', methods=['POST'])
def heartbeat_job_v1(job_ref: str):
    operator, _reason, note, trace_id, _idempotency_key = _job_command_payload()
    payload = request.get_json(silent=True) or {}
    worker_id = str(payload.get('workerId') or payload.get('worker_id') or '').strip()
    try:
        data = _get_action_queue_service().heartbeat_job(job_ref, worker_id=worker_id, operator=operator, note=note)
        return ok(data, trace_id=trace_id, status_code=202)
    except ValueError as exc:
        code = str(exc)
        if code == 'job_not_found':
            return fail('job_not_found', '作业不存在', status_code=404, trace_id=trace_id)
        if code == 'worker_id_required':
            return fail('worker_id_required', 'workerId 必填', status_code=400, trace_id=trace_id)
        if code == 'worker_mismatch':
            return fail('worker_mismatch', '当前 worker 无权更新该作业心跳', details={'reason': code}, status_code=409, trace_id=trace_id)
        if code == 'job_not_heartbeatable':
            return fail('job_not_heartbeatable', '当前作业不允许心跳续约', details={'reason': code}, status_code=409, trace_id=trace_id)
        return fail('job_heartbeat_failed', '更新作业心跳失败', details={'reason': code}, status_code=409, trace_id=trace_id)
    except Exception as exc:
        return fail('job_heartbeat_failed', '更新作业心跳失败', details={'reason': str(exc)}, status_code=500, trace_id=trace_id)


@jobs_bp.route('/<job_ref>/release-lease', methods=['POST'])
def release_job_lease_v1(job_ref: str):
    operator, reason, note, trace_id, idempotency_key = _job_command_payload()
    payload = request.get_json(silent=True) or {}
    worker_id = str(payload.get('workerId') or payload.get('worker_id') or '').strip()
    try:
        data = _get_action_queue_service().release_job_lease(job_ref, worker_id=worker_id, operator=operator, reason=reason, note=note, idempotency_key=idempotency_key)
        return ok(data, trace_id=trace_id, status_code=202)
    except ValueError as exc:
        code = str(exc)
        if code == 'job_not_found':
            return fail('job_not_found', '作业不存在', status_code=404, trace_id=trace_id)
        if code == 'worker_id_required':
            return fail('worker_id_required', 'workerId 必填', status_code=400, trace_id=trace_id)
        if code == 'worker_mismatch':
            return fail('worker_mismatch', '当前 worker 无权释放该作业租约', details={'reason': code}, status_code=409, trace_id=trace_id)
        if code == 'job_not_releasable':
            return fail('job_not_releasable', '当前作业不允许释放租约', details={'reason': code}, status_code=409, trace_id=trace_id)
        return fail('job_release_lease_failed', '释放作业租约失败', details={'reason': code}, status_code=409, trace_id=trace_id)
    except Exception as exc:
        return fail('job_release_lease_failed', '释放作业租约失败', details={'reason': str(exc)}, status_code=500, trace_id=trace_id)


@jobs_bp.route('/<job_ref>/mark-succeeded', methods=['POST'])
def mark_job_succeeded_v1(job_ref: str):
    operator, _reason, note, trace_id, idempotency_key = _job_command_payload()
    payload = request.get_json(silent=True) or {}
    worker_id = str(payload.get('workerId') or payload.get('worker_id') or '').strip()
    external_ref = str(payload.get('externalRef') or '').strip() or None
    try:
        data = _get_action_queue_service().mark_job_succeeded(job_ref, worker_id=worker_id, operator=operator, external_ref=external_ref, note=note, idempotency_key=idempotency_key)
        return ok(data, trace_id=trace_id, status_code=202)
    except ValueError as exc:
        code = str(exc)
        if code == 'job_not_found':
            return fail('job_not_found', '作业不存在', status_code=404, trace_id=trace_id)
        if code == 'worker_id_required':
            return fail('worker_id_required', 'workerId 必填', status_code=400, trace_id=trace_id)
        if code == 'worker_mismatch':
            return fail('worker_mismatch', '当前 worker 无权完成该作业', details={'reason': code}, status_code=409, trace_id=trace_id)
        if code == 'job_not_completable':
            return fail('job_not_completable', '当前作业不允许标记完成', details={'reason': code}, status_code=409, trace_id=trace_id)
        return fail('job_mark_succeeded_failed', '标记作业完成失败', details={'reason': code}, status_code=409, trace_id=trace_id)
    except Exception as exc:
        return fail('job_mark_succeeded_failed', '标记作业完成失败', details={'reason': str(exc)}, status_code=500, trace_id=trace_id)


@jobs_bp.route('/<job_ref>/mark-failed', methods=['POST'])
def mark_job_failed_v1(job_ref: str):
    operator, reason, note, trace_id, idempotency_key = _job_command_payload()
    payload = request.get_json(silent=True) or {}
    worker_id = str(payload.get('workerId') or payload.get('worker_id') or '').strip()
    normalized_reason = reason or str(payload.get('reason') or '').strip() or 'worker_failed'
    try:
        data = _get_action_queue_service().mark_job_failed(job_ref, worker_id=worker_id, operator=operator, reason=normalized_reason, note=note, idempotency_key=idempotency_key)
        return ok(data, trace_id=trace_id, status_code=202)
    except ValueError as exc:
        code = str(exc)
        if code == 'job_not_found':
            return fail('job_not_found', '作业不存在', status_code=404, trace_id=trace_id)
        if code == 'worker_id_required':
            return fail('worker_id_required', 'workerId 必填', status_code=400, trace_id=trace_id)
        if code == 'worker_mismatch':
            return fail('worker_mismatch', '当前 worker 无权标记该作业失败', details={'reason': code}, status_code=409, trace_id=trace_id)
        if code == 'job_not_failurable':
            return fail('job_not_failurable', '当前作业不允许标记失败', details={'reason': code}, status_code=409, trace_id=trace_id)
        return fail('job_mark_failed_failed', '标记作业失败', details={'reason': code}, status_code=409, trace_id=trace_id)
    except Exception as exc:
        return fail('job_mark_failed_failed', '标记作业失败', details={'reason': str(exc)}, status_code=500, trace_id=trace_id)


@jobs_bp.route('/<job_ref>/retry', methods=['POST'])
def retry_job_v1(job_ref: str):
    operator, reason, note, trace_id, idempotency_key = _job_command_payload()
    try:
        payload = _get_action_queue_service().retry_job(job_ref, operator=operator, reason=reason, note=note, idempotency_key=idempotency_key)
        return ok(payload, trace_id=trace_id, status_code=202)
    except ValueError as exc:
        code = str(exc)
        if code == 'job_not_found':
            return fail('job_not_found', '作业不存在', status_code=404, trace_id=trace_id)
        if code == 'job_not_retryable':
            return fail('job_not_retryable', '当前作业不允许重试', details={'reason': code}, status_code=409, trace_id=trace_id)
        return fail('job_retry_failed', '发起作业重试失败', details={'reason': code}, status_code=409, trace_id=trace_id)
    except Exception as exc:
        return fail('job_retry_failed', '发起作业重试失败', details={'reason': str(exc)}, status_code=500, trace_id=trace_id)


@jobs_bp.route('/<job_ref>/redrive', methods=['POST'])
def redrive_job_v1(job_ref: str):
    operator, reason, note, trace_id, idempotency_key = _job_command_payload()
    try:
        payload = _get_action_queue_service().redrive_job(job_ref, operator=operator, reason=reason, note=note, idempotency_key=idempotency_key)
        return ok(payload, trace_id=trace_id, status_code=202)
    except ValueError as exc:
        code = str(exc)
        if code == 'job_not_found':
            return fail('job_not_found', '作业不存在', status_code=404, trace_id=trace_id)
        if code == 'job_not_redriveable':
            return fail('job_not_redriveable', '当前作业不允许重新驱动', details={'reason': code}, status_code=409, trace_id=trace_id)
        return fail('job_redrive_failed', '发起作业重新驱动失败', details={'reason': code}, status_code=409, trace_id=trace_id)
    except Exception as exc:
        return fail('job_redrive_failed', '发起作业重新驱动失败', details={'reason': str(exc)}, status_code=500, trace_id=trace_id)


@jobs_bp.route('/<job_ref>/dead-letter', methods=['POST'])
def dead_letter_job_v1(job_ref: str):
    operator, reason, note, trace_id, idempotency_key = _job_command_payload()
    try:
        payload = _get_action_queue_service().mark_dead_letter(job_ref, operator=operator, reason=reason or 'manual_dead_letter', note=note, idempotency_key=idempotency_key)
        return ok(payload, trace_id=trace_id, status_code=202)
    except ValueError as exc:
        code = str(exc)
        if code == 'job_not_found':
            return fail('job_not_found', '作业不存在', status_code=404, trace_id=trace_id)
        if code == 'job_not_dead_letterable':
            return fail('job_not_dead_letterable', '当前作业不允许进入死信', details={'reason': code}, status_code=409, trace_id=trace_id)
        return fail('job_dead_letter_failed', '写入死信作业失败', details={'reason': code}, status_code=409, trace_id=trace_id)
    except Exception as exc:
        return fail('job_dead_letter_failed', '写入死信作业失败', details={'reason': str(exc)}, status_code=500, trace_id=trace_id)
