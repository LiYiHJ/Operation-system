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


def test_action_job_round7_worker_store_contract():
    client = _build_client()
    _request_a, job_a = _create_and_push_request(client, batch_ref='batch-r7-api', suffix='a')
    _request_b, job_b = _create_and_push_request(client, batch_ref='batch-r7-api', suffix='b')

    overview_resp = client.get('/api/v1/actions/worker/overview?batchRef=batch-r7-api&limit=10')
    assert overview_resp.status_code == 200
    overview_payload = overview_resp.get_json()['data']
    assert overview_payload['summary']['queuedJobs'] == 2
    assert overview_payload['nextJobsTotal'] == 2

    claim_resp = client.post('/api/v1/actions/worker/claim-next', json={'workerId': 'worker-r7', 'operator': 'worker-r7', 'batchRef': 'batch-r7-api'})
    assert claim_resp.status_code == 202
    claim_payload = claim_resp.get_json()['data']
    assert claim_payload['jobStatus'] == 'running'
    assert claim_payload['workerId'] == 'worker-r7'

    heartbeat_resp = client.post(f"/api/v1/jobs/{claim_payload['jobId']}/heartbeat", json={'workerId': 'worker-r7', 'operator': 'worker-r7', 'note': 'alive'})
    assert heartbeat_resp.status_code == 202
    heartbeat_payload = heartbeat_resp.get_json()['data']
    assert heartbeat_payload['jobId'] == claim_payload['jobId']
    assert heartbeat_payload['leaseHeartbeatAt']

    mismatch_resp = client.post(f"/api/v1/jobs/{claim_payload['jobId']}/heartbeat", json={'workerId': 'worker-other', 'operator': 'worker-other'})
    assert mismatch_resp.status_code == 409
    assert mismatch_resp.get_json()['error']['code'] == 'worker_mismatch'

    store_resp = client.get('/api/v1/actions/store/overview?batchRef=batch-r7-api&limit=10')
    assert store_resp.status_code == 200
    store_payload = store_resp.get_json()['data']
    assert store_payload['summary']['totalRequests'] == 2
    assert store_payload['summary']['totalJobs'] == 2
    assert store_payload['summary']['totalDeliveries'] == 2
    assert store_payload['latestJobsTotal'] == 2
    assert {item['jobId'] for item in store_payload['latestJobs']} == {job_a, job_b}
