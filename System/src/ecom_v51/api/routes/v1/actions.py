from __future__ import annotations

from flask import Blueprint, request

from ecom_v51.services.action_approval_service import ActionApprovalService
from ecom_v51.services.action_audit_service import ActionAuditService
from ecom_v51.services.action_callback_service import ActionCallbackService
from ecom_v51.services.action_compensation_service import ActionCompensationService
from ecom_v51.services.action_delivery_service import ActionDeliveryService
from ecom_v51.services.action_entry_service import ActionEntryService
from ecom_v51.services.action_workspace_service import ActionWorkspaceService
from ecom_v51.services.action_automation_service import ActionAutomationService

from .common import fail, get_trace_id, ok


actions_bp = Blueprint('api_v1_actions', __name__)

_action_entry_service = ActionEntryService()
_action_approval_service = ActionApprovalService()
_action_delivery_service = ActionDeliveryService()
_action_callback_service = ActionCallbackService()
_action_compensation_service = ActionCompensationService()
_action_audit_service = ActionAuditService()
_action_workspace_service = ActionWorkspaceService()
_action_automation_service = ActionAutomationService()

# Backward-compatible module-level aliases for older contract tests.
action_entry_service = _action_entry_service
action_approval_service = _action_approval_service
action_delivery_service = _action_delivery_service
action_callback_service = _action_callback_service
action_compensation_service = _action_compensation_service
action_audit_service = _action_audit_service
action_workspace_service = _action_workspace_service
action_automation_service = _action_automation_service


def _get_action_entry_service() -> ActionEntryService:
    return action_entry_service


def _get_action_approval_service() -> ActionApprovalService:
    return action_approval_service


def _get_action_delivery_service() -> ActionDeliveryService:
    return action_delivery_service


def _get_action_callback_service() -> ActionCallbackService:
    return action_callback_service


def _get_action_compensation_service() -> ActionCompensationService:
    return action_compensation_service


def _get_action_audit_service() -> ActionAuditService:
    return action_audit_service


def _get_action_workspace_service() -> ActionWorkspaceService:
    return action_workspace_service


def _get_action_automation_service() -> ActionAutomationService:
    return action_automation_service


@actions_bp.route('/registry', methods=['GET'])
def get_action_registry_v1():
    try:
        return ok(_get_action_entry_service().list_action_registry())
    except Exception as exc:
        return fail('action_registry_failed', '读取动作注册表失败', details={'reason': str(exc)}, status_code=500)


@actions_bp.route('/requests', methods=['GET', 'POST'])
def action_requests_v1():
    try:
        if request.method == 'POST':
            payload = request.get_json(silent=True) or {}
            if payload.get('actionType') or payload.get('snapshotId'):
                item = _get_action_entry_service().create_action_request(
                    batch_ref=str(payload.get('batchRef') or '').strip(),
                    snapshot_id=int(payload.get('snapshotId') or 0),
                    action_type=str(payload.get('actionType') or '').strip(),
                    canonical_sku=str(payload.get('canonicalSku') or '').strip() or None,
                    operator=str(payload.get('operator') or payload.get('requestedBy') or 'system').strip() or 'system',
                    note=str(payload.get('note') or '').strip() or None,
                )
            else:
                item = _get_action_entry_service().create_request(payload)
            return ok(item, status_code=201)

        batch_ref = str(request.args.get('batchRef') or '').strip() or None
        limit = request.args.get('limit', default=20, type=int)
        if batch_ref:
            return ok(_get_action_entry_service().list_action_requests(batch_ref=batch_ref, limit=limit))
        status = str(request.args.get('status') or '').strip() or None
        action_code = str(request.args.get('actionCode') or '').strip() or None
        return ok(_get_action_entry_service().list_requests(status=status, action_code=action_code, limit=limit))
    except ValueError as exc:
        code = str(exc)
        if code == 'action_code_required':
            return fail('action_code_required', 'actionCode 必填', status_code=400)
        if code == 'unsupported_action_type':
            return fail('unsupported_action_type', '不支持的动作类型', status_code=400)
        return fail('action_request_invalid', '动作请求参数非法', details={'reason': code}, status_code=400)
    except Exception as exc:
        return fail('action_request_failed', '读取或创建动作请求失败', details={'reason': str(exc)}, status_code=500)


@actions_bp.route('/requests/<request_id>', methods=['GET'])
def get_action_request_detail_v1(request_id: str):
    try:
        item = _get_action_entry_service().get_action_request_detail(request_id)
        if not item:
            item = _get_action_entry_service().get_request(request_id)
        if not item:
            return fail('request_not_found', '动作请求不存在', status_code=404)
        return ok(item)
    except Exception as exc:
        return fail('action_request_detail_failed', '读取动作请求详情失败', details={'reason': str(exc)}, status_code=500)



def _approval_status_code(operation: str, item: dict) -> int:
    # Compatibility split:
    # - legacy P5.1 monkeypatched contract returns actionRequestId + approvalContractVersion and expects 200
    # - live P5.2 request flow returns requestId and expects submit/approve -> 202
    if isinstance(item, dict) and item.get('requestId') and operation in {'submit', 'approve'}:
        return 202
    if isinstance(item, dict) and item.get('approvalContractVersion'):
        return 200
    if operation in {'submit', 'approve'}:
        return 202
    return 200

def _approval_payload() -> tuple[str, str | None]:
    payload = request.get_json(silent=True) or {}
    operator = str(payload.get('operator') or 'system').strip() or 'system'
    note = str(payload.get('note') or '').strip() or None
    return operator, note


@actions_bp.route('/requests/<request_id>/submit', methods=['POST'])
def submit_action_request_v1(request_id: str):
    operator, note = _approval_payload()
    try:
        item = _get_action_entry_service().transition_action_request(request_id=request_id, operation='submit', operator=operator, note=note)
        return ok(item, status_code=_approval_status_code('submit', item))
    except ValueError as exc:
        code = str(exc)
        if code == 'request_not_found':
            return fail('request_not_found', '动作请求不存在', status_code=404)
        return fail('invalid_request_status', '当前状态不允许提交审批', details={'reason': code}, status_code=409)


