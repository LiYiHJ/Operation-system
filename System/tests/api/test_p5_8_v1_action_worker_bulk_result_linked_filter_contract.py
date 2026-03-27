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


def test_action_job_round19_worker_bulk_linked_filter_contract():
    client = _build_client()
    _, job_a = _create_and_push_request(client, batch_ref='batch-r19-api', suffix='a')
    _, job_b = _create_and_push_request(client, batch_ref='batch-r19-api', suffix='b')
    _, job_c = _create_and_push_request(client, batch_ref='batch-r19-api', suffix='c')

    claim_resp = client.post('/api/v1/actions/worker/claim-next', json={'workerId': 'worker-r19-api', 'operator': 'worker-r19-api', 'batchRef': 'batch-r19-api'})
    assert claim_resp.status_code == 202
    assert claim_resp.get_json()['data']['jobId'] == job_a

    parent_resp = client.post('/api/v1/actions/worker/bulk-command', json={'command': 'release-lease', 'jobIds': [job_a, job_b, job_c], 'operator': 'ops-r19-api', 'workerId': 'worker-r19-api', 'reason': 'bulk_release_partial_r19_api'})
    assert parent_resp.status_code == 202
    parent = parent_resp.get_json()['data']

    child_resp = client.post(f"/api/v1/actions/worker/bulk-results/{parent['bulkCommandId']}/re-execute", json={'selection': 'failed', 'command': 'dead-letter', 'operator': 'ops-r19-api', 'reason': 'rerun_failed_as_dead_letter_r19_api'})
    assert child_resp.status_code == 202
    child = child_resp.get_json()['data']

    lineage_resp = client.post(f"/api/v1/actions/worker/bulk-results/{parent['bulkCommandId']}/lineage-command", json={'selection': 'failed', 'command': 'redrive', 'scope': 'entire_lineage', 'operator': 'ops-r19-api', 'reason': 'lineage_redrive_r19_api'})
    assert lineage_resp.status_code == 202
    lineage = lineage_resp.get_json()['data']

    history_resp = client.get(f"/api/v1/actions/worker/bulk-results?batchRef=batch-r19-api&commandMode=lineage&sourceBulkCommandId={parent['bulkCommandId']}&offset=0&limit=10")
    assert history_resp.status_code == 200
    history_payload = history_resp.get_json()['data']
    assert history_payload['total'] == 1
    assert history_payload['items'][0]['bulkCommandId'] == lineage['bulkCommandId']
    assert history_payload['linkedFilterSummary']['sourceBulkCommandId'] == 1

    detail_resp = client.get(f"/api/v1/actions/worker/bulk-results/{parent['bulkCommandId']}")
    assert detail_resp.status_code == 200
    detail_payload = detail_resp.get_json()['data']
    assert detail_payload['navigationContext']['focusBulkCommandId'] == parent['bulkCommandId']
    assert detail_payload['navigationContext']['sourceBulkCommandId'] == parent['bulkCommandId']

    summary_resp = client.get(f"/api/v1/actions/worker/bulk-results/{parent['bulkCommandId']}/lineage-summary?commandMode=lineage&sourceBulkCommandId={parent['bulkCommandId']}&selection=failed&reexecuteCommand=redrive&limit=10")
    assert summary_resp.status_code == 200
    summary_payload = summary_resp.get_json()['data']
    assert summary_payload['summary']['totalResults'] == 1
    assert summary_payload['linkedHistoryFilters']['sourceBulkCommandId'] == parent['bulkCommandId']
    assert summary_payload['linkedTimelineFilters']['sourceBulkCommandId'] == parent['bulkCommandId']
    assert summary_payload['latestResults'][0]['bulkCommandId'] == lineage['bulkCommandId']

    timeline_resp = client.get(f"/api/v1/actions/worker/bulk-results/{parent['bulkCommandId']}/timeline?commandMode=lineage&sourceBulkCommandId={parent['bulkCommandId']}&limit=10")
    assert timeline_resp.status_code == 200
    timeline_payload = timeline_resp.get_json()['data']
    assert timeline_payload['total'] == 1
    assert timeline_payload['items'][0]['bulkCommandId'] == lineage['bulkCommandId']
    assert timeline_payload['scope']['sourceBulkCommandId'] == parent['bulkCommandId']
    assert child['bulkCommandId'] != lineage['bulkCommandId']
