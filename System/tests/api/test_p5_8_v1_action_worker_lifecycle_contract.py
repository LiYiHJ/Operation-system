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


def test_action_job_round9_worker_lifecycle_contract():
    client = _build_client()
    _request_id, job_id = _create_and_push_request(client, batch_ref='batch-r9-api', suffix='a')

    claim_resp = client.post('/api/v1/actions/worker/claim-next', json={'workerId': 'worker-r9', 'operator': 'worker-r9', 'batchRef': 'batch-r9-api'})
    assert claim_resp.status_code == 202

    release_resp = client.post(
        f'/api/v1/jobs/{job_id}/release-lease',
        json={'workerId': 'worker-r9', 'operator': 'worker-r9', 'reason': 'manual_release'},
        headers={'Idempotency-Key': 'rel-r9'},
    )
    assert release_resp.status_code == 202
    release_payload = release_resp.get_json()['data']
    assert release_payload['jobStatus'] == 'queued'
    assert release_payload['workerId'] is None

    claim_again_resp = client.post('/api/v1/actions/worker/claim-next', json={'workerId': 'worker-r9', 'operator': 'worker-r9', 'batchRef': 'batch-r9-api'})
    assert claim_again_resp.status_code == 202

    success_resp = client.post(
        f'/api/v1/jobs/{job_id}/mark-succeeded',
        json={'workerId': 'worker-r9', 'operator': 'worker-r9', 'externalRef': 'ext-r9'},
        headers={'Idempotency-Key': 'succ-r9'},
    )
    assert success_resp.status_code == 202
    success_payload = success_resp.get_json()['data']
    assert success_payload['jobStatus'] == 'succeeded'
    assert success_payload['queueStatus'] == 'completed'

    lease_audit_resp = client.get('/api/v1/actions/worker/lease-audit?batchRef=batch-r9-api&workerId=worker-r9&limit=20')
    assert lease_audit_resp.status_code == 200
    audit_payload = lease_audit_resp.get_json()['data']
    assert audit_payload['summary']['claimEvents'] >= 2
    assert audit_payload['summary']['releaseEvents'] == 1
    assert audit_payload['summary']['succeededEvents'] == 1
    assert audit_payload['total'] >= 3


def test_action_job_round9_mark_failed_contract_and_worker_guard():
    client = _build_client()
    _request_id, job_id = _create_and_push_request(client, batch_ref='batch-r9-api-fail', suffix='b')

    claim_resp = client.post('/api/v1/actions/worker/claim-next', json={'workerId': 'worker-r9b', 'operator': 'worker-r9b', 'batchRef': 'batch-r9-api-fail'})
    assert claim_resp.status_code == 202

    mismatch_resp = client.post(f'/api/v1/jobs/{job_id}/mark-failed', json={'workerId': 'worker-other', 'operator': 'worker-other', 'reason': 'worker_timeout'})
    assert mismatch_resp.status_code == 409
    assert mismatch_resp.get_json()['error']['code'] == 'worker_mismatch'

    failed_resp = client.post(
        f'/api/v1/jobs/{job_id}/mark-failed',
        json={'workerId': 'worker-r9b', 'operator': 'worker-r9b', 'reason': 'worker_timeout'},
        headers={'Idempotency-Key': 'fail-r9'},
    )
    assert failed_resp.status_code == 202
    failed_payload = failed_resp.get_json()['data']
    assert failed_payload['jobStatus'] == 'failed'
    assert failed_payload['queueStatus'] == 'failed'
    assert failed_payload['recommendedOperation'] == 'retry'
