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


def test_action_job_round21_worker_bulk_result_timeline_selection_contract():
    client = _build_client()
    _, job_a = _create_and_push_request(client, batch_ref='batch-r21-api', suffix='a')
    _, job_b = _create_and_push_request(client, batch_ref='batch-r21-api', suffix='b')
    _, job_c = _create_and_push_request(client, batch_ref='batch-r21-api', suffix='c')

    claim_resp = client.post('/api/v1/actions/worker/claim-next', json={'workerId': 'worker-r21-api', 'operator': 'worker-r21-api', 'batchRef': 'batch-r21-api'})
    assert claim_resp.status_code == 202
    assert claim_resp.get_json()['data']['jobId'] == job_a

    parent_resp = client.post('/api/v1/actions/worker/bulk-command', json={'command': 'release-lease', 'jobIds': [job_a, job_b, job_c], 'operator': 'ops-r21-api', 'workerId': 'worker-r21-api', 'reason': 'bulk_release_partial_r21_api'})
    assert parent_resp.status_code == 202
    parent = parent_resp.get_json()['data']

    child_resp = client.post(f"/api/v1/actions/worker/bulk-results/{parent['bulkCommandId']}/re-execute", json={'selection': 'failed', 'command': 'dead-letter', 'operator': 'ops-r21-api', 'reason': 'rerun_failed_as_dead_letter_r21_api'})
    assert child_resp.status_code == 202
    child = child_resp.get_json()['data']

    lineage_resp = client.post(f"/api/v1/actions/worker/bulk-results/{parent['bulkCommandId']}/lineage-command", json={'selection': 'failed', 'command': 'redrive', 'scope': 'entire_lineage', 'operator': 'ops-r21-api', 'reason': 'lineage_redrive_r21_api'})
    assert lineage_resp.status_code == 202

    timeline_resp = client.get(f"/api/v1/actions/worker/bulk-results/{parent['bulkCommandId']}/timeline?selection=failed&reexecuteCommand=dead-letter&limit=10")
    assert timeline_resp.status_code == 200
    timeline_payload = timeline_resp.get_json()['data']
    assert timeline_payload['total'] == 1
    assert timeline_payload['scope']['selection'] == 'failed'
    assert timeline_payload['scope']['reexecuteCommand'] == 'dead-letter'
    assert timeline_payload['selectionSummary']['failed'] == 1
    assert timeline_payload['reexecuteCommandSummary']['dead-letter'] == 1
    assert timeline_payload['items'][0]['bulkCommandId'] == child['bulkCommandId']
    assert timeline_payload['items'][0]['selection'] == 'failed'
    assert timeline_payload['items'][0]['reexecuteCommand'] == 'dead-letter'

    summary_resp = client.get(f"/api/v1/actions/worker/bulk-results/{parent['bulkCommandId']}/lineage-summary?selection=failed&reexecuteCommand=dead-letter&limit=10")
    assert summary_resp.status_code == 200
    summary_payload = summary_resp.get_json()['data']
    assert summary_payload['linkedTimelineFilters']['selection'] == 'failed'
    assert summary_payload['linkedTimelineFilters']['reexecuteCommand'] == 'dead-letter'
    assert summary_payload['timelineSummary']['totalEvents'] == 1
