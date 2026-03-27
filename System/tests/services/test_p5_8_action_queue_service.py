from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ecom_v51.services.action_approval_service import ActionApprovalService
from ecom_v51.services.action_callback_service import ActionCallbackService
from ecom_v51.services.action_compensation_service import ActionCompensationService
from ecom_v51.services.action_delivery_service import ActionDeliveryService
from ecom_v51.services.action_entry_service import ActionEntryService
from ecom_v51.services.action_queue_service import ActionQueueService
from ecom_v51.services.action_store import reset_action_store


def test_action_queue_service_request_jobs_and_timeline_extensions():
    reset_action_store()
    entry = ActionEntryService()
    approval = ActionApprovalService()
    queue = ActionQueueService()
    delivery = ActionDeliveryService(queue)
    callback = ActionCallbackService(queue)
    compensation = ActionCompensationService(queue)

    item = entry.create_request({'actionCode': 'price_update', 'requestedBy': 'evan', 'batchRef': 'batch-8'})
    approval.submit(item['requestId'], operator='evan')
    approval.approve(item['requestId'], operator='lead')

    pushed = delivery.push(item['requestId'], operator='ops', channel='mock_push_adapter', trace_id='trc_demo', idempotency_key='idem-1')
    job_id = pushed['jobId']
    assert job_id

    jobs = delivery.list_request_jobs(item['requestId'])
    assert jobs['total'] == 1
    assert jobs['items'][0]['jobId'] == job_id

    callback_result = callback.ingest_callback(item['requestId'], event_type='delivery_update', provider_status='failed', external_ref='ext-1')
    assert callback_result['jobId'] == job_id

    compensation_result = compensation.evaluate_compensation(item['requestId'], operator='ops')
    assert compensation_result['jobId'] == job_id

    events = queue.get_job_events(job_id)
    event_types = [item['eventType'] for item in events['events']]
    assert 'job_accepted' in event_types
    assert 'job_queued' in event_types
    assert 'callback_received' in event_types
    assert 'compensation_evaluated' in event_types
