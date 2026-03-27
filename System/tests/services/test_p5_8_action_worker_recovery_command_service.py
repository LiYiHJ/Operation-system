from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ecom_v51.services.action_approval_service import ActionApprovalService
from ecom_v51.services.action_delivery_service import ActionDeliveryService
from ecom_v51.services.action_entry_service import ActionEntryService
from ecom_v51.services.action_queue_service import ActionQueueService
from ecom_v51.services.action_store import ACTION_JOBS, reset_action_store


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


def test_action_queue_round10_stale_release_and_command_audit_surface():
    reset_action_store()
    entry = ActionEntryService()
    approval = ActionApprovalService()
    queue = ActionQueueService()
    delivery = ActionDeliveryService(queue)

    _request_id, job_id = _create_and_push(entry, approval, delivery, batch_ref='batch-r10', suffix='a')
    claimed = queue.claim_next_job(worker_id='worker-r10', operator='worker-r10', batch_ref='batch-r10')
    assert claimed['jobId'] == job_id

    stale_at = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
    ACTION_JOBS[job_id]['leaseHeartbeatAt'] = stale_at
    ACTION_JOBS[job_id]['leaseExpiresAt'] = stale_at

    released = queue.release_stale_jobs(batch_ref='batch-r10', operator='ops-r10', limit=10, reason='stale_timeout')
    assert released['summary']['staleMatched'] == 1
    assert released['summary']['releasedJobs'] == 1
    assert released['items'][0]['jobId'] == job_id
    assert released['items'][0]['jobStatus'] == 'queued'
    assert released['items'][0]['workerId'] is None
    assert released['items'][0]['releaseEventId']

    audit = queue.get_worker_command_audit(batch_ref='batch-r10', limit=20)
    assert audit['summary']['claimEvents'] >= 1
    assert audit['summary']['staleReleaseEvents'] == 1
    assert audit['commandTypeSummary']['job_stale_released'] == 1
    assert audit['total'] >= 2
