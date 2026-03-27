from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ecom_v51.api.app import create_app
from ecom_v51.services.action_store import reset_action_store


def _build_client():
    reset_action_store()
    app = create_app("development")
    return app.test_client()


def _create_and_push_request(client, *, batch_ref: str, suffix: str) -> tuple[str, str]:
    create_resp = client.post('/api/v1/actions/requests', json={'actionCode': 'price_update', 'batchRef': batch_ref, 'canonicalSku': f'SKU-{suffix}', 'requestedBy': 'evan'})
    request_id = create_resp.get_json()['data']['requestId']
    client.post(f'/api/v1/actions/requests/{request_id}/submit', json={'operator': 'evan'})
    client.post(f'/api/v1/actions/requests/{request_id}/approve', json={'operator': 'lead'})
    push_resp = client.post(f'/api/v1/actions/requests/{request_id}/push', json={'operator': 'ops', 'channel': 'mock_push_adapter', 'idempotencyKey': f'push-{suffix}'}, headers={'X-Trace-Id': f'trc-{suffix}'})
    job_id = push_resp.get_json()['data']['jobId']
    return request_id, job_id


def test_action_job_round27_worker_bulk_result_related_request_batch_contract():
    client = _build_client()
    request_a, job_a = _create_and_push_request(client, batch_ref='batch-r27-api', suffix='a')
    request_b, job_b = _create_and_push_request(client, batch_ref='batch-r27-api', suffix='b')
    request_c, job_c = _create_and_push_request(client, batch_ref='batch-r27b-api', suffix='c')

    parent_resp = client.post('/api/v1/actions/worker/bulk-command', json={'command': 'release-lease', 'jobIds': [job_a, job_b, job_c], 'operator': 'ops-r27-api', 'reason': 'bulk_release_partial_r27_api'})
    assert parent_resp.status_code == 202
    parent = parent_resp.get_json()['data']

    client.post(f"/api/v1/actions/worker/bulk-results/{parent['bulkCommandId']}/re-execute", json={'selection': 'failed', 'command': 'dead-letter', 'operator': 'ops-r27-api', 'reason': 'rerun_failed_as_dead_letter_r27_api'})
    lineage_resp = client.post(f"/api/v1/actions/worker/bulk-results/{parent['bulkCommandId']}/lineage-command", json={'selection': 'failed', 'command': 'redrive', 'scope': 'entire_lineage', 'operator': 'ops-r27-api', 'reason': 'lineage_redrive_r27_api'})
    assert lineage_resp.status_code == 202
    lineage = lineage_resp.get_json()['data']

    related_resp = client.get(f"/api/v1/actions/worker/bulk-results/{parent['bulkCommandId']}/related?limit=10")
    assert related_resp.status_code == 200
    payload = related_resp.get_json()['data']
    assert payload['summary']['totalResults'] == 3
    assert payload['requestIdSummary'][request_a] == 1
    assert payload['requestIdSummary'][request_b] == 1
    assert payload['requestIdSummary'][request_c] == 1
    assert payload['batchRefSummary']['batch-r27-api'] == 2
    assert payload['batchRefSummary']['batch-r27b-api'] == 1
    assert payload['items'][0]['bulkCommandId'] == lineage['bulkCommandId']
    assert set(payload['items'][0]['requestIds']) == {request_a, request_b, request_c}
    assert set(payload['items'][0]['batchRefs']) == {'batch-r27-api', 'batch-r27b-api'}
