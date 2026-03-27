from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ecom_v51.api.app import create_app
from ecom_v51.services.action_store import reset_action_store


def _build_client():
    reset_action_store()
    app = create_app('development')
    return app.test_client()


def test_action_request_jobs_contract_and_timeline_extensions():
    client = _build_client()
    create_resp = client.post('/api/v1/actions/requests', json={'actionCode': 'price_update', 'batchRef': 'batch-async-2', 'canonicalSku': 'SKU-2', 'requestedBy': 'evan'})
    request_id = create_resp.get_json()['data']['requestId']
    client.post(f'/api/v1/actions/requests/{request_id}/submit', json={'operator': 'evan'})
    client.post(f'/api/v1/actions/requests/{request_id}/approve', json={'operator': 'lead'})

    push_resp = client.post(
        f'/api/v1/actions/requests/{request_id}/push',
        json={'operator': 'ops', 'channel': 'mock_push_adapter', 'idempotencyKey': 'idem-async-2'},
        headers={'X-Trace-Id': 'trc_async_2'},
    )
    job_id = push_resp.get_json()['data']['jobId']

    jobs_resp = client.get(f'/api/v1/actions/requests/{request_id}/jobs')
    assert jobs_resp.status_code == 200
    jobs_payload = jobs_resp.get_json()['data']
    assert jobs_payload['total'] == 1
    assert jobs_payload['items'][0]['jobId'] == job_id

    callback_resp = client.post(
        f'/api/v1/actions/requests/{request_id}/callback',
        json={'eventType': 'delivery_update', 'providerStatus': 'failed', 'externalRef': 'ext-async-2'},
    )
    assert callback_resp.status_code == 202
    assert callback_resp.get_json()['data']['jobId'] == job_id

    compensation_resp = client.post(
        f'/api/v1/actions/requests/{request_id}/compensation/evaluate',
        json={'operator': 'ops'},
    )
    assert compensation_resp.status_code == 202
    assert compensation_resp.get_json()['data']['jobId'] == job_id

    events_resp = client.get(f'/api/v1/jobs/{job_id}/events')
    assert events_resp.status_code == 200
    events_payload = events_resp.get_json()['data']
    event_types = [item['eventType'] for item in events_payload['events']]
    assert 'callback_received' in event_types
    assert 'compensation_evaluated' in event_types
