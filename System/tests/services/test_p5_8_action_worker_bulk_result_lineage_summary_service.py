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


def test_action_queue_round18_bulk_lineage_summary_and_command_mode_history_surface():
    reset_action_store()
    entry = ActionEntryService()
    approval = ActionApprovalService()
    queue = ActionQueueService()
    delivery = ActionDeliveryService(queue)

    _, job_a = _create_and_push(entry, approval, delivery, batch_ref='batch-r18', suffix='a')
    _, job_b = _create_and_push(entry, approval, delivery, batch_ref='batch-r18', suffix='b')
    _, job_c = _create_and_push(entry, approval, delivery, batch_ref='batch-r18', suffix='c')

    claimed = queue.claim_next_job(worker_id='worker-r18', operator='worker-r18', batch_ref='batch-r18')
    assert claimed['jobId'] == job_a

    parent = queue.execute_bulk_command(
        command='release-lease',
        job_ids=[job_a, job_b, job_c],
        operator='ops-r18',
        worker_id='worker-r18',
        reason='bulk_release_partial_r18',
    )
    assert parent['summary']['succeededJobs'] == 1
    assert parent['summary']['failedJobs'] == 2

    child = queue.reexecute_bulk_command(
        parent['bulkCommandId'],
        selection='failed',
        command='dead-letter',
        operator='ops-r18',
        reason='rerun_failed_as_dead_letter_r18',
    )
    assert child['summary']['succeededJobs'] == 2

    lineage = queue.reexecute_bulk_command_lineage(
        parent['bulkCommandId'],
        selection='failed',
        command='redrive',
        scope='entire_lineage',
        operator='ops-r18',
        reason='lineage_redrive_r18',
    )
    assert lineage['summary']['succeededJobs'] == 2
    assert lineage['lineageScope'] == 'entire_lineage'

    history = queue.get_bulk_command_history(batch_ref='batch-r18', command_mode='lineage', offset=0, limit=10)
    assert history['total'] == 1
    assert history['items'][0]['bulkCommandId'] == lineage['bulkCommandId']
    assert history['items'][0]['commandMode'] == 'lineage'
    assert history['commandModeSummary']['lineage'] == 1

    summary = queue.get_bulk_command_lineage_summary(parent['bulkCommandId'], command_mode='lineage', limit=10)
    assert summary['summary']['totalResults'] == 1
    assert summary['summary']['totalSucceededJobs'] == 2
    assert summary['commandModeSummary']['lineage'] == 1
    assert summary['timelineEventTypeSummary']['bulk_result_reexecuted'] == 1
    assert summary['latestResults'][0]['bulkCommandId'] == lineage['bulkCommandId']

    timeline = queue.get_bulk_command_timeline(parent['bulkCommandId'], command_mode='lineage', lineage_depth=1, limit=10)
    assert timeline['total'] == 1
    assert timeline['items'][0]['bulkCommandId'] == lineage['bulkCommandId']
    assert timeline['commandModeSummary']['lineage'] == 1
