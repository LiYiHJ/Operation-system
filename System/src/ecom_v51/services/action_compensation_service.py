from __future__ import annotations

from typing import Any, Dict

from .action_store import (
    ACTION_CALLBACK_HISTORY,
    ACTION_COMPENSATION_HISTORY,
    ACTION_DELIVERY_HISTORY,
    ACTION_REQUESTS,
    new_id,
    utcnow_iso,
)


class ActionCompensationService:
    CONTRACT_VERSION = 'p5.4.action_compensation.v1'

    def _get_request(self, request_id: str) -> Dict[str, Any]:
        item = ACTION_REQUESTS.get(str(request_id))
        if not item:
            raise ValueError('request_not_found')
        return item

    def _get_latest_delivery(self, request_id: str) -> Dict[str, Any]:
        history = ACTION_DELIVERY_HISTORY.get(str(request_id), [])
        if not history:
            raise ValueError('delivery_not_found')
        return history[-1]

    def _get_latest_callback(self, request_id: str) -> Dict[str, Any]:
        history = ACTION_CALLBACK_HISTORY.get(str(request_id), [])
        if not history:
            raise ValueError('callback_not_found')
        return history[-1]

    @staticmethod
    def _policy_result(provider_status: str, reason_override: str | None = None) -> Dict[str, Any]:
        normalized = str(provider_status or '').strip().lower() or 'unknown'
        if normalized in {'failed', 'rejected', 'cancelled', 'returned', 'error'}:
            return {
                'shouldCompensate': True,
                'level': 'high',
                'reason': reason_override or f'provider_status_{normalized}',
                'recommendedAction': 'manual_compensation_review',
            }
        if normalized in {'delayed', 'timeout', 'pending_exception'}:
            return {
                'shouldCompensate': True,
                'level': 'medium',
                'reason': reason_override or f'provider_status_{normalized}',
                'recommendedAction': 'monitor_and_review',
            }
        return {
            'shouldCompensate': False,
            'level': 'none',
            'reason': reason_override or 'delivery_healthy',
            'recommendedAction': 'no_action',
        }

    def evaluate_compensation(
        self,
        request_id: str,
        *,
        operator: str,
        reason_override: str | None = None,
        note: str | None = None,
    ) -> Dict[str, Any]:
        item = self._get_request(request_id)
        delivery = self._get_latest_delivery(request_id)
        callback = self._get_latest_callback(request_id)
        evaluated_at = utcnow_iso()
        policy_result = self._policy_result(callback.get('providerStatus'), reason_override=reason_override)
        evaluation = {
            'compensationEvaluationId': new_id('comp'),
            'requestId': str(request_id),
            'deliveryId': delivery.get('deliveryId'),
            'callbackEventId': callback.get('callbackEventId'),
            'evaluatedAt': evaluated_at,
            'shouldCompensate': bool(policy_result.get('shouldCompensate')),
            'level': str(policy_result.get('level') or 'none'),
            'reason': str(policy_result.get('reason') or ''),
            'recommendedAction': str(policy_result.get('recommendedAction') or ''),
            'operator': str(operator or 'system'),
            'note': note,
        }
        ACTION_COMPENSATION_HISTORY.setdefault(str(request_id), []).append(evaluation)
        item['compensationState'] = 'recommended' if evaluation['shouldCompensate'] else 'not_required'
        item['lastCompensationEvaluationId'] = evaluation['compensationEvaluationId']
        item['lastCompensationEvaluatedAt'] = evaluation['evaluatedAt']
        item['lastCompensationReason'] = evaluation['reason']
        item['lastCompensationRecommendedAction'] = evaluation['recommendedAction']
        return {
            'requestId': str(request_id),
            'deliveryId': delivery.get('deliveryId'),
            'compensationEvaluationId': evaluation['compensationEvaluationId'],
            'latestCompensationState': item['compensationState'],
            'evaluatedAt': evaluation['evaluatedAt'],
            'policyResult': {
                'shouldCompensate': evaluation['shouldCompensate'],
                'level': evaluation['level'],
                'reason': evaluation['reason'],
                'recommendedAction': evaluation['recommendedAction'],
            },
        }

    def get_compensation_state(self, request_id: str) -> Dict[str, Any]:
        self._get_request(request_id)
        delivery = self._get_latest_delivery(request_id)
        history = ACTION_COMPENSATION_HISTORY.get(str(request_id), [])
        if not history:
            self._get_latest_callback(request_id)
        latest = history[-1] if history else None
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'requestId': str(request_id),
            'deliveryId': delivery.get('deliveryId'),
            'latestCompensationState': (latest or {}).get('level') if (latest or {}).get('shouldCompensate') else ((latest or {}) and 'not_required') or 'not_evaluated',
            'latestEvaluationId': (latest or {}).get('compensationEvaluationId'),
            'latestReason': (latest or {}).get('reason'),
            'latestRecommendedAction': (latest or {}).get('recommendedAction'),
            'latestEvaluatedAt': (latest or {}).get('evaluatedAt'),
        }

    def get_compensation_history(self, request_id: str) -> Dict[str, Any]:
        self._get_request(request_id)
        self._get_latest_delivery(request_id)
        if not ACTION_COMPENSATION_HISTORY.get(str(request_id)):
            self._get_latest_callback(request_id)
        history = ACTION_COMPENSATION_HISTORY.get(str(request_id), [])
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'requestId': str(request_id),
            'items': list(history),
            'total': len(history),
        }
