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


def _create_and_push_request(client, *, batch_ref: str, suffix: str) -> tuple[str, str]:
    create_resp = client.post(
        '/api/v1/actions/requests',
        json={'actionCode': 'price_update', 'batchRef': batch_ref, 'canonicalSku': f'SKU-{suffix}', 'requestedBy': 'evan'},
    )
    request_id = create_resp.get_json()['data']['requestId']
    client.post(f'/api/v1/actions/requests/{request_id}/submit', json={'operator': 'evan'})
    client.post(f'/api/v1/actions/requests/{request_id}/approve', json={'operator': 'lead'})
    push_resp = client.post(
        f'/api/v1/actions/requests/{request_id}/push',
        json={'operator': 'ops', 'channel': 'mock_push_adapter', 'idempotencyKey': f'push-{suffix}'},
        headers={'X-Trace-Id': f'trc-{suffix}'},
    )
    job_id = push_resp.get_json()['data']['jobId']
    return request_id, job_id


def test_action_job_round8_worker_stale_and_job_drilldown_contract():
    client = _build_client()
    _request_id, job_id = _create_and_push_request(client, batch_ref='batch-r8-api', suffix='a')

    claim_resp = client.post('/api/v1/actions/worker/claim-next', json={'workerId': 'worker-r8', 'operator': 'worker-r8', 'batchRef': 'batch-r8-api'})
    assert claim_resp.status_code == 202

    # expire lease via detail lookup against in-memory store
    detail_resp = client.get(f'/api/v1/jobs/{job_id}')
    assert detail_resp.status_code == 200
    from ecom_v51.services.action_queue_service import ActionQueueService
    queue = ActionQueueService()
    job = queue.get_job_detail(job_id)
    job['leaseExpiresAt'] = '2000-01-01T00:00:00+00:00'
    job['leaseHeartbeatAt'] = '2000-01-01T00:00:00+00:00'

    stale_resp = client.get('/api/v1/actions/worker/stale-jobs?batchRef=batch-r8-api&limit=10')
    assert stale_resp.status_code == 200
    stale_payload = stale_resp.get_json()['data']
    assert stale_payload['summary']['staleJobs'] == 1
    assert stale_payload['items'][0]['jobId'] == job_id

    audit_resp = client.get(f'/api/v1/actions/jobs/{job_id}/audit')
    assert audit_resp.status_code == 200
    audit_payload = audit_resp.get_json()['data']
    assert audit_payload['jobId'] == job_id
    assert 'timeline' in audit_payload

    events_resp = client.get(f'/api/v1/jobs/{job_id}/events')
    assert events_resp.status_code == 200
    events_payload = events_resp.get_json()['data']
    assert events_payload['jobId'] == job_id
    assert events_payload['total'] >= 2
