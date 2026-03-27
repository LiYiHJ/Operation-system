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


def test_action_queue_round22_bulk_result_linked_command_filters_surface():
    reset_action_store()
    entry = ActionEntryService()
    approval = ActionApprovalService()
    queue = ActionQueueService()
    delivery = ActionDeliveryService(queue)

    _, job_a = _create_and_push(entry, approval, delivery, batch_ref='batch-r22', suffix='a')
    _, job_b = _create_and_push(entry, approval, delivery, batch_ref='batch-r22', suffix='b')
    _, job_c = _create_and_push(entry, approval, delivery, batch_ref='batch-r22', suffix='c')

    claimed = queue.claim_next_job(worker_id='worker-r22', operator='worker-r22', batch_ref='batch-r22')
    assert claimed['jobId'] == job_a

    parent = queue.execute_bulk_command(
        command='release-lease',
        job_ids=[job_a, job_b, job_c],
        operator='ops-r22',
        worker_id='worker-r22',
        reason='bulk_release_partial_r22',
    )
    child = queue.reexecute_bulk_command(
        parent['bulkCommandId'],
        selection='failed',
        command='dead-letter',
        operator='ops-r22',
        reason='rerun_failed_as_dead_letter_r22',
    )
    queue.reexecute_bulk_command_lineage(
        parent['bulkCommandId'],
        selection='failed',
        command='redrive',
        scope='entire_lineage',
        operator='ops-r22',
        reason='lineage_redrive_r22',
    )

    detail = queue.get_bulk_command_detail(child['bulkCommandId'])
    assert detail['navigationContext']['command'] == 'dead-letter'
    assert detail['navigationContext']['resultMode'] == 'failed'

    summary = queue.get_bulk_command_lineage_summary(
        parent['bulkCommandId'],
        command='dead-letter',
        limit=10,
    )
    assert summary['summary']['totalResults'] == 1
    assert summary['commandSummary']['dead-letter'] == 1
    assert summary['linkedHistoryFilters']['command'] == 'dead-letter'
    assert summary['linkedTimelineFilters']['command'] == 'dead-letter'
    assert summary['latestResults'][0]['bulkCommandId'] == child['bulkCommandId']
    assert summary['timeline'][0]['bulkCommandId'] == child['bulkCommandId']
