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


def _create_and_push(entry, approval, delivery, *, batch_ref: str, suffix: str, action_code: str = 'price_update') -> tuple[str, str]:
    item = entry.create_request(
        {
            'actionCode': action_code,
            'requestedBy': 'evan',
            'batchRef': batch_ref,
            'canonicalSku': f'SKU-{suffix}',
        }
    )
    approval.submit(item['requestId'], operator='evan')
    approval.approve(item['requestId'], operator='lead')
    pushed = delivery.push(item['requestId'], operator='ops', channel='mock_push_adapter', trace_id=f'trc-{suffix}')
    return item['requestId'], pushed['jobId']


def test_action_queue_round12_command_audit_filters_and_bulk_feedback_surface():
    reset_action_store()
    entry = ActionEntryService()
    approval = ActionApprovalService()
    queue = ActionQueueService()
    delivery = ActionDeliveryService(queue)

    _request_a, job_a = _create_and_push(entry, approval, delivery, batch_ref='batch-r12', suffix='a', action_code='price_update')
    _request_b, job_b = _create_and_push(entry, approval, delivery, batch_ref='batch-r12', suffix='b', action_code='inventory_adjustment')
    _request_c, job_c = _create_and_push(entry, approval, delivery, batch_ref='batch-r12', suffix='c', action_code='price_update')

    queue.claim_next_job(worker_id='worker-r12-a', operator='worker-r12-a', batch_ref='batch-r12')
    queue.claim_next_job(worker_id='worker-r12-b', operator='worker-r12-b', batch_ref='batch-r12')

    queue.release_job_lease(job_a, worker_id='worker-r12-a', operator='ops-r12', reason='manual_release')
    queue.mark_job_failed(job_b, worker_id='worker-r12-b', operator='ops-r12', reason='provider_failed')

    filtered = queue.get_worker_command_audit(batch_ref='batch-r12', event_type='job_failed', action_code='inventory_adjustment', limit=20)
    assert filtered['scope']['eventType'] == 'job_failed'
    assert filtered['scope']['actionCode'] == 'inventory_adjustment'
    assert filtered['total'] == 1
    assert filtered['items'][0]['jobId'] == job_b
    assert filtered['items'][0]['eventType'] == 'job_failed'
    assert filtered['items'][0]['actionCode'] == 'inventory_adjustment'
    assert filtered['commandTypeSummary']['job_failed'] == 1
    assert filtered['actionCodeSummary']['inventory_adjustment'] == 1

    bulk = queue.execute_bulk_command(
        command='mark-succeeded',
        job_ids=[job_c, job_a],
        operator='ops-r12',
        worker_id='worker-r12-a',
        external_ref='ext-r12',
        note='round12',
    )
    assert bulk['summary']['requestedJobs'] == 2
    assert bulk['summary']['succeededJobs'] == 1
    assert bulk['summary']['failedJobs'] == 1
    assert bulk['itemStatusSummary']['succeeded'] == 1
    assert bulk['errorReasonSummary']['job_not_completable'] == 1
