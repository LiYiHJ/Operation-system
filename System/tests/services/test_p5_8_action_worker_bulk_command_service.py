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


def test_action_queue_round11_bulk_release_and_command_audit_detail_surface():
    reset_action_store()
    entry = ActionEntryService()
    approval = ActionApprovalService()
    queue = ActionQueueService()
    delivery = ActionDeliveryService(queue)

    _request_a, job_a = _create_and_push(entry, approval, delivery, batch_ref='batch-r11', suffix='a')
    _request_b, job_b = _create_and_push(entry, approval, delivery, batch_ref='batch-r11', suffix='b')

    claimed_a = queue.claim_next_job(worker_id='worker-r11-a', operator='worker-r11-a', batch_ref='batch-r11')
    claimed_b = queue.claim_next_job(worker_id='worker-r11-b', operator='worker-r11-b', batch_ref='batch-r11')
    assert {claimed_a['jobId'], claimed_b['jobId']} == {job_a, job_b}

    bulk = queue.execute_bulk_command(
        command='release-lease',
        job_ids=[job_a, job_b],
        operator='ops-r11',
        reason='bulk_release',
        note='round11',
    )
    assert bulk['summary']['requestedJobs'] == 2
    assert bulk['summary']['succeededJobs'] == 2
    assert bulk['summary']['failedJobs'] == 0
    assert {item['jobId'] for item in bulk['items']} == {job_a, job_b}
    assert all(item['jobStatus'] == 'queued' for item in bulk['items'])

    audit = queue.get_worker_command_audit(batch_ref='batch-r11', limit=20)
    assert audit['summary']['releaseEvents'] >= 2
    detail_event_id = next(item['eventId'] for item in audit['items'] if item['eventType'] == 'job_lease_released')
    detail = queue.get_worker_command_audit_detail(detail_event_id)
    assert detail['eventId'] == detail_event_id
    assert detail['commandAudit']['eventType'] == 'job_lease_released'
    assert detail['job']['jobId'] in {job_a, job_b}
    assert detail['timelineTotal'] >= 2
