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


def test_action_queue_round17_lineage_filters_and_bulk_followup_surface():
    reset_action_store()
    entry = ActionEntryService()
    approval = ActionApprovalService()
    queue = ActionQueueService()
    delivery = ActionDeliveryService(queue)

    _, job_a = _create_and_push(entry, approval, delivery, batch_ref='batch-r17', suffix='a')
    _, job_b = _create_and_push(entry, approval, delivery, batch_ref='batch-r17', suffix='b')
    _, job_c = _create_and_push(entry, approval, delivery, batch_ref='batch-r17', suffix='c')

    claimed = queue.claim_next_job(worker_id='worker-r17', operator='worker-r17', batch_ref='batch-r17')
    assert claimed['jobId'] == job_a

    parent = queue.execute_bulk_command(
        command='release-lease',
        job_ids=[job_a, job_b, job_c],
        operator='ops-r17',
        worker_id='worker-r17',
        reason='bulk_release_partial_r17',
    )
    assert parent['summary']['succeededJobs'] == 1
    assert parent['summary']['failedJobs'] == 2

    child = queue.reexecute_bulk_command(
        parent['bulkCommandId'],
        selection='failed',
        command='dead-letter',
        operator='ops-r17',
        reason='rerun_failed_as_dead_letter_r17',
    )
    assert child['summary']['succeededJobs'] == 2
    assert child['selection'] == 'failed'
    assert child['reexecuteCommand'] == 'dead-letter'

    history = queue.get_bulk_command_history(batch_ref='batch-r17', selection='failed', reexecute_command='dead-letter', offset=0, limit=10)
    assert history['total'] == 1
    assert history['items'][0]['bulkCommandId'] == child['bulkCommandId']
    assert history['selectionSummary']['failed'] == 1
    assert history['reexecuteCommandSummary']['dead-letter'] == 1

    timeline = queue.get_bulk_command_timeline(
        parent['bulkCommandId'],
        event_type='bulk_result_reexecuted',
        command='dead-letter',
        action_code='price_update',
        lineage_depth=1,
        limit=10,
    )
    assert timeline['total'] == 1
    assert timeline['items'][0]['bulkCommandId'] == child['bulkCommandId']
    assert timeline['eventTypeSummary']['bulk_result_reexecuted'] == 1
    assert timeline['actionCodeSummary']['price_update'] == 1
    assert timeline['lineageSummary']['childEvents'] == 1

    lineage_followup = queue.reexecute_bulk_command_lineage(
        parent['bulkCommandId'],
        selection='failed',
        command='redrive',
        scope='entire_lineage',
        operator='ops-r17',
        reason='lineage_redrive_r17',
    )
    assert lineage_followup['summary']['succeededJobs'] == 2
    assert lineage_followup['lineageScope'] == 'entire_lineage'
    assert lineage_followup['sourceBulkCommandIds'] == [parent['bulkCommandId']]

    followup_detail = queue.get_bulk_command_detail(lineage_followup['bulkCommandId'])
    bulk_command = followup_detail['bulkCommand']
    assert bulk_command['lineageScope'] == 'entire_lineage'
    assert bulk_command['sourceBulkCommandIds'] == [parent['bulkCommandId']]
