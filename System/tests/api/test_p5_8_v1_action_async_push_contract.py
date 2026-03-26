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


def test_action_async_push_returns_job_and_job_detail_surface():
    client = _build_client()
    create_resp = client.post('/api/v1/actions/requests', json={'actionCode': 'price_update', 'batchRef': 'batch-async-1', 'canonicalSku': 'SKU-1', 'requestedBy': 'evan'})
    request_id = create_resp.get_json()['data']['requestId']
    client.post(f'/api/v1/actions/requests/{request_id}/submit', json={'operator': 'evan'})
    client.post(f'/api/v1/actions/requests/{request_id}/approve', json={'operator': 'lead'})

    push_resp = client.post(
        f'/api/v1/actions/requests/{request_id}/push',
        json={'operator': 'ops', 'channel': 'mock_push_adapter', 'idempotencyKey': 'idem-async-1'},
        headers={'X-Trace-Id': 'trc_async_1'},
    )
    assert push_resp.status_code == 202
    payload = push_resp.get_json()['data']
    assert payload['deliveryStatus'] == 'accepted'
    assert payload['queueStatus'] == 'queued'
    assert payload['executionMode'] == 'async_queue'
    assert payload['jobId']

    job_resp = client.get(f"/api/v1/jobs/{payload['jobId']}")
    assert job_resp.status_code == 200
    job_payload = job_resp.get_json()['data']
    assert job_payload['jobStatus'] == 'queued'
    assert job_payload['requestId'] == request_id

    events_resp = client.get(f"/api/v1/jobs/{payload['jobId']}/events")
    assert events_resp.status_code == 200
    events_payload = events_resp.get_json()['data']
    assert events_payload['total'] >= 2
