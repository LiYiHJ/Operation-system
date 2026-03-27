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


def test_action_job_round11_bulk_release_and_command_audit_detail_contract():
    client = _build_client()
    _request_a, job_a = _create_and_push_request(client, batch_ref='batch-r11-api', suffix='a')
    _request_b, job_b = _create_and_push_request(client, batch_ref='batch-r11-api', suffix='b')

    claim_a = client.post('/api/v1/actions/worker/claim-next', json={'workerId': 'worker-r11-a', 'operator': 'worker-r11-a', 'batchRef': 'batch-r11-api'})
    claim_b = client.post('/api/v1/actions/worker/claim-next', json={'workerId': 'worker-r11-b', 'operator': 'worker-r11-b', 'batchRef': 'batch-r11-api'})
    assert claim_a.status_code == 202
    assert claim_b.status_code == 202

    bulk_resp = client.post(
        '/api/v1/actions/worker/bulk-command',
        json={'command': 'release-lease', 'jobIds': [job_a, job_b], 'operator': 'ops-r11-api', 'reason': 'bulk_release'},
    )
    assert bulk_resp.status_code == 202
    bulk_payload = bulk_resp.get_json()['data']
    assert bulk_payload['summary']['requestedJobs'] == 2
    assert bulk_payload['summary']['succeededJobs'] == 2
    assert bulk_payload['summary']['failedJobs'] == 0

    audit_resp = client.get('/api/v1/actions/worker/command-audit?batchRef=batch-r11-api&limit=20')
    assert audit_resp.status_code == 200
    audit_payload = audit_resp.get_json()['data']
    assert audit_payload['summary']['releaseEvents'] >= 2
    detail_event_id = next(item['eventId'] for item in audit_payload['items'] if item['eventType'] == 'job_lease_released')

    detail_resp = client.get(f'/api/v1/actions/worker/command-audit/{detail_event_id}')
    assert detail_resp.status_code == 200
    detail_payload = detail_resp.get_json()['data']
    assert detail_payload['eventId'] == detail_event_id
    assert detail_payload['commandAudit']['eventType'] == 'job_lease_released'
    assert detail_payload['job']['jobId'] in {job_a, job_b}
    assert detail_payload['timelineTotal'] >= 2
