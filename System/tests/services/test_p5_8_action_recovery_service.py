from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ecom_v51.services.action_approval_service import ActionApprovalService
from ecom_v51.services.action_delivery_service import ActionDeliveryService
from ecom_v51.services.action_dispatcher_service import ActionDispatcherService
from ecom_v51.services.action_entry_service import ActionEntryService
from ecom_v51.services.action_queue_service import ActionQueueService
from ecom_v51.services.action_worker_service import ActionWorkerService
from ecom_v51.services.action_store import reset_action_store


def test_action_queue_recovery_retry_dead_letter_and_redrive_flow():
    reset_action_store()
    entry = ActionEntryService()
    approval = ActionApprovalService()
    queue = ActionQueueService()
    delivery = ActionDeliveryService(queue)
    dispatcher = ActionDispatcherService(queue)
    worker = ActionWorkerService(queue)

    item = entry.create_request({'actionCode': 'price_update', 'requestedBy': 'evan', 'batchRef': 'batch-r3'})
    approval.submit(item['requestId'], operator='evan')
    approval.approve(item['requestId'], operator='lead')

    pushed = delivery.push(item['requestId'], operator='ops', channel='mock_push_adapter', trace_id='trc_r3')
    job_id = pushed['jobId']

    dispatcher.dispatch(job_id, operator='dispatcher')
    worker.mark_failed(job_id, operator='worker', reason='provider_timeout')

    recovery = queue.get_request_recovery(item['requestId'])
    assert recovery['summary']['failedJobs'] == 1
    assert recovery['summary']['retryableJobs'] == 1
    assert recovery['items'][0]['recommendedOperation'] == 'retry'

    retried = queue.retry_job(job_id, operator='ops', reason='manual_retry')
    assert retried['jobStatus'] == 'queued'
    assert retried['retryCount'] == 1

    dispatcher.dispatch(job_id, operator='dispatcher')
    worker.mark_failed(job_id, operator='worker', reason='provider_timeout_again')
    dead_lettered = worker.mark_dead_letter(job_id, operator='worker', reason='max_retries_exceeded')
    assert dead_lettered['jobStatus'] == 'dead_letter'
    assert dead_lettered['deadLettered'] is True

    recovery_after_dead_letter = queue.get_request_recovery(item['requestId'])
    assert recovery_after_dead_letter['summary']['deadLetterJobs'] == 1
    assert recovery_after_dead_letter['summary']['redriveableJobs'] == 1
    assert recovery_after_dead_letter['items'][0]['recommendedOperation'] == 'redrive'

    redriven = queue.redrive_job(job_id, operator='ops', reason='manual_redrive')
    assert redriven['jobStatus'] == 'queued'
    assert redriven['redriveCount'] == 1

    events = queue.get_job_events(job_id)
    event_types = [item['eventType'] for item in events['events']]
    assert 'job_retry_requested' in event_types
    assert 'job_requeued' in event_types
    assert 'job_dead_lettered' in event_types
    assert 'job_redriven' in event_types
