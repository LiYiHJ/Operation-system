from __future__ import annotations

from typing import Any, Dict

from .action_queue_service import ActionQueueService
from .action_store import ACTION_DELIVERY_HISTORY, ACTION_REQUESTS, new_id, utcnow_iso


class ActionDeliveryService:
    CONTRACT_VERSION = 'p5.2.action_delivery.v1'

    def __init__(self, queue_service: ActionQueueService | None = None) -> None:
        self.queue_service = queue_service or ActionQueueService()

    def push(
        self,
        request_id: str,
        operator: str,
        channel: str | None = None,
        note: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> Dict[str, Any]:
        item = ACTION_REQUESTS.get(str(request_id))
        if not item:
            raise ValueError('request_not_found')
        current = str(item.get('status') or 'draft')
        if current != 'approved':
            raise ValueError('request_not_approved')

        job = self.queue_service.enqueue_push(
            request_id,
            operator=operator,
            channel=channel,
            note=note,
            trace_id=trace_id,
            idempotency_key=idempotency_key,
        )
        delivery = {
            'deliveryId': new_id('delivery'),
            'requestId': str(request_id),
            'adapter': str(channel or 'mock_push_adapter'),
            'deliveryStatus': 'accepted',
            'queueStatus': str(job.get('queueStatus') or 'queued'),
            'jobId': job.get('jobId'),
            'executionMode': job.get('executionMode') or 'async_queue',
            'pushedAt': utcnow_iso(),
            'externalRef': new_id('ext'),
            'resultMessage': 'accepted_into_async_queue',
            'operator': operator,
            'note': note,
            'traceId': trace_id,
            'idempotencyKey': idempotency_key,
        }
        ACTION_DELIVERY_HISTORY.setdefault(str(request_id), []).append(delivery)
        item['status'] = 'pushed'
        item['lastDeliveryId'] = delivery['deliveryId']
        item['lastPushedAt'] = delivery['pushedAt']
        item['lastJobId'] = job.get('jobId')
        return {
            'requestId': str(request_id),
            'deliveryId': delivery['deliveryId'],
            'requestStatus': item['status'],
            'deliveryStatus': delivery['deliveryStatus'],
            'queueStatus': delivery['queueStatus'],
            'jobId': job.get('jobId'),
            'executionMode': delivery['executionMode'],
            'adapter': delivery['adapter'],
            'pushedAt': delivery['pushedAt'],
            'traceId': trace_id,
            'idempotencyKey': idempotency_key,
            'result': {
                'accepted': True,
                'queued': True,
                'message': delivery['resultMessage'],
                'externalRef': delivery['externalRef'],
            },
        }

    def get_delivery(self, request_id: str) -> Dict[str, Any]:
        item = ACTION_REQUESTS.get(str(request_id))
        if not item:
            raise ValueError('request_not_found')
        history = ACTION_DELIVERY_HISTORY.get(str(request_id), [])
        latest = history[-1] if history else None
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'requestId': str(request_id),
            'currentApprovalStatus': str(item.get('status') or 'draft'),
            'latestDelivery': latest,
        }

    def get_delivery_history(self, request_id: str) -> Dict[str, Any]:
        item = ACTION_REQUESTS.get(str(request_id))
        if not item:
            raise ValueError('request_not_found')
        history = ACTION_DELIVERY_HISTORY.get(str(request_id), [])
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'requestId': str(request_id),
            'items': list(history),
            'total': len(history),
        }

    def list_request_jobs(self, request_id: str) -> Dict[str, Any]:
        return self.queue_service.list_request_jobs(request_id)



    def get_request_recovery(self, request_id: str) -> Dict[str, Any]:
        return self.queue_service.get_request_recovery(request_id)
