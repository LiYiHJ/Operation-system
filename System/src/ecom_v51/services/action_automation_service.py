from __future__ import annotations

from typing import Any, Dict, List

from .action_store import (
    ACTION_APPROVAL_HISTORY,
    ACTION_CALLBACK_HISTORY,
    ACTION_COMPENSATION_HISTORY,
    ACTION_DELIVERY_HISTORY,
    ACTION_REQUESTS,
)


class ActionAutomationService:
    CONTRACT_VERSION = 'p5.7.action_automation.v1'

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

    def get_automation_boundary(self, request_id: str) -> Dict[str, Any]:
        item = self._get_request(request_id)
        stage, state = self._derive_stage_status(request_id, item)
        latest_comp = self._latest(ACTION_COMPENSATION_HISTORY.get(str(request_id), [])) or {}
        latest_cb = self._latest(ACTION_CALLBACK_HISTORY.get(str(request_id), [])) or {}
        status = str(item.get('status') or 'draft')
        blocked_reasons: List[str] = []
        requires_human = stage in {'entry', 'approval'} or bool(latest_comp.get('shouldCompensate'))
        can_auto = stage in {'delivery', 'callback'} and not bool(latest_comp.get('shouldCompensate'))
        if status == 'draft':
            blocked_reasons.append('await_submit')
        elif status == 'submitted':
            blocked_reasons.append('await_human_approval')
        elif latest_comp.get('shouldCompensate'):
            blocked_reasons.append('compensation_requires_human_review')
        available = [
            {
                'code': 'auto_push',
                'enabled': status == 'approved',
                'reasonBlocked': None if status == 'approved' else 'request_not_approved',
            },
            {
                'code': 'auto_callback_progress',
                'enabled': bool(ACTION_DELIVERY_HISTORY.get(str(request_id))),
                'reasonBlocked': None if ACTION_DELIVERY_HISTORY.get(str(request_id)) else 'delivery_not_found',
            },
            {
                'code': 'auto_compensation_evaluate',
                'enabled': bool(latest_cb),
                'reasonBlocked': None if latest_cb else 'callback_not_found',
            },
        ]
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'requestId': str(request_id),
            'currentStage': stage,
            'currentStatus': state,
            'automationBoundary': {
                'canAutoProceed': can_auto,
                'requiresHumanReview': requires_human,
                'blocked': bool(blocked_reasons),
                'blockedReasons': blocked_reasons,
            },
            'availableAutomationActions': available,
        }

    def get_handoff_preview(self, request_id: str) -> Dict[str, Any]:
        item = self._get_request(request_id)
        stage, state = self._derive_stage_status(request_id, item)
        latest_comp = self._latest(ACTION_COMPENSATION_HISTORY.get(str(request_id), [])) or {}
        if stage == 'entry':
            target, reason, action = 'review_queue', 'request_created', 'submit'
        elif stage == 'approval':
            target, reason, action = 'approver', 'await_approval', 'approve'
        elif stage == 'delivery':
            target, reason, action = 'callback_listener', 'await_provider_callback', 'callback_ingest'
        elif stage == 'callback':
            target = 'compensation_review' if state in {'failed', 'rejected', 'error'} else 'monitoring'
            reason = 'callback_requires_follow_up' if target == 'compensation_review' else 'callback_received'
            action = 'compensation_evaluate' if target == 'compensation_review' else 'observe'
        elif stage == 'compensation':
            if latest_comp.get('shouldCompensate'):
                target, reason, action = 'human_operator', 'compensation_recommended', 'manual_compensation_review'
            else:
                target, reason, action = 'closed', 'no_compensation_required', 'none'
        else:
            target, reason, action = 'monitoring', 'unknown_stage', 'observe'
        updated_at = latest_comp.get('evaluatedAt') or item.get('lastApprovalEventAt') or item.get('createdAt')
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'requestId': str(request_id),
            'currentStage': stage,
            'currentStatus': state,
            'handoffTarget': target,
            'handoffReason': reason,
            'nextRecommendedAction': action,
            'summary': {
                'latestMessage': reason,
                'updatedAt': updated_at,
            },
        }

    def execute_handoff_command(self, request_id: str, *, command: str, operator: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
        _ = operator, payload
        item = self._get_request(request_id)
        cmd = str(command or '').strip()
        if not cmd:
            raise ValueError('invalid_command')
        if cmd not in {'route_next', 'route_to_human', 'route_to_monitoring'}:
            raise ValueError('invalid_command')
        preview = self.get_handoff_preview(request_id)
        boundary = self.get_automation_boundary(request_id)
        status = str(item.get('status') or 'draft')
        # Compatibility rule:
        # - draft + review_queue remains blocked
        # - submitted should be able to route_next into approver
        # - later blocked states still honor blocked review_queue behavior
        if (
            cmd == 'route_next'
            and boundary['automationBoundary']['blocked']
            and preview['handoffTarget'] == 'review_queue'
            and status == 'draft'
        ):
            raise ValueError('handoff_blocked')
        target = preview['handoffTarget'] if cmd == 'route_next' else ('human_operator' if cmd == 'route_to_human' else 'monitoring')
        stage, state = self._derive_stage_status(request_id, item)
        # submitted request should advance toward approver even though boundary still flags human review
        if cmd == 'route_next' and status == 'submitted' and target == 'review_queue':
            target = 'approver'
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'requestId': str(request_id),
            'command': cmd,
            'accepted': True,
            'handoffTarget': target,
            'resultStage': stage,
            'resultStatus': state,
            'message': f'{cmd}_accepted',
        }
