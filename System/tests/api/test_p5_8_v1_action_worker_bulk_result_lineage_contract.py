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


def test_action_job_round15_worker_bulk_result_lineage_contract():
    client = _build_client()
    _, job_a = _create_and_push_request(client, batch_ref='batch-r15-api', suffix='a')
    _, job_b = _create_and_push_request(client, batch_ref='batch-r15-api', suffix='b')

    claim_resp = client.post('/api/v1/actions/worker/claim-next', json={'workerId': 'worker-r15-api', 'operator': 'worker-r15-api', 'batchRef': 'batch-r15-api'})
    assert claim_resp.status_code == 202
    assert claim_resp.get_json()['data']['jobId'] == job_a

    parent_resp = client.post('/api/v1/actions/worker/bulk-command', json={'command': 'release-lease', 'jobIds': [job_a, job_b], 'operator': 'ops-r15-api', 'workerId': 'worker-r15-api', 'reason': 'bulk_release_partial'})
    assert parent_resp.status_code == 202
    parent = parent_resp.get_json()['data']

    child_resp = client.post(f"/api/v1/actions/worker/bulk-results/{parent['bulkCommandId']}/re-execute", json={'selection': 'failed', 'command': 'dead-letter', 'operator': 'ops-r15-api', 'reason': 'rerun_failed_as_dead_letter'})
    assert child_resp.status_code == 202
    child = child_resp.get_json()['data']

    grand_resp = client.post(f"/api/v1/actions/worker/bulk-results/{child['bulkCommandId']}/re-execute", json={'selection': 'all', 'command': 'redrive', 'operator': 'ops-r15-api', 'reason': 'rerun_all_as_redrive'})
    assert grand_resp.status_code == 202
    grand = grand_resp.get_json()['data']

    history_resp = client.get(f"/api/v1/actions/worker/bulk-results?batchRef=batch-r15-api&rootBulkCommandId={parent['bulkCommandId']}&offset=0&limit=10")
    assert history_resp.status_code == 200
    history_payload = history_resp.get_json()['data']
    assert history_payload['total'] == 3
    assert history_payload['items'][0]['bulkCommandId'] == grand['bulkCommandId']

    child_history_resp = client.get(f"/api/v1/actions/worker/bulk-results?batchRef=batch-r15-api&reexecuteOf={parent['bulkCommandId']}&offset=0&limit=10")
    assert child_history_resp.status_code == 200
    child_history_payload = child_history_resp.get_json()['data']
    assert child_history_payload['total'] == 1
    assert child_history_payload['items'][0]['bulkCommandId'] == child['bulkCommandId']

    detail_resp = client.get(f"/api/v1/actions/worker/bulk-results/{child['bulkCommandId']}")
    assert detail_resp.status_code == 200
    detail_payload = detail_resp.get_json()['data']
    assert detail_payload['lineage']['rootBulkCommandId'] == parent['bulkCommandId']
    assert detail_payload['lineage']['reexecuteOf'] == parent['bulkCommandId']

    related_resp = client.get(f"/api/v1/actions/worker/bulk-results/{parent['bulkCommandId']}/related?limit=10")
    assert related_resp.status_code == 200
    related_payload = related_resp.get_json()['data']
    assert related_payload['summary']['totalResults'] == 3
    assert related_payload['items'][0]['bulkCommandId'] == grand['bulkCommandId']
    assert related_payload['items'][-1]['bulkCommandId'] == parent['bulkCommandId']
