from __future__ import annotations

from typing import Any, Dict, List

from .action_store import ACTION_APPROVAL_HISTORY, ACTION_REQUESTS, new_id, utcnow_iso


class ActionApprovalService:
    CONTRACT_VERSION = 'p5.1.action_approval.v1'

    def _append_history(self, request_id: str, from_status: str, to_status: str, event_type: str, operator: str, note: str | None = None) -> Dict[str, Any]:
        event = {
            'approvalEventId': new_id('appr'),
            'requestId': request_id,
            'eventType': event_type,
            'statusFrom': from_status,
            'statusTo': to_status,
            'operator': operator,
            'note': note,
            'eventAt': utcnow_iso(),
        }
        ACTION_APPROVAL_HISTORY.setdefault(request_id, []).append(event)
        return event

    def _transition(self, request_id: str, allowed_from: List[str], to_status: str, event_type: str, operator: str, note: str | None = None) -> Dict[str, Any]:
        item = ACTION_REQUESTS.get(str(request_id))
        if not item:
            raise ValueError('request_not_found')
        current = str(item.get('status') or 'draft')
        if current not in allowed_from:
            raise ValueError('invalid_request_status')
        item['status'] = to_status
        item['lastApprovalEventAt'] = utcnow_iso()
        self._append_history(str(request_id), current, to_status, event_type, operator, note)
        return dict(item)

    def submit(self, request_id: str, operator: str, note: str | None = None) -> Dict[str, Any]:
        return self._transition(request_id, ['draft'], 'submitted', 'submit', operator, note)

    def approve(self, request_id: str, operator: str, note: str | None = None) -> Dict[str, Any]:
        return self._transition(request_id, ['submitted'], 'approved', 'approve', operator, note)

    def reject(self, request_id: str, operator: str, note: str | None = None) -> Dict[str, Any]:
        return self._transition(request_id, ['submitted'], 'rejected', 'reject', operator, note)

    def cancel(self, request_id: str, operator: str, note: str | None = None) -> Dict[str, Any]:
        return self._transition(request_id, ['draft', 'submitted', 'approved'], 'cancelled', 'cancel', operator, note)

    def get_history(self, request_id: str) -> Dict[str, Any]:
        item = ACTION_REQUESTS.get(str(request_id))
        if not item:
            raise ValueError('request_not_found')
        history = ACTION_APPROVAL_HISTORY.get(str(request_id), [])
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'requestId': str(request_id),
            'items': list(history),
            'total': len(history),
        }
