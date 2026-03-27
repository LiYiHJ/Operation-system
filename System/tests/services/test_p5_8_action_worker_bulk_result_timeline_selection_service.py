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


def test_action_queue_round21_bulk_result_timeline_selection_and_reexecute_filters_surface():
    reset_action_store()
    entry = ActionEntryService()
    approval = ActionApprovalService()
    queue = ActionQueueService()
    delivery = ActionDeliveryService(queue)

    _, job_a = _create_and_push(entry, approval, delivery, batch_ref='batch-r21', suffix='a')
    _, job_b = _create_and_push(entry, approval, delivery, batch_ref='batch-r21', suffix='b')
    _, job_c = _create_and_push(entry, approval, delivery, batch_ref='batch-r21', suffix='c')

    claimed = queue.claim_next_job(worker_id='worker-r21', operator='worker-r21', batch_ref='batch-r21')
    assert claimed['jobId'] == job_a

    parent = queue.execute_bulk_command(
        command='release-lease',
        job_ids=[job_a, job_b, job_c],
        operator='ops-r21',
        worker_id='worker-r21',
        reason='bulk_release_partial_r21',
    )
    child = queue.reexecute_bulk_command(
        parent['bulkCommandId'],
        selection='failed',
        command='dead-letter',
        operator='ops-r21',
        reason='rerun_failed_as_dead_letter_r21',
    )
    lineage = queue.reexecute_bulk_command_lineage(
        parent['bulkCommandId'],
        selection='failed',
        command='redrive',
        scope='entire_lineage',
        operator='ops-r21',
        reason='lineage_redrive_r21',
    )

    timeline = queue.get_bulk_command_timeline(
        parent['bulkCommandId'],
        selection='failed',
        reexecute_command='dead-letter',
        limit=10,
    )
    assert timeline['total'] == 1
    assert timeline['scope']['selection'] == 'failed'
    assert timeline['scope']['reexecuteCommand'] == 'dead-letter'
    assert timeline['selectionSummary']['failed'] == 1
    assert timeline['reexecuteCommandSummary']['dead-letter'] == 1
    assert timeline['items'][0]['bulkCommandId'] == child['bulkCommandId']
    assert timeline['items'][0]['selection'] == 'failed'
    assert timeline['items'][0]['reexecuteCommand'] == 'dead-letter'

    summary = queue.get_bulk_command_lineage_summary(
        parent['bulkCommandId'],
        selection='failed',
        reexecute_command='dead-letter',
        limit=10,
    )
    assert summary['linkedTimelineFilters']['selection'] == 'failed'
    assert summary['linkedTimelineFilters']['reexecuteCommand'] == 'dead-letter'
    assert summary['timelineSummary']['totalEvents'] == 1
    assert summary['latestResults'][0]['bulkCommandId'] in {child['bulkCommandId'], lineage['bulkCommandId']}
