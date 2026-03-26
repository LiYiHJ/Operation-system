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


def test_action_job_round16_worker_bulk_result_timeline_contract():
    client = _build_client()
    _, job_a = _create_and_push_request(client, batch_ref='batch-r16-api', suffix='a')
    _, job_b = _create_and_push_request(client, batch_ref='batch-r16-api', suffix='b')

    claim_resp = client.post('/api/v1/actions/worker/claim-next', json={'workerId': 'worker-r16-api', 'operator': 'worker-r16-api', 'batchRef': 'batch-r16-api'})
    assert claim_resp.status_code == 202
    assert claim_resp.get_json()['data']['jobId'] == job_a

    parent_resp = client.post('/api/v1/actions/worker/bulk-command', json={'command': 'release-lease', 'jobIds': [job_a, job_b], 'operator': 'ops-r16-api', 'workerId': 'worker-r16-api', 'reason': 'bulk_release_partial'})
    assert parent_resp.status_code == 202
    parent = parent_resp.get_json()['data']

    child_resp = client.post(f"/api/v1/actions/worker/bulk-results/{parent['bulkCommandId']}/re-execute", json={'selection': 'failed', 'command': 'dead-letter', 'operator': 'ops-r16-api', 'reason': 'rerun_failed_as_dead_letter'})
    assert child_resp.status_code == 202
    child = child_resp.get_json()['data']

    grand_resp = client.post(f"/api/v1/actions/worker/bulk-results/{child['bulkCommandId']}/re-execute", json={'selection': 'all', 'command': 'redrive', 'operator': 'ops-r16-api', 'reason': 'rerun_all_as_redrive'})
    assert grand_resp.status_code == 202
    grand = grand_resp.get_json()['data']

    history_resp = client.get(f"/api/v1/actions/worker/bulk-results?batchRef=batch-r16-api&parentBulkCommandId={parent['bulkCommandId']}&offset=0&limit=10")
    assert history_resp.status_code == 200
    history_payload = history_resp.get_json()['data']
    assert history_payload['total'] == 1
    assert history_payload['items'][0]['bulkCommandId'] == child['bulkCommandId']

    depth_resp = client.get('/api/v1/actions/worker/bulk-results?batchRef=batch-r16-api&lineageDepth=2&offset=0&limit=10')
    assert depth_resp.status_code == 200
    depth_payload = depth_resp.get_json()['data']
    assert depth_payload['total'] == 1
    assert depth_payload['items'][0]['bulkCommandId'] == grand['bulkCommandId']

    children_resp = client.get('/api/v1/actions/worker/bulk-results?batchRef=batch-r16-api&hasChildren=true&offset=0&limit=10')
    assert children_resp.status_code == 200
    children_payload = children_resp.get_json()['data']
    assert children_payload['lineageSummary']['resultsWithChildren'] == 2

    timeline_resp = client.get(f"/api/v1/actions/worker/bulk-results/{parent['bulkCommandId']}/timeline?limit=10")
    assert timeline_resp.status_code == 200
    timeline_payload = timeline_resp.get_json()['data']
    assert timeline_payload['total'] == 3
    assert timeline_payload['items'][0]['bulkCommandId'] == parent['bulkCommandId']
    assert timeline_payload['items'][-1]['bulkCommandId'] == grand['bulkCommandId']
    assert timeline_payload['commandSummary']['release-lease'] == 1
