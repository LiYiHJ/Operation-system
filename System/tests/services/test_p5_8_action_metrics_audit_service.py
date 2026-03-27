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
from ecom_v51.services.action_store import reset_action_store
from ecom_v51.services.action_worker_service import ActionWorkerService


def _create_and_push(entry, approval, delivery, *, action_code: str, batch_ref: str, suffix: str) -> tuple[str, str]:
    item = entry.create_request(
        {
            'actionCode': action_code,
            'requestedBy': 'evan',
            'batchRef': batch_ref,
            'canonicalSku': f'SKU-{suffix}',
        }
    )
    approval.submit(item['requestId'], operator='evan')
    approval.approve(item['requestId'], operator='lead')
    pushed = delivery.push(item['requestId'], operator='ops', channel='mock_push_adapter', trace_id=f'trc-{suffix}')
    return item['requestId'], pushed['jobId']


def test_action_queue_round6_metrics_failure_buckets_and_audit_surfaces():
    reset_action_store()
    entry = ActionEntryService()
    approval = ActionApprovalService()
    queue = ActionQueueService()
    delivery = ActionDeliveryService(queue)
    dispatcher = ActionDispatcherService(queue)
    worker = ActionWorkerService(queue)

    req_a, job_a = _create_and_push(entry, approval, delivery, action_code='price_update', batch_ref='batch-r6', suffix='a')
    req_b, job_b = _create_and_push(entry, approval, delivery, action_code='inventory_adjustment', batch_ref='batch-r6', suffix='b')
    _req_c, job_c = _create_and_push(entry, approval, delivery, action_code='price_update', batch_ref='batch-r6b', suffix='c')

    dispatcher.dispatch(job_a, operator='dispatcher')
    worker.mark_failed(job_a, operator='worker', reason='provider_timeout')

    dispatcher.dispatch(job_b, operator='dispatcher')
    worker.mark_failed(job_b, operator='worker', reason='provider_reject')
    queue.mark_dead_letter(job_b, operator='ops', reason='provider_reject_dead', idempotency_key='dead-r6')

    dispatcher.dispatch(job_c, operator='dispatcher')
    worker.mark_succeeded(job_c, operator='worker', external_ref='ext-r6-c')

    metrics = queue.get_jobs_metrics(batch_ref='batch-r6', limit=10)
    assert metrics['summary']['totalJobs'] == 2
    assert metrics['summary']['finishedJobs'] == 2
    assert metrics['queueLagMetrics']['samples'] == 2
    assert metrics['turnaroundMetrics']['samples'] == 2
    assert metrics['topLaggingJobsTotal'] == 2

    failure = queue.get_failure_buckets(batch_ref='batch-r6', limit=10)
    assert failure['summary']['totalFailedJobs'] == 2
    assert failure['reasonSummary']['provider_timeout'] == 1
    assert failure['reasonSummary']['provider_reject_dead'] == 1
    assert failure['reasonBucketSummary']['timeout'] == 1
    assert failure['reasonBucketSummary']['validation_or_reject'] == 1

    job_audit = queue.get_job_audit(job_b)
    assert job_audit['jobId'] == job_b
    assert job_audit['jobStatus'] == 'dead_letter'
    assert job_audit['eventTypeSummary']['job_dead_lettered'] == 1
    assert job_audit['metrics']['turnaroundSeconds'] is not None

    request_audit = queue.get_request_audit(req_a)
    assert request_audit['requestId'] == req_a
    assert request_audit['summary']['failedJobs'] == 1
    assert request_audit['failureBuckets']['summary']['totalFailedJobs'] == 1
    assert request_audit['timelineTotal'] >= 4

    batch_audit = queue.get_batch_audit('batch-r6')
    assert batch_audit['batchRef'] == 'batch-r6'
    assert batch_audit['summary']['totalJobs'] == 2
    assert batch_audit['failureBuckets']['summary']['totalFailedJobs'] == 2
    assert batch_audit['metrics']['summary']['totalJobs'] == 2
    assert batch_audit['timelineTotal'] >= 7
