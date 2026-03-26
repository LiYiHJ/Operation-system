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
    create_resp = client.post('/api/v1/actions/requests', json={'actionCode': 'price_update', 'batchRef': batch_ref, 'canonicalSku': f'SKU-{suffix}', 'requestedBy': 'evan'})
    request_id = create_resp.get_json()['data']['requestId']
    client.post(f'/api/v1/actions/requests/{request_id}/submit', json={'operator': 'evan'})
    client.post(f'/api/v1/actions/requests/{request_id}/approve', json={'operator': 'lead'})
    push_resp = client.post(f'/api/v1/actions/requests/{request_id}/push', json={'operator': 'ops', 'channel': 'mock_push_adapter', 'idempotencyKey': f'push-{suffix}'}, headers={'X-Trace-Id': f'trc-{suffix}'})
    job_id = push_resp.get_json()['data']['jobId']
    return request_id, job_id


def test_action_job_round13_bulk_result_history_contract():
    client = _build_client()
    _, job_a = _create_and_push_request(client, batch_ref='batch-r13-api', suffix='a')
    _, job_b = _create_and_push_request(client, batch_ref='batch-r13-api', suffix='b')
    client.post('/api/v1/actions/worker/claim-next', json={'workerId': 'worker-r13-api', 'operator': 'worker-r13-api', 'batchRef': 'batch-r13-api'})

    bulk_resp = client.post('/api/v1/actions/worker/bulk-command', json={'command': 'mark-failed', 'jobIds': [job_a, job_b], 'operator': 'ops-r13-api', 'workerId': 'worker-r13-api', 'reason': 'bulk_failed'})
    assert bulk_resp.status_code == 202
    bulk_payload = bulk_resp.get_json()['data']

    history_resp = client.get('/api/v1/actions/worker/bulk-results?batchRef=batch-r13-api&command=mark-failed&limit=10')
    assert history_resp.status_code == 200
    history_payload = history_resp.get_json()['data']
    assert history_payload['scope']['batchRef'] == 'batch-r13-api'
    assert history_payload['scope']['command'] == 'mark-failed'
    assert history_payload['summary']['totalCommands'] == 1
    assert history_payload['items'][0]['bulkCommandId'] == bulk_payload['bulkCommandId']

    detail_resp = client.get(f"/api/v1/actions/worker/bulk-results/{bulk_payload['bulkCommandId']}")
    assert detail_resp.status_code == 200
    detail_payload = detail_resp.get_json()['data']
    assert detail_payload['bulkCommandId'] == bulk_payload['bulkCommandId']
    assert detail_payload['bulkCommand']['summary']['requestedJobs'] == 2
    assert detail_payload['bulkCommand']['summary']['failedJobs'] == 1