@actions_bp.route('/requests/<request_id>/approve', methods=['POST'])
def approve_action_request_v1(request_id: str):
    operator, note = _approval_payload()
    try:
        item = _get_action_entry_service().transition_action_request(request_id=request_id, operation='approve', operator=operator, note=note)
        return ok(item, status_code=_approval_status_code('approve', item))
    except ValueError as exc:
        code = str(exc)
        if code == 'request_not_found':
            return fail('request_not_found', '动作请求不存在', status_code=404)
        return fail('invalid_request_status', '当前状态不允许审批通过', details={'reason': code}, status_code=409)


@actions_bp.route('/requests/<request_id>/reject', methods=['POST'])
def reject_action_request_v1(request_id: str):
    operator, note = _approval_payload()
    try:
        item = _get_action_entry_service().transition_action_request(request_id=request_id, operation='reject', operator=operator, note=note)
        return ok(item, status_code=_approval_status_code('reject', item))
    except ValueError as exc:
        code = str(exc)
        if code == 'request_not_found':
            return fail('request_not_found', '动作请求不存在', status_code=404)
        return fail('invalid_request_status', '当前状态不允许驳回', details={'reason': code}, status_code=409)


@actions_bp.route('/requests/<request_id>/cancel', methods=['POST'])
def cancel_action_request_v1(request_id: str):
    operator, note = _approval_payload()
    try:
        item = _get_action_entry_service().transition_action_request(request_id=request_id, operation='cancel', operator=operator, note=note)
        return ok(item, status_code=_approval_status_code('cancel', item))
    except ValueError as exc:
        code = str(exc)
        if code == 'request_not_found':
            return fail('request_not_found', '动作请求不存在', status_code=404)
        return fail('invalid_request_status', '当前状态不允许取消', details={'reason': code}, status_code=409)


@actions_bp.route('/requests/<request_id>/approval-history', methods=['GET'])
def get_action_request_approval_history_v1(request_id: str):
    try:
        return ok(_get_action_entry_service().get_action_approval_history(request_id))
    except ValueError as exc:
        code = str(exc)
        if code == 'request_not_found':
            return fail('request_not_found', '动作请求不存在', status_code=404)
        return fail('approval_history_failed', '读取审批历史失败', details={'reason': code}, status_code=409)
    except Exception as exc:
        return fail('approval_history_failed', '读取审批历史失败', details={'reason': str(exc)}, status_code=500)


@actions_bp.route('/requests/<request_id>/push', methods=['POST'])
def push_action_request_v1(request_id: str):
    trace_id = get_trace_id()
    payload = request.get_json(silent=True) or {}
    operator = str(payload.get('operator') or 'system').strip() or 'system'
    channel = str(payload.get('channel') or '').strip() or None
    note = str(payload.get('note') or '').strip() or None
    idempotency_key = str(request.headers.get('Idempotency-Key') or request.headers.get('IdempotencyKey') or payload.get('idempotencyKey') or '').strip() or None
    try:
        data = _get_action_delivery_service().push(
            request_id,
            operator=operator,
            channel=channel,
            note=note,
            trace_id=trace_id,
            idempotency_key=idempotency_key,
        )
        return ok(data, trace_id=trace_id, status_code=202)
    except ValueError as exc:
        code = str(exc)
        if code == 'request_not_found':
            return fail('request_not_found', '动作请求不存在', status_code=404, trace_id=trace_id)
        if code == 'request_not_approved':
            return fail('request_not_approved', '仅已批准请求允许执行推送', status_code=409, trace_id=trace_id)
        return fail('action_push_failed', '执行动作推送失败', details={'reason': code}, status_code=409, trace_id=trace_id)
    except Exception as exc:
        return fail('action_push_failed', '执行动作推送失败', details={'reason': str(exc)}, status_code=500, trace_id=trace_id)




@actions_bp.route('/requests/<request_id>/jobs', methods=['GET'])
def list_action_request_jobs_v1(request_id: str):
    try:
        return ok(_get_action_delivery_service().list_request_jobs(request_id))
    except ValueError as exc:
        code = str(exc)
        if code == 'request_not_found':
            return fail('request_not_found', '动作请求不存在', status_code=404)
        return fail('request_jobs_failed', '读取动作作业列表失败', details={'reason': code}, status_code=409)
    except Exception as exc:
        return fail('request_jobs_failed', '读取动作作业列表失败', details={'reason': str(exc)}, status_code=500)


@actions_bp.route('/requests/<request_id>/recovery', methods=['GET'])
def get_action_request_recovery_v1(request_id: str):
    try:
        return ok(_get_action_delivery_service().get_request_recovery(request_id))
    except ValueError as exc:
        code = str(exc)
        if code == 'request_not_found':
            return fail('request_not_found', '动作请求不存在', status_code=404)
        return fail('request_recovery_failed', '读取动作恢复视图失败', details={'reason': code}, status_code=409)
    except Exception as exc:
        return fail('request_recovery_failed', '读取动作恢复视图失败', details={'reason': str(exc)}, status_code=500)

@actions_bp.route('/requests/<request_id>/delivery', methods=['GET'])
def get_action_request_delivery_v1(request_id: str):
    try:
        return ok(_get_action_delivery_service().get_delivery(request_id))
    except ValueError as exc:
        code = str(exc)
        if code == 'request_not_found':
            return fail('request_not_found', '动作请求不存在', status_code=404)
        return fail('delivery_detail_failed', '读取动作投递详情失败', details={'reason': code}, status_code=409)
    except Exception as exc:
        return fail('delivery_detail_failed', '读取动作投递详情失败', details={'reason': str(exc)}, status_code=500)


@actions_bp.route('/requests/<request_id>/delivery-history', methods=['GET'])
def get_action_request_delivery_history_v1(request_id: str):
    try:
        return ok(_get_action_delivery_service().get_delivery_history(request_id))
    except ValueError as exc:
        code = str(exc)
        if code == 'request_not_found':
            return fail('request_not_found', '动作请求不存在', status_code=404)
        return fail('delivery_history_failed', '读取动作投递历史失败', details={'reason': code}, status_code=409)
    except Exception as exc:
        return fail('delivery_history_failed', '读取动作投递历史失败', details={'reason': str(exc)}, status_code=500)


