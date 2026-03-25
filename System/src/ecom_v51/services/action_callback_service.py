from __future__ import annotations

from typing import Any, Dict

from .action_store import ACTION_CALLBACK_HISTORY, ACTION_DELIVERY_HISTORY, ACTION_REQUESTS, new_id, utcnow_iso


class ActionCallbackService:
    CONTRACT_VERSION = 'p5.3.action_callback.v1'

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

    def ingest_callback(
        self,
        request_id: str,
        *,
        event_type: str,
        provider_status: str,
        external_ref: str | None = None,
        payload: Dict[str, Any] | None = None,
        received_at: str | None = None,
    ) -> Dict[str, Any]:
        item = self._get_request(request_id)
        delivery = self._get_latest_delivery(request_id)
        event = {
            'callbackEventId': new_id('callback'),
            'requestId': str(request_id),
            'deliveryId': delivery.get('deliveryId'),
            'eventType': str(event_type or '').strip() or 'status_update',
            'providerStatus': str(provider_status or '').strip() or 'unknown',
            'externalRef': str(external_ref or delivery.get('externalRef') or '').strip() or None,
            'payload': dict(payload or {}),
            'receivedAt': str(received_at or utcnow_iso()),
        }
        ACTION_CALLBACK_HISTORY.setdefault(str(request_id), []).append(event)
        item['callbackState'] = event['providerStatus']
        item['lastCallbackEventId'] = event['callbackEventId']
        item['lastCallbackReceivedAt'] = event['receivedAt']
        item['lastCallbackEventType'] = event['eventType']
        item['lastCallbackProviderStatus'] = event['providerStatus']
        item['lastCallbackExternalRef'] = event['externalRef']
        return {
            'requestId': str(request_id),
            'deliveryId': delivery.get('deliveryId'),
            'callbackEventId': event['callbackEventId'],
            'latestCallbackState': event['providerStatus'],
            'receivedAt': event['receivedAt'],
            'ingestResult': {
                'accepted': True,
                'message': 'callback_ingested',
            },
        }

    def get_callback_state(self, request_id: str) -> Dict[str, Any]:
        item = self._get_request(request_id)
        delivery = self._get_latest_delivery(request_id)
        history = ACTION_CALLBACK_HISTORY.get(str(request_id), [])
        latest = history[-1] if history else None
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'requestId': str(request_id),
            'deliveryId': delivery.get('deliveryId'),
            'latestCallbackState': (latest or {}).get('providerStatus') or str(item.get('callbackState') or 'not_received'),
            'latestProviderStatus': (latest or {}).get('providerStatus'),
            'latestEventType': (latest or {}).get('eventType'),
            'latestReceivedAt': (latest or {}).get('receivedAt'),
            'externalRef': (latest or {}).get('externalRef') or delivery.get('externalRef'),
        }

    def get_callback_events(self, request_id: str) -> Dict[str, Any]:
        self._get_request(request_id)
        self._get_latest_delivery(request_id)
        history = ACTION_CALLBACK_HISTORY.get(str(request_id), [])
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'requestId': str(request_id),
            'items': list(history),
            'total': len(history),
        }
