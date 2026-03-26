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


def test_action_queue_round4_transition_guards_and_idempotent_recovery_commands():
    reset_action_store()
    entry = ActionEntryService()
    approval = ActionApprovalService()
    queue = ActionQueueService()
    delivery = ActionDeliveryService(queue)
    dispatcher = ActionDispatcherService(queue)
    worker = ActionWorkerService(queue)

    item = entry.create_request({'actionCode': 'price_update', 'requestedBy': 'evan', 'batchRef': 'batch-r4'})
    approval.submit(item['requestId'], operator='evan')
    approval.approve(item['requestId'], operator='lead')

    pushed = delivery.push(item['requestId'], operator='ops', channel='mock_push_adapter', trace_id='trc_r4')
    job_id = pushed['jobId']

    dispatcher.dispatch(job_id, operator='dispatcher')
    worker.mark_failed(job_id, operator='worker', reason='provider_timeout')

    recovery_failed = queue.get_request_recovery(item['requestId'])
    assert recovery_failed['summary']['failedJobs'] == 1
    assert recovery_failed['summary']['retryableJobs'] == 1
    assert recovery_failed['statusSummary']['failed'] == 1
    assert recovery_failed['timelineTotal'] >= 4
    assert 'retry' in recovery_failed['items'][0]['availableCommands']
    assert 'dead-letter' in recovery_failed['items'][0]['availableCommands']

    retried_once = queue.retry_job(job_id, operator='ops', reason='manual_retry', idempotency_key='retry-r4')
    retried_twice = queue.retry_job(job_id, operator='ops', reason='manual_retry', idempotency_key='retry-r4')
    assert retried_once['retryCount'] == 1
    assert retried_twice['retryCount'] == 1
    assert retried_twice['jobStatus'] == 'queued'

    dispatcher.dispatch(job_id, operator='dispatcher')
    worker.mark_failed(job_id, operator='worker', reason='provider_timeout_again')
    dead_lettered = queue.mark_dead_letter(job_id, operator='ops', reason='manual_dead_letter')
    assert dead_lettered['jobStatus'] == 'dead_letter'
    assert dead_lettered['recommendedOperation'] == 'redrive'

    redriven_once = queue.redrive_job(job_id, operator='ops', reason='manual_redrive', idempotency_key='redrive-r4')
    redriven_twice = queue.redrive_job(job_id, operator='ops', reason='manual_redrive', idempotency_key='redrive-r4')
    assert redriven_once['redriveCount'] == 1
    assert redriven_twice['redriveCount'] == 1
    assert redriven_twice['jobStatus'] == 'queued'

    recovery_after = queue.get_request_recovery(item['requestId'])
    assert recovery_after['summary']['queuedJobs'] == 1
    assert recovery_after['latestJobStatus'] == 'queued'
    assert recovery_after['latestRecoveryOperation'] == 'redrive'
    event_types = [item['eventType'] for item in recovery_after['timeline']]
    assert 'job_retry_requested' in event_types
    assert 'job_redriven' in event_types
