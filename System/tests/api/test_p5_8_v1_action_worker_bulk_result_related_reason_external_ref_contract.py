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


def test_action_job_round29_worker_bulk_result_related_reason_external_ref_contract():
    client = _build_client()
    _, job_a = _create_and_push_request(client, batch_ref='batch-r29-api', suffix='a')
    _, job_b = _create_and_push_request(client, batch_ref='batch-r29-api', suffix='b')
    _, job_c = _create_and_push_request(client, batch_ref='batch-r29b-api', suffix='c')

    parent_resp = client.post('/api/v1/actions/worker/bulk-command', json={
        'command': 'release-lease',
        'jobIds': [job_a, job_b, job_c],
        'operator': 'ops-r29-api',
        'reason': 'bulk_release_partial_r29_api',
        'externalRef': 'ext-parent-r29-api',
    })
    assert parent_resp.status_code == 202
    parent = parent_resp.get_json()['data']

    rerun_resp = client.post(f"/api/v1/actions/worker/bulk-results/{parent['bulkCommandId']}/re-execute", json={
        'selection': 'failed',
        'command': 'dead-letter',
        'operator': 'ops-r29-api',
        'reason': 'rerun_failed_dead_letter_r29_api',
        'externalRef': 'ext-rerun-r29-api',
    })
    assert rerun_resp.status_code == 202

    lineage_resp = client.post(f"/api/v1/actions/worker/bulk-results/{parent['bulkCommandId']}/lineage-command", json={
        'selection': 'failed',
        'command': 'redrive',
        'scope': 'entire_lineage',
        'operator': 'ops-r29-api',
        'reason': 'lineage_redrive_r29_api',
        'externalRef': 'ext-lineage-r29-api',
    })
    assert lineage_resp.status_code == 202
    lineage = lineage_resp.get_json()['data']

    related_resp = client.get(f"/api/v1/actions/worker/bulk-results/{parent['bulkCommandId']}/related?limit=10")
    assert related_resp.status_code == 200
    payload = related_resp.get_json()['data']
    assert payload['summary']['totalResults'] == 3
    assert payload['reasonSummary']['bulk_release_partial_r29_api'] == 1
    assert payload['reasonSummary']['rerun_failed_dead_letter_r29_api'] == 1
    assert payload['reasonSummary']['lineage_redrive_r29_api'] == 1
    assert payload['externalRefSummary']['ext-parent-r29-api'] == 1
    assert payload['externalRefSummary']['ext-rerun-r29-api'] == 1
    assert payload['externalRefSummary']['ext-lineage-r29-api'] == 1
    assert payload['items'][0]['bulkCommandId'] == lineage['bulkCommandId']
    assert payload['items'][0]['reason'] == 'lineage_redrive_r29_api'
    assert payload['items'][0]['externalRef'] == 'ext-lineage-r29-api'
