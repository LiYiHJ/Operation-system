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
    item = entry.create_request({'actionCode': 'price_update', 'requestedBy': 'evan', 'batchRef': batch_ref, 'canonicalSku': f'SKU-{suffix}'})
    approval.submit(item['requestId'], operator='evan')
    approval.approve(item['requestId'], operator='lead')
    pushed = delivery.push(item['requestId'], operator='ops', channel='mock_push_adapter', trace_id=f'trc-{suffix}')
    return item['requestId'], pushed['jobId']


def test_action_queue_round13_bulk_result_history_surface():
    reset_action_store()
    entry = ActionEntryService()
    approval = ActionApprovalService()
    queue = ActionQueueService()
    delivery = ActionDeliveryService(queue)

    _, job_a = _create_and_push(entry, approval, delivery, batch_ref='batch-r13', suffix='a')
    _, job_b = _create_and_push(entry, approval, delivery, batch_ref='batch-r13', suffix='b')
    queue.claim_next_job(worker_id='worker-r13', operator='worker-r13', batch_ref='batch-r13')

    bulk = queue.execute_bulk_command(command='mark-failed', job_ids=[job_a, job_b], operator='ops-r13', worker_id='worker-r13', reason='bulk_failed')
    history = queue.get_bulk_command_history(batch_ref='batch-r13', command='mark-failed', limit=10)
    assert history['scope']['batchRef'] == 'batch-r13'
    assert history['scope']['command'] == 'mark-failed'
    assert history['summary']['totalCommands'] == 1
    assert history['commandSummary']['mark-failed'] == 1
    assert history['items'][0]['bulkCommandId'] == bulk['bulkCommandId']
    detail = queue.get_bulk_command_detail(bulk['bulkCommandId'])
    assert detail['bulkCommandId'] == bulk['bulkCommandId']
    assert detail['bulkCommand']['summary']['requestedJobs'] == 2
    assert detail['bulkCommand']['summary']['failedJobs'] == 1
    assert len(detail['bulkCommand']['items']) == 1
    assert len(detail['bulkCommand']['errors']) == 1
