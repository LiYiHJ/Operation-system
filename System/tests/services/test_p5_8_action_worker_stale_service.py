from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ecom_v51.services.action_approval_service import ActionApprovalService
from ecom_v51.services.action_delivery_service import ActionDeliveryService
from ecom_v51.services.action_entry_service import ActionEntryService
from ecom_v51.services.action_queue_service import ActionQueueService
from ecom_v51.services.action_store import reset_action_store


def _create_and_push(entry, approval, delivery, *, batch_ref: str, suffix: str) -> tuple[str, str]:
    item = entry.create_request(
        {
            'actionCode': 'price_update',
            'requestedBy': 'evan',
            'batchRef': batch_ref,
            'canonicalSku': f'SKU-{suffix}',
        }
    )
    approval.submit(item['requestId'], operator='evan')
    approval.approve(item['requestId'], operator='lead')
    pushed = delivery.push(item['requestId'], operator='ops', channel='mock_push_adapter', trace_id=f'trc-{suffix}')
    return item['requestId'], pushed['jobId']


def test_action_queue_round8_stale_detection_surface():
    reset_action_store()
    entry = ActionEntryService()
    approval = ActionApprovalService()
    queue = ActionQueueService()
    delivery = ActionDeliveryService(queue)

    _request_id, job_id = _create_and_push(entry, approval, delivery, batch_ref='batch-r8', suffix='a')
    claimed = queue.claim_next_job(worker_id='worker-r8', operator='worker-r8', batch_ref='batch-r8')
    assert claimed['jobId'] == job_id

    # force a stale lease
    job = queue.get_job_detail(job_id)
    job['leaseExpiresAt'] = '2000-01-01T00:00:00+00:00'
    job['leaseHeartbeatAt'] = '2000-01-01T00:00:00+00:00'

    stale = queue.get_worker_stale_jobs(batch_ref='batch-r8', limit=10)
    assert stale['summary']['staleJobs'] == 1
    assert stale['summary']['leaseTtlSeconds'] == queue.LEASE_TTL_SECONDS
    assert stale['total'] == 1
    assert stale['items'][0]['jobId'] == job_id
    assert stale['items'][0]['staleCategory'] == 'lease_expired'
    assert stale['items'][0]['staleSeconds'] > 0
