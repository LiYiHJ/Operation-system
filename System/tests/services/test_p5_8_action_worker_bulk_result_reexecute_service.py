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


def test_action_queue_round14_bulk_result_history_filters_pagination_and_reexecute_surface():
    reset_action_store()
    entry = ActionEntryService()
    approval = ActionApprovalService()
    queue = ActionQueueService()
    delivery = ActionDeliveryService(queue)

    _, job_a = _create_and_push(entry, approval, delivery, batch_ref='batch-r14', suffix='a')
    _, job_b = _create_and_push(entry, approval, delivery, batch_ref='batch-r14', suffix='b')

    claimed = queue.claim_next_job(worker_id='worker-r14', operator='worker-r14', batch_ref='batch-r14')
    assert claimed['jobId'] == job_a

    first_bulk = queue.execute_bulk_command(
        command='release-lease',
        job_ids=[job_a, job_b],
        operator='ops-r14',
        worker_id='worker-r14',
        reason='bulk_release_partial',
    )
    assert first_bulk['summary']['requestedJobs'] == 2
    assert first_bulk['summary']['succeededJobs'] == 1
    assert first_bulk['summary']['failedJobs'] == 1

    history = queue.get_bulk_command_history(
        batch_ref='batch-r14',
        command='release-lease',
        worker_id='worker-r14',
        action_code='price_update',
        result_mode='partial',
        offset=0,
        limit=1,
    )
    assert history['scope']['resultMode'] == 'partial'
    assert history['scope']['actionCode'] == 'price_update'
    assert history['pagination']['returned'] == 1
    assert history['summary']['commandsPartial'] == 1
    assert history['items'][0]['bulkCommandId'] == first_bulk['bulkCommandId']

    detail = queue.get_bulk_command_detail(first_bulk['bulkCommandId'])
    assert detail['secondaryActions']['failedJobCount'] == 1
    assert detail['failedJobIds'] == [job_b]
    assert 'dead-letter' in detail['secondaryActions']['rerunnableCommands']

    second_bulk = queue.reexecute_bulk_command(
        first_bulk['bulkCommandId'],
        selection='failed',
        command='dead-letter',
        operator='ops-r14',
        reason='rerun_failed_as_dead_letter',
    )
    assert second_bulk['reexecuteOf'] == first_bulk['bulkCommandId']
    assert second_bulk['summary']['requestedJobs'] == 1
    assert second_bulk['summary']['succeededJobs'] == 1
    assert second_bulk['summary']['failedJobs'] == 0

    history_page_1 = queue.get_bulk_command_history(batch_ref='batch-r14', offset=0, limit=1)
    history_page_2 = queue.get_bulk_command_history(batch_ref='batch-r14', offset=1, limit=1)
    assert history_page_1['total'] == 2
    assert history_page_1['pagination']['hasMore'] is True
    assert history_page_2['pagination']['returned'] == 1
    assert history_page_2['items'][0]['bulkCommandId'] == first_bulk['bulkCommandId']

    rerun_history = queue.get_bulk_command_history(batch_ref='batch-r14', command='dead-letter', result_mode='succeeded', offset=0, limit=10)
    assert rerun_history['summary']['commandsFullySucceeded'] == 1
    assert rerun_history['items'][0]['bulkCommandId'] == second_bulk['bulkCommandId']
