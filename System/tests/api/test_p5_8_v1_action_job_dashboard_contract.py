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


def test_action_job_round5_summary_dashboard_and_batch_health_contract():
    client = _build_client()
    request_a, job_a = _create_and_push_request(client, batch_ref='batch-r5-api', suffix='a')
    request_b, job_b = _create_and_push_request(client, batch_ref='batch-r5-api', suffix='b', action_code='inventory_adjustment')
    _create_and_push_request(client, batch_ref='batch-r5-api-other', suffix='c')

    client.post(
        f'/api/v1/actions/requests/{request_a}/callback',
        json={'eventType': 'delivery_update', 'providerStatus': 'failed', 'externalRef': 'ext-r5-a'},
    )
    client.post(
        f'/api/v1/jobs/{job_a}/retry',
        json={'operator': 'ops', 'reason': 'manual_retry'},
        headers={'Idempotency-Key': 'retry-r5-api'},
    )

    client.post(
        f'/api/v1/actions/requests/{request_b}/callback',
        json={'eventType': 'delivery_update', 'providerStatus': 'failed', 'externalRef': 'ext-r5-b'},
    )
    client.post(
        f'/api/v1/jobs/{job_b}/dead-letter',
        json={'operator': 'ops', 'reason': 'manual_dead_letter'},
        headers={'Idempotency-Key': 'dead-r5-api'},
    )

    summary_resp = client.get('/api/v1/actions/jobs/summary?batchRef=batch-r5-api&limit=10')
    assert summary_resp.status_code == 200
    summary_payload = summary_resp.get_json()['data']
    assert summary_payload['summary']['totalJobs'] == 2
    assert summary_payload['summary']['queuedJobs'] == 1
    assert summary_payload['summary']['deadLetterJobs'] == 1
    assert summary_payload['filters']['batchRef'] == 'batch-r5-api'
    assert summary_payload['total'] == 2

    dashboard_resp = client.get('/api/v1/actions/jobs/dashboard?batchRef=batch-r5-api&limit=10')
    assert dashboard_resp.status_code == 200
    dashboard_payload = dashboard_resp.get_json()['data']
    assert dashboard_payload['summary']['totalJobs'] == 2
    assert dashboard_payload['latestJobsTotal'] == 2
    event_types = {item['eventType'] for item in dashboard_payload['recentRecoveryEvents']}
    assert 'job_retry_requested' in event_types
    assert 'job_dead_lettered' in event_types

    health_resp = client.get('/api/v1/actions/batches/batch-r5-api/queue-health')
    assert health_resp.status_code == 200
    health_payload = health_resp.get_json()['data']
    assert health_payload['batchRef'] == 'batch-r5-api'
    assert health_payload['requestSummary']['totalRequests'] == 2
    assert health_payload['requestSummary']['requestsWithDeadLetter'] == 1
    assert health_payload['requestSummary']['requestsNeedingAttention'] == 1
    assert health_payload['summary']['deadLetterJobs'] == 1
    assert health_payload['timelineTotal'] >= 6


def test_action_job_round5_batch_queue_health_not_found_contract():
    client = _build_client()
    resp = client.get('/api/v1/actions/batches/non-existent-batch/queue-health')
    assert resp.status_code == 404
    error_payload = resp.get_json()['error']
    assert error_payload['code'] == 'batch_not_found'
