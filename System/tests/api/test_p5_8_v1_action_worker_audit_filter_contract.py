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


def _create_and_push_request(client, *, batch_ref: str, suffix: str, action_code: str = 'price_update') -> tuple[str, str]:
    create_resp = client.post(
        '/api/v1/actions/requests',
        json={'actionCode': action_code, 'batchRef': batch_ref, 'canonicalSku': f'SKU-{suffix}', 'requestedBy': 'evan'},
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


def test_action_job_round12_worker_audit_filter_and_bulk_feedback_contract():
    client = _build_client()
    _request_a, job_a = _create_and_push_request(client, batch_ref='batch-r12-api', suffix='a', action_code='price_update')
    _request_b, job_b = _create_and_push_request(client, batch_ref='batch-r12-api', suffix='b', action_code='inventory_adjustment')
    _request_c, job_c = _create_and_push_request(client, batch_ref='batch-r12-api', suffix='c', action_code='price_update')

    claim_a = client.post('/api/v1/actions/worker/claim-next', json={'workerId': 'worker-r12-api-a', 'operator': 'worker-r12-api-a', 'batchRef': 'batch-r12-api'})
    claim_b = client.post('/api/v1/actions/worker/claim-next', json={'workerId': 'worker-r12-api-b', 'operator': 'worker-r12-api-b', 'batchRef': 'batch-r12-api'})
    assert claim_a.status_code == 202
    assert claim_b.status_code == 202

    release_resp = client.post(f'/api/v1/jobs/{job_a}/release-lease', json={'workerId': 'worker-r12-api-a', 'operator': 'ops-r12-api', 'reason': 'manual_release'})
    fail_resp = client.post(f'/api/v1/jobs/{job_b}/mark-failed', json={'workerId': 'worker-r12-api-b', 'operator': 'ops-r12-api', 'reason': 'provider_failed'})
    assert release_resp.status_code == 202
    assert fail_resp.status_code == 202

    audit_resp = client.get('/api/v1/actions/worker/command-audit?batchRef=batch-r12-api&eventType=job_failed&actionCode=inventory_adjustment&limit=20')
    assert audit_resp.status_code == 200
    audit_payload = audit_resp.get_json()['data']
    assert audit_payload['scope']['eventType'] == 'job_failed'
    assert audit_payload['scope']['actionCode'] == 'inventory_adjustment'
    assert audit_payload['total'] == 1
    assert audit_payload['items'][0]['jobId'] == job_b
    assert audit_payload['items'][0]['eventType'] == 'job_failed'
    assert audit_payload['items'][0]['actionCode'] == 'inventory_adjustment'

    bulk_resp = client.post(
        '/api/v1/actions/worker/bulk-command',
        json={'command': 'mark-succeeded', 'jobIds': [job_c, job_a], 'operator': 'ops-r12-api', 'workerId': 'worker-r12-api-a', 'externalRef': 'ext-r12-api'},
    )
    assert bulk_resp.status_code == 202
    bulk_payload = bulk_resp.get_json()['data']
    assert bulk_payload['summary']['requestedJobs'] == 2
    assert bulk_payload['summary']['succeededJobs'] == 1
    assert bulk_payload['summary']['failedJobs'] == 1
    assert bulk_payload['itemStatusSummary']['succeeded'] == 1
    assert bulk_payload['errorReasonSummary']['job_not_completable'] == 1
