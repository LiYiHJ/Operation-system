from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ecom_v51.api.app import create_app
from ecom_v51.services.action_store import ACTION_JOBS, reset_action_store


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


def test_action_job_round10_release_stale_and_command_audit_contract():
    client = _build_client()
    _request_id, job_id = _create_and_push_request(client, batch_ref='batch-r10-api', suffix='a')

    claim_resp = client.post('/api/v1/actions/worker/claim-next', json={'workerId': 'worker-r10', 'operator': 'worker-r10', 'batchRef': 'batch-r10-api'})
    assert claim_resp.status_code == 202

    stale_at = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
    ACTION_JOBS[job_id]['leaseHeartbeatAt'] = stale_at
    ACTION_JOBS[job_id]['leaseExpiresAt'] = stale_at

    release_resp = client.post('/api/v1/actions/worker/release-stale', json={'batchRef': 'batch-r10-api', 'operator': 'ops-r10', 'limit': 10, 'reason': 'stale_timeout'})
    assert release_resp.status_code == 202
    release_payload = release_resp.get_json()['data']
    assert release_payload['summary']['releasedJobs'] == 1
    assert release_payload['items'][0]['jobId'] == job_id
    assert release_payload['items'][0]['jobStatus'] == 'queued'

    audit_resp = client.get('/api/v1/actions/worker/command-audit?batchRef=batch-r10-api&limit=20')
    assert audit_resp.status_code == 200
    audit_payload = audit_resp.get_json()['data']
    assert audit_payload['summary']['staleReleaseEvents'] == 1
    assert audit_payload['commandTypeSummary']['job_stale_released'] == 1
    assert audit_payload['total'] >= 2
