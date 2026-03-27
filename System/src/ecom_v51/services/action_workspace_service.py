from __future__ import annotations

from typing import Any, Dict, List

from .action_approval_service import ActionApprovalService
from .action_callback_service import ActionCallbackService
from .action_compensation_service import ActionCompensationService
from .action_delivery_service import ActionDeliveryService
from .action_store import (
    ACTION_APPROVAL_HISTORY,
    ACTION_CALLBACK_HISTORY,
    ACTION_COMPENSATION_HISTORY,
    ACTION_DELIVERY_HISTORY,
    ACTION_REQUESTS,
)


class ActionWorkspaceService:
    CONTRACT_VERSION = 'p5.6.action_workspace.v1'

    def __init__(self) -> None:
        self.approval_service = ActionApprovalService()
        self.delivery_service = ActionDeliveryService()
        self.callback_service = ActionCallbackService()
        self.compensation_service = ActionCompensationService()

    def _get_request(self, request_id: str) -> Dict[str, Any]:
        item = ACTION_REQUESTS.get(str(request_id))
        if not item:
            raise ValueError('request_not_found')
        return item

    @staticmethod
    def _latest(history: List[Dict[str, Any]]) -> Dict[str, Any] | None:
        return history[-1] if history else None

    def _derive_stage_status(self, request_id: str, item: Dict[str, Any]) -> tuple[str, str]:
        latest_comp = self._latest(ACTION_COMPENSATION_HISTORY.get(str(request_id), []))
        if latest_comp:
            state = 'recommended' if latest_comp.get('shouldCompensate') else 'not_required'
            return 'compensation', state
        latest_cb = self._latest(ACTION_CALLBACK_HISTORY.get(str(request_id), []))
        if latest_cb:
            return 'callback', str(latest_cb.get('providerStatus') or 'received')
        latest_delivery = self._latest(ACTION_DELIVERY_HISTORY.get(str(request_id), []))
        if latest_delivery:
            return 'delivery', str(latest_delivery.get('deliveryStatus') or 'accepted')
        latest_approval = self._latest(ACTION_APPROVAL_HISTORY.get(str(request_id), []))
        if latest_approval:
            return 'approval', str(latest_approval.get('statusTo') or item.get('status') or 'submitted')
        return 'entry', str(item.get('status') or 'draft')

    def _build_actions(self, item: Dict[str, Any], request_id: str) -> List[Dict[str, Any]]:
        status = str(item.get('status') or 'draft')
        has_delivery = bool(ACTION_DELIVERY_HISTORY.get(str(request_id)))
        has_callback = bool(ACTION_CALLBACK_HISTORY.get(str(request_id)))
        actions = []
        def add(code: str, label: str, enabled: bool, reason: str | None = None):
            actions.append({'code': code, 'label': label, 'enabled': enabled, 'reasonBlocked': None if enabled else reason})

        add('submit', '提交审批', status == 'draft', None if status == 'draft' else 'request_not_draft')
        add('approve', '审批通过', status == 'submitted', None if status == 'submitted' else 'request_not_submitted')
        add('reject', '驳回请求', status == 'submitted', None if status == 'submitted' else 'request_not_submitted')
        add('cancel', '取消请求', status in {'draft', 'submitted', 'approved'}, None if status in {'draft','submitted','approved'} else 'request_not_cancellable')
        add('push', '执行推送', status == 'approved', None if status == 'approved' else 'request_not_approved')
        add('callback_ingest', '写入回调', has_delivery, None if has_delivery else 'delivery_not_found')
        add('compensation_evaluate', '执行补偿评估', has_callback, None if has_callback else 'callback_not_found')
        return actions

    def get_workspace_actions(self, request_id: str) -> Dict[str, Any]:
        item = self._get_request(request_id)
        stage, state = self._derive_stage_status(request_id, item)
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'requestId': str(request_id),
            'currentStage': stage,
            'currentStatus': state,
            'availableActions': self._build_actions(item, request_id),
        }

    def get_workspace_preview(self, request_id: str) -> Dict[str, Any]:
        item = self._get_request(request_id)
        stage, state = self._derive_stage_status(request_id, item)
        latest_delivery = self._latest(ACTION_DELIVERY_HISTORY.get(str(request_id), [])) or {}
        latest_callback = self._latest(ACTION_CALLBACK_HISTORY.get(str(request_id), [])) or {}
        latest_comp = self._latest(ACTION_COMPENSATION_HISTORY.get(str(request_id), [])) or {}
        actions = self._build_actions(item, request_id)
        latest_message = latest_comp.get('recommendedAction') or latest_callback.get('eventType') or latest_delivery.get('resultMessage') or 'request_ready'
        updated_at = latest_comp.get('evaluatedAt') or latest_callback.get('receivedAt') or latest_delivery.get('pushedAt') or item.get('lastApprovalEventAt') or item.get('createdAt')
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'requestId': str(request_id),
            'actionCode': item.get('actionCode'),
            'currentStage': stage,
            'currentStatus': state,
            'approvalStatus': item.get('status'),
            'deliveryStatus': latest_delivery.get('deliveryStatus'),
            'callbackState': latest_callback.get('providerStatus') or item.get('callbackState'),
            'compensationState': ('recommended' if latest_comp.get('shouldCompensate') else 'not_required') if latest_comp else item.get('compensationState'),
            'availableActions': actions,
            'summary': {
                'latestMessage': latest_message,
                'updatedAt': updated_at,
            },
        }

    def execute_command(self, request_id: str, *, command: str, operator: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
        payload = dict(payload or {})
        item = self._get_request(request_id)
        cmd = str(command or '').strip()
        if not cmd:
            raise ValueError('invalid_command')
        if cmd == 'submit':
            self.approval_service.submit(request_id, operator=operator, note=payload.get('note'))
        elif cmd == 'approve':
            self.approval_service.approve(request_id, operator=operator, note=payload.get('note'))
        elif cmd == 'reject':
            self.approval_service.reject(request_id, operator=operator, note=payload.get('note'))
        elif cmd == 'cancel':
            self.approval_service.cancel(request_id, operator=operator, note=payload.get('note'))
        elif cmd == 'push':
            self.delivery_service.push(request_id, operator=operator, channel=payload.get('channel'), note=payload.get('note'))
        elif cmd == 'callback_ingest':
            self.callback_service.ingest_callback(
                request_id,
                event_type=str(payload.get('eventType') or 'status_update'),
                provider_status=str(payload.get('providerStatus') or 'received'),
                external_ref=payload.get('externalRef'),
                payload=payload.get('payload') or {},
                received_at=payload.get('receivedAt'),
            )
        elif cmd == 'compensation_evaluate':
            self.compensation_service.evaluate_compensation(
                request_id,
                operator=operator,
                reason_override=payload.get('reasonOverride'),
                note=payload.get('note'),
            )
        else:
            raise ValueError('invalid_command')
        item = self._get_request(request_id)
        stage, state = self._derive_stage_status(request_id, item)
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'requestId': str(request_id),
            'command': cmd,
            'accepted': True,
            'resultStage': stage,
            'resultStatus': state,
            'message': f'{cmd}_accepted',
        }