@actions_bp.route('/requests/<request_id>/callback', methods=['POST'])
def ingest_action_request_callback_v1(request_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        data = _get_action_callback_service().ingest_callback(
            request_id,
            event_type=str(payload.get('eventType') or '').strip(),
            provider_status=str(payload.get('providerStatus') or '').strip(),
            external_ref=str(payload.get('externalRef') or '').strip() or None,
            payload=payload.get('payload') or {},
            received_at=str(payload.get('receivedAt') or '').strip() or None,
        )
        return ok(data, status_code=202)
    except ValueError as exc:
        code = str(exc)
        if code == 'request_not_found':
            return fail('request_not_found', '动作请求不存在', status_code=404)
        if code == 'delivery_not_found':
            return fail('delivery_not_found', '当前请求尚未产生投递记录', status_code=409)
        return fail('callback_ingest_failed', '写入回调事件失败', details={'reason': code}, status_code=409)
    except Exception as exc:
        return fail('callback_ingest_failed', '写入回调事件失败', details={'reason': str(exc)}, status_code=500)


@actions_bp.route('/requests/<request_id>/callback-state', methods=['GET'])
def get_action_request_callback_state_v1(request_id: str):
    try:
        return ok(_get_action_callback_service().get_callback_state(request_id))
    except ValueError as exc:
        code = str(exc)
        if code == 'request_not_found':
            return fail('request_not_found', '动作请求不存在', status_code=404)
        if code == 'delivery_not_found':
            return fail('delivery_not_found', '当前请求尚未产生投递记录', status_code=409)
        return fail('callback_state_failed', '读取回调状态失败', details={'reason': code}, status_code=409)
    except Exception as exc:
        return fail('callback_state_failed', '读取回调状态失败', details={'reason': str(exc)}, status_code=500)


@actions_bp.route('/requests/<request_id>/callback-events', methods=['GET'])
def get_action_request_callback_events_v1(request_id: str):
    try:
        return ok(_get_action_callback_service().get_callback_events(request_id))
    except ValueError as exc:
        code = str(exc)
        if code == 'request_not_found':
            return fail('request_not_found', '动作请求不存在', status_code=404)
        if code == 'delivery_not_found':
            return fail('delivery_not_found', '当前请求尚未产生投递记录', status_code=409)
        return fail('callback_events_failed', '读取回调事件失败', details={'reason': code}, status_code=409)
    except Exception as exc:
        return fail('callback_events_failed', '读取回调事件失败', details={'reason': str(exc)}, status_code=500)

@actions_bp.route('/requests/<request_id>/compensation/evaluate', methods=['POST'])
def evaluate_action_request_compensation_v1(request_id: str):
    payload = request.get_json(silent=True) or {}
    operator = str(payload.get('operator') or 'system').strip() or 'system'
    reason_override = str(payload.get('reasonOverride') or '').strip() or None
    note = str(payload.get('note') or '').strip() or None
    try:
        data = _get_action_compensation_service().evaluate_compensation(
            request_id,
            operator=operator,
            reason_override=reason_override,
            note=note,
        )
        return ok(data, status_code=202)
    except ValueError as exc:
        code = str(exc)
        if code == 'request_not_found':
            return fail('request_not_found', '动作请求不存在', status_code=404)
        if code == 'delivery_not_found':
            return fail('delivery_not_found', '当前请求尚未产生投递记录', status_code=409)
        if code == 'callback_not_found':
            return fail('callback_not_found', '当前请求尚未产生回调状态', status_code=409)
        return fail('compensation_evaluate_failed', '执行补偿评估失败', details={'reason': code}, status_code=409)
    except Exception as exc:
        return fail('compensation_evaluate_failed', '执行补偿评估失败', details={'reason': str(exc)}, status_code=500)


@actions_bp.route('/requests/<request_id>/compensation-state', methods=['GET'])
def get_action_request_compensation_state_v1(request_id: str):
    try:
        return ok(_get_action_compensation_service().get_compensation_state(request_id))
    except ValueError as exc:
        code = str(exc)
        if code == 'request_not_found':
            return fail('request_not_found', '动作请求不存在', status_code=404)
        if code == 'delivery_not_found':
            return fail('delivery_not_found', '当前请求尚未产生投递记录', status_code=409)
        if code == 'callback_not_found':
            return fail('callback_not_found', '当前请求尚未产生回调状态', status_code=409)
        return fail('compensation_state_failed', '读取补偿状态失败', details={'reason': code}, status_code=409)
    except Exception as exc:
        return fail('compensation_state_failed', '读取补偿状态失败', details={'reason': str(exc)}, status_code=500)


@actions_bp.route('/requests/<request_id>/compensation-history', methods=['GET'])
def get_action_request_compensation_history_v1(request_id: str):
    try:
        return ok(_get_action_compensation_service().get_compensation_history(request_id))
    except ValueError as exc:
        code = str(exc)
        if code == 'request_not_found':
            return fail('request_not_found', '动作请求不存在', status_code=404)
        if code == 'delivery_not_found':
            return fail('delivery_not_found', '当前请求尚未产生投递记录', status_code=409)
        if code == 'callback_not_found':
            return fail('callback_not_found', '当前请求尚未产生回调状态', status_code=409)
        return fail('compensation_history_failed', '读取补偿历史失败', details={'reason': code}, status_code=409)
    except Exception as exc:
        return fail('compensation_history_failed', '读取补偿历史失败', details={'reason': str(exc)}, status_code=500)


@actions_bp.route('/requests/<request_id>/audit-trace', methods=['GET'])
def get_action_request_audit_trace_v1(request_id: str):
    try:
        return ok(_get_action_audit_service().get_audit_trace(request_id))
    except ValueError as exc:
        code = str(exc)
        if code == 'request_not_found':
            return fail('request_not_found', '动作请求不存在', status_code=404)
        return fail('audit_trace_failed', '读取动作审计轨迹失败', details={'reason': code}, status_code=409)
    except Exception as exc:
        return fail('audit_trace_failed', '读取动作审计轨迹失败', details={'reason': str(exc)}, status_code=500)




@actions_bp.route('/jobs/summary', methods=['GET'])
def get_action_jobs_summary_v1():
    try:
        request_id = str(request.args.get('requestId') or '').strip() or None
        batch_ref = str(request.args.get('batchRef') or '').strip() or None
        action_code = str(request.args.get('actionCode') or '').strip() or None
        status = str(request.args.get('status') or '').strip() or None
        limit = request.args.get('limit', default=20, type=int)
        return ok(
            _get_action_delivery_service().queue_service.list_jobs_summary(
                request_id=request_id,
                batch_ref=batch_ref,
                action_code=action_code,
                status=status,
                limit=limit,
            )
        )
    except Exception as exc:
        return fail('action_job_summary_failed', '读取动作作业汇总失败', details={'reason': str(exc)}, status_code=500)


@actions_bp.route('/jobs/dashboard', methods=['GET'])
def get_action_jobs_dashboard_v1():
    try:
        batch_ref = str(request.args.get('batchRef') or '').strip() or None
        limit = request.args.get('limit', default=10, type=int)
        return ok(_get_action_delivery_service().queue_service.get_jobs_dashboard(batch_ref=batch_ref, limit=limit))
    except Exception as exc:
        return fail('action_job_dashboard_failed', '读取动作作业看板失败', details={'reason': str(exc)}, status_code=500)


@actions_bp.route('/jobs/metrics', methods=['GET'])
def get_action_jobs_metrics_v1():
    try:
        request_id = str(request.args.get('requestId') or '').strip() or None
        batch_ref = str(request.args.get('batchRef') or '').strip() or None
        action_code = str(request.args.get('actionCode') or '').strip() or None
        status = str(request.args.get('status') or '').strip() or None
        limit = request.args.get('limit', default=20, type=int)
        return ok(
            _get_action_delivery_service().queue_service.get_jobs_metrics(
                request_id=request_id,
                batch_ref=batch_ref,
                action_code=action_code,
                status=status,
                limit=limit,
            )
        )
    except Exception as exc:
        return fail('action_job_metrics_failed', '读取动作作业指标失败', details={'reason': str(exc)}, status_code=500)


@actions_bp.route('/jobs/failure-buckets', methods=['GET'])
def get_action_jobs_failure_buckets_v1():
    try:
        request_id = str(request.args.get('requestId') or '').strip() or None
        batch_ref = str(request.args.get('batchRef') or '').strip() or None
        action_code = str(request.args.get('actionCode') or '').strip() or None
        limit = request.args.get('limit', default=20, type=int)
        return ok(
            _get_action_delivery_service().queue_service.get_failure_buckets(
                request_id=request_id,
                batch_ref=batch_ref,
                action_code=action_code,
                limit=limit,
            )
        )
    except Exception as exc:
        return fail('action_job_failure_buckets_failed', '读取动作作业失败桶失败', details={'reason': str(exc)}, status_code=500)


@actions_bp.route('/jobs/<job_id>/audit', methods=['GET'])
def get_action_job_audit_v1(job_id: str):
    try:
        return ok(_get_action_delivery_service().queue_service.get_job_audit(job_id))
    except ValueError as exc:
        code = str(exc)
        if code == 'job_not_found':
            return fail('job_not_found', '作业不存在', status_code=404)
        return fail('action_job_audit_failed', '读取动作作业审计视图失败', details={'reason': code}, status_code=409)
    except Exception as exc:
        return fail('action_job_audit_failed', '读取动作作业审计视图失败', details={'reason': str(exc)}, status_code=500)


@actions_bp.route('/requests/<request_id>/audit', methods=['GET'])
def get_action_request_audit_v1(request_id: str):
    try:
        return ok(_get_action_delivery_service().queue_service.get_request_audit(request_id))
    except ValueError as exc:
        code = str(exc)
        if code == 'request_not_found':
            return fail('request_not_found', '动作请求不存在', status_code=404)
        return fail('action_request_audit_failed', '读取动作请求审计视图失败', details={'reason': code}, status_code=409)
    except Exception as exc:
        return fail('action_request_audit_failed', '读取动作请求审计视图失败', details={'reason': str(exc)}, status_code=500)


@actions_bp.route('/batches/<batch_ref>/audit', methods=['GET'])
def get_action_batch_audit_v1(batch_ref: str):
    try:
        return ok(_get_action_delivery_service().queue_service.get_batch_audit(batch_ref))
    except ValueError as exc:
        code = str(exc)
        if code == 'batch_not_found':
            return fail('batch_not_found', '批次不存在', status_code=404)
        return fail('action_batch_audit_failed', '读取动作批次审计视图失败', details={'reason': code}, status_code=409)
    except Exception as exc:
        return fail('action_batch_audit_failed', '读取动作批次审计视图失败', details={'reason': str(exc)}, status_code=500)


@actions_bp.route('/batches/<batch_ref>/queue-health', methods=['GET'])
def get_action_batch_queue_health_v1(batch_ref: str):
    try:
        return ok(_get_action_delivery_service().queue_service.get_batch_queue_health(batch_ref))
    except ValueError as exc:
        code = str(exc)
        if code == 'batch_not_found':
            return fail('batch_not_found', '批次不存在', status_code=404)
        return fail('batch_queue_health_failed', '读取批次队列健康度失败', details={'reason': code}, status_code=409)
    except Exception as exc:
        return fail('batch_queue_health_failed', '读取批次队列健康度失败', details={'reason': str(exc)}, status_code=500)

@actions_bp.route('/worker/overview', methods=['GET'])
def get_action_worker_overview_v1():
    try:
        batch_ref = str(request.args.get('batchRef') or '').strip() or None
        limit = request.args.get('limit', default=10, type=int)
        return ok(_get_action_delivery_service().queue_service.get_worker_overview(batch_ref=batch_ref, limit=limit))
    except Exception as exc:
        return fail('action_worker_overview_failed', '读取动作队列 worker 视图失败', details={'reason': str(exc)}, status_code=500)


@actions_bp.route('/worker/claim-next', methods=['POST'])
def claim_action_worker_next_job_v1():
    trace_id = get_trace_id()
    payload = request.get_json(silent=True) or {}
    worker_id = str(payload.get('workerId') or payload.get('worker_id') or '').strip()
    operator = str(payload.get('operator') or worker_id or 'worker').strip() or 'worker'
    batch_ref = str(payload.get('batchRef') or '').strip() or None
    note = str(payload.get('note') or '').strip() or None
    try:
        data = _get_action_delivery_service().queue_service.claim_next_job(worker_id=worker_id, operator=operator, batch_ref=batch_ref, note=note)
        return ok(data, trace_id=trace_id, status_code=202)
    except ValueError as exc:
        code = str(exc)
        if code == 'worker_id_required':
            return fail('worker_id_required', 'workerId 必填', status_code=400, trace_id=trace_id)
        if code == 'no_job_available':
            return fail('no_job_available', '当前没有可领取作业', status_code=409, trace_id=trace_id)
        return fail('action_worker_claim_failed', '领取下一个动作作业失败', details={'reason': code}, status_code=409, trace_id=trace_id)
    except Exception as exc:
        return fail('action_worker_claim_failed', '领取下一个动作作业失败', details={'reason': str(exc)}, status_code=500, trace_id=trace_id)



@actions_bp.route('/worker/stale-jobs', methods=['GET'])
def get_action_worker_stale_jobs_v1():
    try:
        batch_ref = str(request.args.get('batchRef') or '').strip() or None
        limit = request.args.get('limit', default=10, type=int)
        return ok(_get_action_delivery_service().queue_service.get_worker_stale_jobs(batch_ref=batch_ref, limit=limit))
    except Exception as exc:
        return fail('action_worker_stale_jobs_failed', '读取动作队列 stale jobs 失败', details={'reason': str(exc)}, status_code=500)


@actions_bp.route('/worker/release-stale', methods=['POST'])
def release_action_worker_stale_jobs_v1():
    trace_id = get_trace_id()
    payload = request.get_json(silent=True) or {}
    batch_ref = str(payload.get('batchRef') or '').strip() or None
    worker_id = str(payload.get('workerId') or payload.get('worker_id') or '').strip() or None
    operator = str(payload.get('operator') or 'system').strip() or 'system'
    limit = int(payload.get('limit') or 20)
    reason = str(payload.get('reason') or '').strip() or None
    note = str(payload.get('note') or '').strip() or None
    try:
        data = _get_action_delivery_service().queue_service.release_stale_jobs(batch_ref=batch_ref, worker_id=worker_id, operator=operator, limit=limit, reason=reason, note=note)
        return ok(data, trace_id=trace_id, status_code=202)
    except Exception as exc:
        return fail('action_worker_release_stale_failed', '释放 stale 作业失败', details={'reason': str(exc)}, status_code=500, trace_id=trace_id)


@actions_bp.route('/worker/lease-audit', methods=['GET'])
def get_action_worker_lease_audit_v1():
    try:
        batch_ref = str(request.args.get('batchRef') or '').strip() or None
        worker_id = str(request.args.get('workerId') or '').strip() or None
        event_type = str(request.args.get('eventType') or '').strip() or None
        action_code = str(request.args.get('actionCode') or '').strip() or None
        limit = request.args.get('limit', default=20, type=int)
        return ok(_get_action_delivery_service().queue_service.get_worker_lease_audit(batch_ref=batch_ref, worker_id=worker_id, event_type=event_type, action_code=action_code, limit=limit))
    except Exception as exc:
        return fail('action_worker_lease_audit_failed', '读取动作队列租约审计失败', details={'reason': str(exc)}, status_code=500)


@actions_bp.route('/worker/command-audit', methods=['GET'])
def get_action_worker_command_audit_v1():
    try:
        batch_ref = str(request.args.get('batchRef') or '').strip() or None
        worker_id = str(request.args.get('workerId') or '').strip() or None
        event_type = str(request.args.get('eventType') or '').strip() or None
        action_code = str(request.args.get('actionCode') or '').strip() or None
        limit = request.args.get('limit', default=20, type=int)
        return ok(_get_action_delivery_service().queue_service.get_worker_command_audit(batch_ref=batch_ref, worker_id=worker_id, event_type=event_type, action_code=action_code, limit=limit))
    except Exception as exc:
        return fail('action_worker_command_audit_failed', '读取动作队列命令审计失败', details={'reason': str(exc)}, status_code=500)


@actions_bp.route('/worker/command-audit/<event_id>', methods=['GET'])
def get_action_worker_command_audit_detail_v1(event_id: str):
    try:
        return ok(_get_action_delivery_service().queue_service.get_worker_command_audit_detail(event_id))
    except ValueError as exc:
        code = str(exc)
        if code == 'command_audit_event_not_found':
            return fail('command_audit_event_not_found', '命令审计事件不存在', status_code=404)
        return fail('action_worker_command_audit_detail_failed', '读取动作队列命令审计明细失败', details={'reason': code}, status_code=409)
    except Exception as exc:
        return fail('action_worker_command_audit_detail_failed', '读取动作队列命令审计明细失败', details={'reason': str(exc)}, status_code=500)



@actions_bp.route('/worker/bulk-results', methods=['GET'])
def get_action_worker_bulk_results_v1():
    try:
        batch_ref = str(request.args.get('batchRef') or '').strip() or None
        command = str(request.args.get('command') or '').strip() or None
        worker_id = str(request.args.get('workerId') or '').strip() or None
        action_code = str(request.args.get('actionCode') or '').strip() or None
        result_mode = str(request.args.get('resultMode') or '').strip() or None
        root_bulk_command_id = str(request.args.get('rootBulkCommandId') or '').strip() or None
        reexecute_of = str(request.args.get('reexecuteOf') or '').strip() or None
        parent_bulk_command_id = str(request.args.get('parentBulkCommandId') or '').strip() or None
        has_children = str(request.args.get('hasChildren') or '').strip() or None
        lineage_depth = request.args.get('lineageDepth', default=None, type=int)
        selection = str(request.args.get('selection') or '').strip() or None
        reexecute_command = str(request.args.get('reexecuteCommand') or '').strip() or None
        command_mode = str(request.args.get('commandMode') or '').strip() or None
        source_bulk_command_id = str(request.args.get('sourceBulkCommandId') or '').strip() or None
        offset = request.args.get('offset', default=0, type=int)
        limit = request.args.get('limit', default=20, type=int)
        return ok(_get_action_delivery_service().queue_service.get_bulk_command_history(batch_ref=batch_ref, command=command, worker_id=worker_id, action_code=action_code, result_mode=result_mode, root_bulk_command_id=root_bulk_command_id, reexecute_of=reexecute_of, parent_bulk_command_id=parent_bulk_command_id, has_children=has_children, lineage_depth=lineage_depth, selection=selection, reexecute_command=reexecute_command, command_mode=command_mode, source_bulk_command_id=source_bulk_command_id, offset=offset, limit=limit))
    except Exception as exc:
        return fail('action_worker_bulk_results_failed', '读取动作队列批量命令结果失败', details={'reason': str(exc)}, status_code=500)


@actions_bp.route('/worker/bulk-results/<bulk_command_id>', methods=['GET'])
def get_action_worker_bulk_result_detail_v1(bulk_command_id: str):
    try:
        return ok(_get_action_delivery_service().queue_service.get_bulk_command_detail(bulk_command_id))
    except ValueError as exc:
        code = str(exc)
        if code == 'bulk_command_not_found':
            return fail('bulk_command_not_found', '批量命令结果不存在', status_code=404)
        return fail('action_worker_bulk_result_detail_failed', '读取动作队列批量命令结果明细失败', details={'reason': code}, status_code=409)
    except Exception as exc:
        return fail('action_worker_bulk_result_detail_failed', '读取动作队列批量命令结果明细失败', details={'reason': str(exc)}, status_code=500)


@actions_bp.route('/worker/bulk-results/<bulk_command_id>/related', methods=['GET'])
def get_action_worker_bulk_result_related_v1(bulk_command_id: str):
    try:
        limit = request.args.get('limit', default=20, type=int)
        return ok(_get_action_delivery_service().queue_service.get_bulk_command_related(bulk_command_id, limit=limit))
    except ValueError as exc:
        code = str(exc)
        if code == 'bulk_command_not_found':
            return fail('bulk_command_not_found', '批量命令结果不存在', status_code=404)
        return fail('action_worker_bulk_result_related_failed', '读取动作队列批量命令关联结果失败', details={'reason': code}, status_code=409)
    except Exception as exc:
        return fail('action_worker_bulk_result_related_failed', '读取动作队列批量命令关联结果失败', details={'reason': str(exc)}, status_code=500)


@actions_bp.route('/worker/bulk-results/<bulk_command_id>/timeline', methods=['GET'])
def get_action_worker_bulk_result_timeline_v1(bulk_command_id: str):
    try:
        result_mode = str(request.args.get('resultMode') or '').strip() or None
        event_type = str(request.args.get('eventType') or '').strip() or None
        command = str(request.args.get('command') or '').strip() or None
        action_code = str(request.args.get('actionCode') or '').strip() or None
        lineage_depth = request.args.get('lineageDepth', default=None, type=int)
        command_mode = str(request.args.get('commandMode') or '').strip() or None
        source_bulk_command_id = str(request.args.get('sourceBulkCommandId') or '').strip() or None
        limit = request.args.get('limit', default=20, type=int)
        return ok(_get_action_delivery_service().queue_service.get_bulk_command_timeline(bulk_command_id, result_mode=result_mode, event_type=event_type, command=command, action_code=action_code, lineage_depth=lineage_depth, command_mode=command_mode, source_bulk_command_id=source_bulk_command_id, limit=limit))
    except ValueError as exc:
        code = str(exc)
        if code == 'bulk_command_not_found':
            return fail('bulk_command_not_found', '批量命令结果不存在', status_code=404)
        return fail('action_worker_bulk_result_timeline_failed', '读取批量命令结果时间线失败', details={'reason': code}, status_code=409)
    except Exception as exc:
        return fail('action_worker_bulk_result_timeline_failed', '读取批量命令结果时间线失败', details={'reason': str(exc)}, status_code=500)



@actions_bp.route('/worker/bulk-results/<bulk_command_id>/lineage-summary', methods=['GET'])
def get_action_worker_bulk_result_lineage_summary_v1(bulk_command_id: str):
    try:
        event_type = str(request.args.get('eventType') or '').strip() or None
        action_code = str(request.args.get('actionCode') or '').strip() or None
        lineage_depth = request.args.get('lineageDepth', default=None, type=int)
        command_mode = str(request.args.get('commandMode') or '').strip() or None
        source_bulk_command_id = str(request.args.get('sourceBulkCommandId') or '').strip() or None
        selection = str(request.args.get('selection') or '').strip() or None
        reexecute_command = str(request.args.get('reexecuteCommand') or '').strip() or None
        limit = request.args.get('limit', default=20, type=int)
        return ok(_get_action_delivery_service().queue_service.get_bulk_command_lineage_summary(bulk_command_id, event_type=event_type, action_code=action_code, lineage_depth=lineage_depth, command_mode=command_mode, source_bulk_command_id=source_bulk_command_id, selection=selection, reexecute_command=reexecute_command, limit=limit))
    except ValueError as exc:
        code = str(exc)
        if code == 'bulk_command_not_found':
            return fail('bulk_command_not_found', '批量命令结果不存在', status_code=404)
        return fail('action_worker_bulk_result_lineage_summary_failed', '读取批量命令 lineage 汇总失败', details={'reason': code}, status_code=409)
    except Exception as exc:
        return fail('action_worker_bulk_result_lineage_summary_failed', '读取批量命令 lineage 汇总失败', details={'reason': str(exc)}, status_code=500)


@actions_bp.route('/worker/bulk-results/<bulk_command_id>/re-execute', methods=['POST'])
def reexecute_action_worker_bulk_result_v1(bulk_command_id: str):
    trace_id = get_trace_id()
    payload = request.get_json(silent=True) or {}
    selection = str(payload.get('selection') or 'failed').strip() or 'failed'
    command = str(payload.get('command') or '').strip() or None
    operator = str(payload.get('operator') or 'system').strip() or 'system'
    worker_id = str(payload.get('workerId') or payload.get('worker_id') or '').strip() or None
    reason = str(payload.get('reason') or '').strip() or None
    note = str(payload.get('note') or '').strip() or None
    external_ref = str(payload.get('externalRef') or '').strip() or None
    try:
        data = _get_action_delivery_service().queue_service.reexecute_bulk_command(
            bulk_command_id,
            selection=selection,
            command=command,
            operator=operator,
            worker_id=worker_id,
            reason=reason,
            note=note,
            external_ref=external_ref,
        )
        return ok(data, trace_id=trace_id, status_code=202)
    except ValueError as exc:
        code = str(exc)
        if code == 'bulk_command_not_found':
            return fail('bulk_command_not_found', '批量命令结果不存在', status_code=404, trace_id=trace_id)
        if code == 'unsupported_bulk_selection':
            return fail('unsupported_bulk_selection', '不支持的批量历史重放选择', status_code=400, trace_id=trace_id)
        if code == 'bulk_command_no_jobs_to_reexecute':
            return fail('bulk_command_no_jobs_to_reexecute', '当前批量历史没有可再执行作业', status_code=409, trace_id=trace_id)
        if code == 'unsupported_bulk_command':
            return fail('unsupported_bulk_command', '不支持的批量命令', status_code=400, trace_id=trace_id)
        return fail('action_worker_bulk_result_reexecute_failed', '重新执行批量命令失败', details={'reason': code}, status_code=409, trace_id=trace_id)
    except Exception as exc:
        return fail('action_worker_bulk_result_reexecute_failed', '重新执行批量命令失败', details={'reason': str(exc)}, status_code=500, trace_id=trace_id)


@actions_bp.route('/worker/bulk-results/<bulk_command_id>/lineage-command', methods=['POST'])
def reexecute_action_worker_bulk_result_lineage_v1(bulk_command_id: str):
    trace_id = get_trace_id()
    payload = request.get_json(silent=True) or {}
    selection = str(payload.get('selection') or 'failed').strip() or 'failed'
    command = str(payload.get('command') or '').strip() or None
    scope = str(payload.get('scope') or 'entire_lineage').strip() or 'entire_lineage'
    operator = str(payload.get('operator') or 'system').strip() or 'system'
    worker_id = str(payload.get('workerId') or payload.get('worker_id') or '').strip() or None
    reason = str(payload.get('reason') or '').strip() or None
    note = str(payload.get('note') or '').strip() or None
    external_ref = str(payload.get('externalRef') or '').strip() or None
    try:
        data = _get_action_delivery_service().queue_service.reexecute_bulk_command_lineage(
            bulk_command_id,
            selection=selection,
            command=command,
            scope=scope,
            operator=operator,
            worker_id=worker_id,
            reason=reason,
            note=note,
            external_ref=external_ref,
        )
        return ok(data, trace_id=trace_id, status_code=202)
    except ValueError as exc:
        code = str(exc)
        if code == 'bulk_command_not_found':
            return fail('bulk_command_not_found', '批量命令结果不存在', status_code=404, trace_id=trace_id)
        if code == 'unsupported_bulk_selection':
            return fail('unsupported_bulk_selection', '不支持的批量历史重放选择', status_code=400, trace_id=trace_id)
        if code == 'unsupported_lineage_scope':
            return fail('unsupported_lineage_scope', '不支持的 lineage 重放范围', status_code=400, trace_id=trace_id)
        if code == 'bulk_command_no_jobs_to_reexecute':
            return fail('bulk_command_no_jobs_to_reexecute', '当前 lineage 没有可再执行作业', status_code=409, trace_id=trace_id)
        if code == 'unsupported_bulk_command':
            return fail('unsupported_bulk_command', '不支持的批量命令', status_code=400, trace_id=trace_id)
        return fail('action_worker_bulk_result_lineage_reexecute_failed', '重新执行 lineage 批量命令失败', details={'reason': code}, status_code=409, trace_id=trace_id)
    except Exception as exc:
        return fail('action_worker_bulk_result_lineage_reexecute_failed', '重新执行 lineage 批量命令失败', details={'reason': str(exc)}, status_code=500, trace_id=trace_id)


@actions_bp.route('/worker/bulk-command', methods=['POST'])
def execute_action_worker_bulk_command_v1():
    trace_id = get_trace_id()
    payload = request.get_json(silent=True) or {}
    command = str(payload.get('command') or '').strip()
    job_ids = payload.get('jobIds') if isinstance(payload.get('jobIds'), list) else []
    operator = str(payload.get('operator') or 'system').strip() or 'system'
    worker_id = str(payload.get('workerId') or payload.get('worker_id') or '').strip() or None
    reason = str(payload.get('reason') or '').strip() or None
    note = str(payload.get('note') or '').strip() or None
    external_ref = str(payload.get('externalRef') or '').strip() or None
    try:
        data = _get_action_delivery_service().queue_service.execute_bulk_command(
            command=command,
            job_ids=job_ids,
            operator=operator,
            worker_id=worker_id,
            reason=reason,
            note=note,
            external_ref=external_ref,
        )
        return ok(data, trace_id=trace_id, status_code=202)
    except ValueError as exc:
        code = str(exc)
        if code == 'unsupported_bulk_command':
            return fail('unsupported_bulk_command', '不支持的批量命令', status_code=400, trace_id=trace_id)
        if code == 'job_ids_required':
            return fail('job_ids_required', 'jobIds 必填', status_code=400, trace_id=trace_id)
        return fail('action_worker_bulk_command_failed', '执行动作队列批量命令失败', details={'reason': code}, status_code=409, trace_id=trace_id)
    except Exception as exc:
        return fail('action_worker_bulk_command_failed', '执行动作队列批量命令失败', details={'reason': str(exc)}, status_code=500, trace_id=trace_id)


@actions_bp.route('/store/overview', methods=['GET'])
def get_action_store_overview_v1():
    try:
        batch_ref = str(request.args.get('batchRef') or '').strip() or None
        limit = request.args.get('limit', default=10, type=int)
        return ok(_get_action_delivery_service().queue_service.get_store_overview(batch_ref=batch_ref, limit=limit))
    except Exception as exc:
        return fail('action_store_overview_failed', '读取动作队列存储视图失败', details={'reason': str(exc)}, status_code=500)


@actions_bp.route('/workspace/summary', methods=['GET'])
def get_action_workspace_summary_v1():
    try:
        return ok(_get_action_audit_service().get_workspace_summary())
    except Exception as exc:
        return fail('workspace_summary_failed', '读取动作工作台汇总失败', details={'reason': str(exc)}, status_code=500)


@actions_bp.route('/workspace/items', methods=['GET'])
def list_action_workspace_items_v1():
    try:
        stage = str(request.args.get('stage') or '').strip() or None
        status = str(request.args.get('status') or '').strip() or None
        return ok(_get_action_audit_service().list_workspace_items(stage=stage, status=status))
    except Exception as exc:
        return fail('workspace_items_failed', '读取动作工作台队列失败', details={'reason': str(exc)}, status_code=500)


@actions_bp.route('/requests/<request_id>/workspace-actions', methods=['GET'])
def get_action_request_workspace_actions_v1(request_id: str):
    try:
        return ok(_get_action_workspace_service().get_workspace_actions(request_id))
    except ValueError as exc:
        code = str(exc)
        if code == 'request_not_found':
            return fail('request_not_found', '动作请求不存在', status_code=404)
        return fail('workspace_actions_failed', '读取工作台可用动作失败', details={'reason': code}, status_code=409)
    except Exception as exc:
        return fail('workspace_actions_failed', '读取工作台可用动作失败', details={'reason': str(exc)}, status_code=500)


@actions_bp.route('/requests/<request_id>/workspace-preview', methods=['GET'])
def get_action_request_workspace_preview_v1(request_id: str):
    try:
        return ok(_get_action_workspace_service().get_workspace_preview(request_id))
    except ValueError as exc:
        code = str(exc)
        if code == 'request_not_found':
            return fail('request_not_found', '动作请求不存在', status_code=404)
        return fail('workspace_preview_failed', '读取工作台预览失败', details={'reason': code}, status_code=409)
    except Exception as exc:
        return fail('workspace_preview_failed', '读取工作台预览失败', details={'reason': str(exc)}, status_code=500)


@actions_bp.route('/requests/<request_id>/workspace-command', methods=['POST'])
def execute_action_request_workspace_command_v1(request_id: str):
    payload = request.get_json(silent=True) or {}
    command = str(payload.get('command') or '').strip()
    operator = str(payload.get('operator') or 'system').strip() or 'system'
    command_payload = payload.get('payload') if isinstance(payload.get('payload'), dict) else {}
    try:
        data = _get_action_workspace_service().execute_command(
            request_id,
            command=command,
            operator=operator,
            payload=command_payload,
        )
        return ok(data, status_code=202)
    except ValueError as exc:
        code = str(exc)
        if code == 'request_not_found':
            return fail('request_not_found', '动作请求不存在', status_code=404)
        if code == 'invalid_command':
            return fail('invalid_command', '无效的工作台命令', status_code=400)
        if code in {'invalid_request_status', 'request_not_approved', 'delivery_not_found', 'callback_not_found'}:
            return fail('workspace_command_blocked', '当前状态不允许执行该工作台命令', details={'reason': code}, status_code=409)
        return fail('workspace_command_failed', '执行工作台命令失败', details={'reason': code}, status_code=409)
    except Exception as exc:
        return fail('workspace_command_failed', '执行工作台命令失败', details={'reason': str(exc)}, status_code=500)


@actions_bp.route('/requests/<request_id>/automation-boundary', methods=['GET'])
def get_action_request_automation_boundary_v1(request_id: str):
    try:
        return ok(_get_action_automation_service().get_automation_boundary(request_id))
    except ValueError as exc:
        code = str(exc)
        if code == 'request_not_found':
            return fail('request_not_found', '动作请求不存在', status_code=404)
        return fail('automation_boundary_failed', '读取自动化边界失败', details={'reason': code}, status_code=409)
    except Exception as exc:
        return fail('automation_boundary_failed', '读取自动化边界失败', details={'reason': str(exc)}, status_code=500)


@actions_bp.route('/requests/<request_id>/handoff-preview', methods=['GET'])
def get_action_request_handoff_preview_v1(request_id: str):
    try:
        return ok(_get_action_automation_service().get_handoff_preview(request_id))
    except ValueError as exc:
        code = str(exc)
        if code == 'request_not_found':
            return fail('request_not_found', '动作请求不存在', status_code=404)
        return fail('handoff_preview_failed', '读取交接预览失败', details={'reason': code}, status_code=409)
    except Exception as exc:
        return fail('handoff_preview_failed', '读取交接预览失败', details={'reason': str(exc)}, status_code=500)


@actions_bp.route('/requests/<request_id>/handoff-command', methods=['POST'])
def execute_action_request_handoff_command_v1(request_id: str):
    payload = request.get_json(silent=True) or {}
    command = str(payload.get('command') or '').strip()
    operator = str(payload.get('operator') or 'system').strip() or 'system'
    command_payload = payload.get('payload') if isinstance(payload.get('payload'), dict) else {}
    try:
        data = _get_action_automation_service().execute_handoff_command(
            request_id,
            command=command,
            operator=operator,
            payload=command_payload,
        )
        return ok(data, status_code=202)
    except ValueError as exc:
        code = str(exc)
        if code == 'request_not_found':
            return fail('request_not_found', '动作请求不存在', status_code=404)
        if code == 'invalid_command':
            return fail('invalid_command', '无效的交接命令', status_code=400)
        if code == 'handoff_blocked':
            return fail('handoff_command_blocked', '当前状态不允许执行该交接命令', details={'reason': code}, status_code=409)
        return fail('handoff_command_failed', '执行交接命令失败', details={'reason': code}, status_code=409)
    except Exception as exc:
        return fail('handoff_command_failed', '执行交接命令失败', details={'reason': str(exc)}, status_code=500)
