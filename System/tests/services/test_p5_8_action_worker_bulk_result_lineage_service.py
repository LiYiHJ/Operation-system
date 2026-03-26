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


def test_action_queue_round15_bulk_result_lineage_and_related_history_surface():
    reset_action_store()
    entry = ActionEntryService()
    approval = ActionApprovalService()
    queue = ActionQueueService()
    delivery = ActionDeliveryService(queue)

    _, job_a = _create_and_push(entry, approval, delivery, batch_ref='batch-r15', suffix='a')
    _, job_b = _create_and_push(entry, approval, delivery, batch_ref='batch-r15', suffix='b')

    claimed = queue.claim_next_job(worker_id='worker-r15', operator='worker-r15', batch_ref='batch-r15')
    assert claimed['jobId'] == job_a

    parent = queue.execute_bulk_command(
        command='release-lease',
        job_ids=[job_a, job_b],
        operator='ops-r15',
        worker_id='worker-r15',
        reason='bulk_release_partial',
    )
    child = queue.reexecute_bulk_command(
        parent['bulkCommandId'],
        selection='failed',
        command='dead-letter',
        operator='ops-r15',
        reason='rerun_failed_as_dead_letter',
    )
    grandchild = queue.reexecute_bulk_command(
        child['bulkCommandId'],
        selection='all',
        command='redrive',
        operator='ops-r15',
        reason='rerun_all_as_redrive',
    )

    root_history = queue.get_bulk_command_history(batch_ref='batch-r15', root_bulk_command_id=parent['bulkCommandId'], offset=0, limit=10)
    assert root_history['total'] == 3
    assert root_history['items'][0]['bulkCommandId'] == grandchild['bulkCommandId']

    child_history = queue.get_bulk_command_history(batch_ref='batch-r15', reexecute_of=parent['bulkCommandId'], offset=0, limit=10)
    assert child_history['total'] == 1
    assert child_history['items'][0]['bulkCommandId'] == child['bulkCommandId']

    parent_detail = queue.get_bulk_command_detail(parent['bulkCommandId'])
    assert parent_detail['lineage']['rootBulkCommandId'] == parent['bulkCommandId']
    assert parent_detail['lineage']['childCount'] == 1
    assert parent_detail['lineage']['latestChildBulkCommandId'] == child['bulkCommandId']

    child_detail = queue.get_bulk_command_detail(child['bulkCommandId'])
    assert child_detail['lineage']['reexecuteOf'] == parent['bulkCommandId']
    assert child_detail['lineage']['rootBulkCommandId'] == parent['bulkCommandId']
    assert child_detail['lineage']['childCount'] == 1
    assert child_detail['lineage']['latestChildBulkCommandId'] == grandchild['bulkCommandId']

    related = queue.get_bulk_command_related(parent['bulkCommandId'], limit=10)
    assert related['summary']['totalResults'] == 3
    assert related['items'][0]['bulkCommandId'] == grandchild['bulkCommandId']
    assert related['items'][-1]['bulkCommandId'] == parent['bulkCommandId']

    grandchild_detail = queue.get_bulk_command_detail(grandchild['bulkCommandId'])
    assert grandchild_detail['lineage']['reexecuteOf'] == child['bulkCommandId']
    assert grandchild_detail['lineage']['rootBulkCommandId'] == parent['bulkCommandId']
    assert grandchild_detail['relatedResults'][0]['bulkCommandId'] == grandchild['bulkCommandId']
