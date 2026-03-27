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


def test_action_job_round31_worker_bulk_result_related_status_error_contract():
    client = _build_client()
    _, job_a = _create_and_push_request(client, batch_ref='batch-r31-api', suffix='a')
    _, job_b = _create_and_push_request(client, batch_ref='batch-r31-api', suffix='b')
    _, job_c = _create_and_push_request(client, batch_ref='batch-r31-api', suffix='c')

    claim_a = client.post('/api/v1/actions/worker/claim-next', json={'workerId': 'worker-r31-api-a', 'operator': 'worker-r31-api-a', 'batchRef': 'batch-r31-api'})
    claim_c = client.post('/api/v1/actions/worker/claim-next', json={'workerId': 'worker-r31-api-c', 'operator': 'worker-r31-api-c', 'batchRef': 'batch-r31-api'})
    assert claim_a.status_code == 202
    assert claim_c.status_code == 202

    parent_resp = client.post('/api/v1/actions/worker/bulk-command', json={
        'command': 'mark-succeeded',
        'jobIds': [job_a, job_b, job_c],
        'operator': 'ops-r31-api',
        'workerId': 'worker-r31-api-a',
        'externalRef': 'ext-parent-r31-api',
        'note': 'parent-note-r31-api',
    })
    assert parent_resp.status_code == 202
    parent = parent_resp.get_json()['data']

    rerun_resp = client.post(f"/api/v1/actions/worker/bulk-results/{parent['bulkCommandId']}/re-execute", json={
        'selection': 'failed',
        'command': 'dead-letter',
        'operator': 'ops-r31-api',
        'reason': 'rerun_failed_dead_letter_r31_api',
        'note': 'rerun-note-r31-api',
    })
    assert rerun_resp.status_code == 202
    rerun = rerun_resp.get_json()['data']

    lineage_resp = client.post(f"/api/v1/actions/worker/bulk-results/{parent['bulkCommandId']}/lineage-command", json={
        'selection': 'failed',
        'command': 'redrive',
        'scope': 'entire_lineage',
        'operator': 'ops-r31-api',
        'reason': 'lineage_redrive_r31_api',
        'note': 'lineage-note-r31-api',
    })
    assert lineage_resp.status_code == 202
    lineage = lineage_resp.get_json()['data']

    related_resp = client.get(f"/api/v1/actions/worker/bulk-results/{parent['bulkCommandId']}/related?limit=10")
    assert related_resp.status_code == 200
    payload = related_resp.get_json()['data']
    assert payload['summary']['totalResults'] == 3
    assert payload['itemStatusSummary']['succeeded'] == 2
    assert payload['itemStatusSummary']['dead_letter'] == 1
    assert payload['itemStatusSummary']['queued'] == 1
    assert payload['errorReasonSummary']['job_not_completable'] == 1
    assert payload['items'][0]['bulkCommandId'] == lineage['bulkCommandId']
    assert payload['items'][0]['itemStatusSummary']['queued'] == 1
    assert payload['items'][1]['bulkCommandId'] == rerun['bulkCommandId']
    assert payload['items'][1]['itemStatusSummary']['dead_letter'] == 1
    assert payload['items'][2]['bulkCommandId'] == parent['bulkCommandId']
    assert payload['items'][2]['itemStatusSummary']['succeeded'] == 2
    assert payload['items'][2]['errorReasonSummary']['job_not_completable'] == 1
