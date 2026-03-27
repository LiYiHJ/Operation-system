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


def test_action_queue_round5_dashboard_and_batch_health_summary():
    reset_action_store()
    entry = ActionEntryService()
    approval = ActionApprovalService()
    queue = ActionQueueService()
    delivery = ActionDeliveryService(queue)
    dispatcher = ActionDispatcherService(queue)
    worker = ActionWorkerService(queue)

    req_a, job_a = _create_and_push(entry, approval, delivery, action_code='price_update', batch_ref='batch-r5', suffix='a')
    req_b, job_b = _create_and_push(entry, approval, delivery, action_code='inventory_adjustment', batch_ref='batch-r5', suffix='b')
    req_c, job_c = _create_and_push(entry, approval, delivery, action_code='price_update', batch_ref='batch-r5b', suffix='c')

    dispatcher.dispatch(job_a, operator='dispatcher')
    worker.mark_failed(job_a, operator='worker', reason='provider_timeout')
    queue.retry_job(job_a, operator='ops', reason='manual_retry', idempotency_key='retry-r5-service')

    dispatcher.dispatch(job_b, operator='dispatcher')
    worker.mark_failed(job_b, operator='worker', reason='provider_reject')
    queue.mark_dead_letter(job_b, operator='ops', reason='manual_dead_letter', idempotency_key='dead-r5-service')

    dispatcher.dispatch(job_c, operator='dispatcher')
    worker.mark_succeeded(job_c, operator='worker', external_ref='ext-r5-c')

    dashboard = queue.get_jobs_dashboard(batch_ref='batch-r5', limit=5)
    assert dashboard['summary']['totalJobs'] == 2
    assert dashboard['summary']['queuedJobs'] == 1
    assert dashboard['summary']['deadLetterJobs'] == 1
    assert dashboard['statusSummary']['queued'] == 1
    assert dashboard['statusSummary']['dead_letter'] == 1
    assert dashboard['actionCodeSummary']['price_update'] == 1
    assert dashboard['actionCodeSummary']['inventory_adjustment'] == 1
    assert dashboard['latestJobsTotal'] == 2
    assert len(dashboard['recentRecoveryEvents']) >= 2
    recovery_types = {item['eventType'] for item in dashboard['recentRecoveryEvents']}
    assert 'job_retry_requested' in recovery_types
    assert 'job_dead_lettered' in recovery_types

    batch_health = queue.get_batch_queue_health('batch-r5')
    assert batch_health['requestSummary']['totalRequests'] == 2
    assert batch_health['requestSummary']['requestsWithFailures'] == 0
    assert batch_health['requestSummary']['requestsWithDeadLetter'] == 1
    assert batch_health['requestSummary']['requestsNeedingAttention'] == 1
    assert batch_health['summary']['totalJobs'] == 2
    assert batch_health['summary']['deadLetterJobs'] == 1
    assert batch_health['timelineTotal'] >= 6
    assert len(batch_health['recentRecoveryEvents']) >= 2

    summary = queue.list_jobs_summary(batch_ref='batch-r5', limit=10)
    assert summary['total'] == 2
    assert summary['summary']['deadLetterJobs'] == 1
    assert summary['summary']['queuedJobs'] == 1
    assert summary['filters']['batchRef'] == 'batch-r5'
    item_job_ids = {item['jobId'] for item in summary['items']}
    assert job_a in item_job_ids
    assert job_b in item_job_ids
