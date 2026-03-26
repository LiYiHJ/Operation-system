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


def test_action_queue_round9_worker_lifecycle_surface():
    reset_action_store()
    entry = ActionEntryService()
    approval = ActionApprovalService()
    queue = ActionQueueService()
    delivery = ActionDeliveryService(queue)

    _request_id, job_a = _create_and_push(entry, approval, delivery, batch_ref='batch-r9', suffix='a')
    _request_id, job_b = _create_and_push(entry, approval, delivery, batch_ref='batch-r9', suffix='b')

    claimed_a = queue.claim_next_job(worker_id='worker-r9', operator='worker-r9', batch_ref='batch-r9')
    assert claimed_a['jobId'] == job_a

    released = queue.release_job_lease(job_a, worker_id='worker-r9', operator='worker-r9', reason='manual_release')
    assert released['jobStatus'] == 'queued'
    assert released['workerId'] is None
    assert 'release-lease' not in released['availableCommands']

    reclaimed = queue.claim_next_job(worker_id='worker-r9', operator='worker-r9', batch_ref='batch-r9')
    assert reclaimed['jobId'] == job_a
    succeeded = queue.mark_job_succeeded(job_a, worker_id='worker-r9', operator='worker-r9', external_ref='ext-r9')
    assert succeeded['jobStatus'] == 'succeeded'
    assert succeeded['queueStatus'] == 'completed'
    assert succeeded['result']['externalRef'] == 'ext-r9'

    claimed_b = queue.claim_next_job(worker_id='worker-r9', operator='worker-r9', batch_ref='batch-r9')
    assert claimed_b['jobId'] == job_b
    failed = queue.mark_job_failed(job_b, worker_id='worker-r9', operator='worker-r9', reason='worker_timeout')
    assert failed['jobStatus'] == 'failed'
    assert failed['recommendedOperation'] == 'retry'

    audit = queue.get_worker_lease_audit(batch_ref='batch-r9', worker_id='worker-r9', limit=20)
    assert audit['summary']['claimEvents'] >= 3
    assert audit['summary']['releaseEvents'] == 1
    assert audit['summary']['succeededEvents'] == 1
    assert audit['summary']['failedEvents'] == 1
    assert audit['total'] >= 5
