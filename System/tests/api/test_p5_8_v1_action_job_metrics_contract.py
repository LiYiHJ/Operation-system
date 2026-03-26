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


def test_action_job_round6_metrics_failure_buckets_and_audit_contract():
    client = _build_client()
    request_a, job_a = _create_and_push_request(client, batch_ref='batch-r6-api', suffix='a')
    request_b, job_b = _create_and_push_request(client, batch_ref='batch-r6-api', suffix='b', action_code='inventory_adjustment')
    _request_c, _job_c = _create_and_push_request(client, batch_ref='batch-r6-api-other', suffix='c')

    client.post(
        f'/api/v1/actions/requests/{request_a}/callback',
        json={'eventType': 'delivery_update', 'providerStatus': 'failed', 'externalRef': 'ext-r6-a'},
    )
    client.post(
        f'/api/v1/actions/requests/{request_b}/callback',
        json={'eventType': 'delivery_update', 'providerStatus': 'provider_reject', 'externalRef': 'ext-r6-b'},
    )
    client.post(
        f'/api/v1/jobs/{job_b}/dead-letter',
        json={'operator': 'ops', 'reason': 'provider_reject_dead'},
        headers={'Idempotency-Key': 'dead-r6-api'},
    )

    metrics_resp = client.get('/api/v1/actions/jobs/metrics?batchRef=batch-r6-api&limit=10')
    assert metrics_resp.status_code == 200
    metrics_payload = metrics_resp.get_json()['data']
    assert metrics_payload['summary']['totalJobs'] == 2
    assert metrics_payload['queueLagMetrics']['samples'] == 2
    assert metrics_payload['topLaggingJobsTotal'] == 2

    failure_resp = client.get('/api/v1/actions/jobs/failure-buckets?batchRef=batch-r6-api&limit=10')
    assert failure_resp.status_code == 200
    failure_payload = failure_resp.get_json()['data']
    assert failure_payload['summary']['totalFailedJobs'] == 2
    assert failure_payload['reasonSummary']['failed'] == 1
    assert failure_payload['reasonSummary']['provider_reject_dead'] == 1

    job_audit_resp = client.get(f'/api/v1/actions/jobs/{job_b}/audit')
    assert job_audit_resp.status_code == 200
    job_audit_payload = job_audit_resp.get_json()['data']
    assert job_audit_payload['jobId'] == job_b
    assert job_audit_payload['jobStatus'] == 'dead_letter'
    assert job_audit_payload['eventTypeSummary']['job_dead_lettered'] == 1

    request_audit_resp = client.get(f'/api/v1/actions/requests/{request_a}/audit')
    assert request_audit_resp.status_code == 200
    request_audit_payload = request_audit_resp.get_json()['data']
    assert request_audit_payload['requestId'] == request_a
    assert request_audit_payload['summary']['failedJobs'] == 1
    assert request_audit_payload['failureBuckets']['summary']['totalFailedJobs'] == 1

    batch_audit_resp = client.get('/api/v1/actions/batches/batch-r6-api/audit')
    assert batch_audit_resp.status_code == 200
    batch_audit_payload = batch_audit_resp.get_json()['data']
    assert batch_audit_payload['batchRef'] == 'batch-r6-api'
    assert batch_audit_payload['summary']['totalJobs'] == 2
    assert batch_audit_payload['failureBuckets']['summary']['totalFailedJobs'] == 2


def test_action_job_round6_job_audit_not_found_contract():
    client = _build_client()
    resp = client.get('/api/v1/actions/jobs/job_missing/audit')
    assert resp.status_code == 404
    assert resp.get_json()['error']['code'] == 'job_not_found'
