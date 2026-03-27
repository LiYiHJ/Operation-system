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


def test_action_queue_round16_bulk_result_timeline_and_lineage_filters_surface():
    reset_action_store()
    entry = ActionEntryService()
    approval = ActionApprovalService()
    queue = ActionQueueService()
    delivery = ActionDeliveryService(queue)

    _, job_a = _create_and_push(entry, approval, delivery, batch_ref='batch-r16', suffix='a')
    _, job_b = _create_and_push(entry, approval, delivery, batch_ref='batch-r16', suffix='b')

    claimed = queue.claim_next_job(worker_id='worker-r16', operator='worker-r16', batch_ref='batch-r16')
    assert claimed['jobId'] == job_a

    parent = queue.execute_bulk_command(
        command='release-lease',
        job_ids=[job_a, job_b],
        operator='ops-r16',
        worker_id='worker-r16',
        reason='bulk_release_partial',
    )
    child = queue.reexecute_bulk_command(
        parent['bulkCommandId'],
        selection='failed',
        command='dead-letter',
        operator='ops-r16',
        reason='rerun_failed_as_dead_letter',
    )
    grandchild = queue.reexecute_bulk_command(
        child['bulkCommandId'],
        selection='all',
        command='redrive',
        operator='ops-r16',
        reason='rerun_all_as_redrive',
    )

    parent_filtered = queue.get_bulk_command_history(batch_ref='batch-r16', parent_bulk_command_id=parent['bulkCommandId'], offset=0, limit=10)
    assert parent_filtered['total'] == 1
    assert parent_filtered['items'][0]['bulkCommandId'] == child['bulkCommandId']

    children_filtered = queue.get_bulk_command_history(batch_ref='batch-r16', has_children='true', offset=0, limit=10)
    assert children_filtered['lineageSummary']['resultsWithChildren'] == 2
    assert children_filtered['total'] == 2

    depth_filtered = queue.get_bulk_command_history(batch_ref='batch-r16', lineage_depth=2, offset=0, limit=10)
    assert depth_filtered['total'] == 1
    assert depth_filtered['items'][0]['bulkCommandId'] == grandchild['bulkCommandId']

    timeline = queue.get_bulk_command_timeline(parent['bulkCommandId'], limit=10)
    assert timeline['total'] == 3
    assert timeline['items'][0]['bulkCommandId'] == parent['bulkCommandId']
    assert timeline['items'][-1]['bulkCommandId'] == grandchild['bulkCommandId']
    assert timeline['commandSummary']['release-lease'] == 1
    assert timeline['commandSummary']['dead-letter'] == 1
    assert timeline['commandSummary']['redrive'] == 1

    grandchild_detail = queue.get_bulk_command_detail(grandchild['bulkCommandId'])
    assert grandchild_detail['lineage']['ancestorBulkCommandIds'] == [child['bulkCommandId'], parent['bulkCommandId']]
    assert grandchild_detail['lineage']['lineageDepth'] == 2
