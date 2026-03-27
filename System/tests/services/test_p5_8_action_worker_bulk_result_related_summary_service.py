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


def test_action_queue_round24_bulk_result_related_summary_surface():
    reset_action_store()
    entry = ActionEntryService()
    approval = ActionApprovalService()
    queue = ActionQueueService()
    delivery = ActionDeliveryService(queue)

    _, job_a = _create_and_push(entry, approval, delivery, batch_ref='batch-r24', suffix='a')
    _, job_b = _create_and_push(entry, approval, delivery, batch_ref='batch-r24', suffix='b')
    _, job_c = _create_and_push(entry, approval, delivery, batch_ref='batch-r24', suffix='c')

    claimed = queue.claim_next_job(worker_id='worker-r24', operator='worker-r24', batch_ref='batch-r24')
    assert claimed['jobId'] == job_a

    parent = queue.execute_bulk_command(
        command='release-lease',
        job_ids=[job_a, job_b, job_c],
        operator='ops-r24',
        worker_id='worker-r24',
        reason='bulk_release_partial_r24',
    )
    child = queue.reexecute_bulk_command(
        parent['bulkCommandId'],
        selection='failed',
        command='dead-letter',
        operator='ops-r24',
        reason='rerun_failed_as_dead_letter_r24',
    )
    lineage = queue.reexecute_bulk_command_lineage(
        parent['bulkCommandId'],
        selection='failed',
        command='redrive',
        scope='entire_lineage',
        operator='ops-r24',
        reason='lineage_redrive_r24',
    )

    related = queue.get_bulk_command_related(parent['bulkCommandId'], limit=10)
    assert related['summary']['totalResults'] == 3
    assert related['commandModeSummary']['direct'] == 1
    assert related['commandModeSummary']['reexecute'] == 1
    assert related['commandModeSummary']['lineage'] == 1
    assert related['selectionSummary']['direct'] == 1
    assert related['selectionSummary']['failed'] == 2
    assert related['reexecuteCommandSummary']['direct'] == 1
    assert related['reexecuteCommandSummary']['dead-letter'] == 1
    assert related['reexecuteCommandSummary']['redrive'] == 1
    assert related['lineageScopeSummary']['direct'] == 2
    assert related['lineageScopeSummary']['entire_lineage'] == 1
    assert related['linkedHistoryFilters']['focusBulkCommandId'] == parent['bulkCommandId']
    assert related['linkedTimelineFilters']['focusBulkCommandId'] == parent['bulkCommandId']

    latest = related['items'][0]
    assert latest['bulkCommandId'] == lineage['bulkCommandId']
    assert latest['commandMode'] == 'lineage'
    assert latest['selection'] == 'failed'
    assert latest['reexecuteCommand'] == 'redrive'
    assert latest['lineageScope'] == 'entire_lineage'
    assert latest['linkedHistoryFilters']['focusBulkCommandId'] == lineage['bulkCommandId']
    assert latest['linkedTimelineFilters']['focusBulkCommandId'] == lineage['bulkCommandId']
    assert related['items'][-1]['bulkCommandId'] == parent['bulkCommandId']
    assert child['bulkCommandId'] in {item['bulkCommandId'] for item in related['items']}
