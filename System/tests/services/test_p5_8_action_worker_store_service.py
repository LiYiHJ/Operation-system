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


def test_action_queue_round7_worker_and_store_surfaces():
    reset_action_store()
    entry = ActionEntryService()
    approval = ActionApprovalService()
    queue = ActionQueueService()
    delivery = ActionDeliveryService(queue)

    request_a, job_a = _create_and_push(entry, approval, delivery, batch_ref='batch-r7', suffix='a')
    request_b, job_b = _create_and_push(entry, approval, delivery, batch_ref='batch-r7', suffix='b')

    overview_before = queue.get_worker_overview(batch_ref='batch-r7', limit=10)
    assert overview_before['summary']['queuedJobs'] == 2
    assert overview_before['summary']['runningJobs'] == 0
    assert overview_before['nextJobsTotal'] == 2

    claimed = queue.claim_next_job(worker_id='worker-r7', operator='worker-r7', batch_ref='batch-r7', note='claim-first')
    assert claimed['jobStatus'] == 'running'
    assert claimed['workerId'] == 'worker-r7'
    assert claimed['leaseClaimedAt']

    heartbeat = queue.heartbeat_job(claimed['jobId'], worker_id='worker-r7', operator='worker-r7', note='alive')
    assert heartbeat['workerId'] == 'worker-r7'
    assert heartbeat['leaseHeartbeatAt']
    assert heartbeat['queueStatus'] == 'claimed'

    overview_after = queue.get_worker_overview(batch_ref='batch-r7', limit=10)
    assert overview_after['summary']['queuedJobs'] == 1
    assert overview_after['summary']['runningJobs'] == 1
    assert overview_after['summary']['leasedJobs'] == 1
    assert overview_after['activeLeasesTotal'] == 1

    store = queue.get_store_overview(batch_ref='batch-r7', limit=10)
    assert store['summary']['totalRequests'] == 2
    assert store['summary']['totalJobs'] == 2
    assert store['summary']['requestJobIndexEntries'] == 2
    assert store['summary']['totalDeliveries'] == 2
    assert store['latestJobsTotal'] == 2
    assert set(store['batchRefs']) == {'batch-r7'}

    request_ids = {request_a, request_b}
    job_ids = {job_a, job_b}
    assert request_ids == {item['requestId'] for item in [queue.get_latest_request_job(request_a), queue.get_latest_request_job(request_b)] if item}
    assert job_ids == {item['jobId'] for item in store['latestJobs']}
