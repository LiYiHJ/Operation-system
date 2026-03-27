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


def _create_and_push_request(client, *, suffix: str) -> tuple[str, str]:
    create_resp = client.post(
        '/api/v1/actions/requests',
        json={'actionCode': 'price_update', 'batchRef': f'batch-{suffix}', 'canonicalSku': f'SKU-{suffix}', 'requestedBy': 'evan'},
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


def test_action_job_round4_failed_callback_recovery_timeline_and_retry_idempotency():
    client = _build_client()
    request_id, job_id = _create_and_push_request(client, suffix='r4-failed')

    callback_resp = client.post(
        f'/api/v1/actions/requests/{request_id}/callback',
        json={
            'eventType': 'delivery_update',
            'providerStatus': 'failed',
            'externalRef': 'ext-r4-failed',
            'payload': {'reason': 'provider_error'},
        },
    )
    assert callback_resp.status_code == 202

    job_resp = client.get(f'/api/v1/jobs/{job_id}')
    assert job_resp.status_code == 200
    job_payload = job_resp.get_json()['data']
    assert job_payload['jobStatus'] == 'failed'
    assert job_payload['recommendedOperation'] == 'retry'
    assert 'retry' in job_payload['availableCommands']
    assert 'dead-letter' in job_payload['availableCommands']

    recovery_resp = client.get(f'/api/v1/actions/requests/{request_id}/recovery')
    assert recovery_resp.status_code == 200
    recovery_payload = recovery_resp.get_json()['data']
    assert recovery_payload['summary']['failedJobs'] == 1
    assert recovery_payload['summary']['retryableJobs'] == 1
    assert recovery_payload['timelineTotal'] >= 4
    event_types = [item['eventType'] for item in recovery_payload['timeline']]
    assert 'callback_received' in event_types
    assert 'job_failed' in event_types

    retry_resp_1 = client.post(
        f'/api/v1/jobs/{job_id}/retry',
        json={'operator': 'ops', 'reason': 'manual_retry'},
        headers={'Idempotency-Key': 'retry-r4-api'},
    )
    retry_resp_2 = client.post(
        f'/api/v1/jobs/{job_id}/retry',
        json={'operator': 'ops', 'reason': 'manual_retry'},
        headers={'Idempotency-Key': 'retry-r4-api'},
    )
    assert retry_resp_1.status_code == 202
    assert retry_resp_2.status_code == 202
    retry_payload_1 = retry_resp_1.get_json()['data']
    retry_payload_2 = retry_resp_2.get_json()['data']
    assert retry_payload_1['retryCount'] == 1
    assert retry_payload_2['retryCount'] == 1
    assert retry_payload_2['jobStatus'] == 'queued'

    recovery_after_retry = client.get(f'/api/v1/actions/requests/{request_id}/recovery').get_json()['data']
    assert recovery_after_retry['summary']['queuedJobs'] == 1
    assert recovery_after_retry['latestJobStatus'] == 'queued'
    assert recovery_after_retry['latestRecoveryOperation'] == 'retry'


def test_action_job_round4_success_callback_blocks_retry_boundary():
    client = _build_client()
    request_id, job_id = _create_and_push_request(client, suffix='r4-success')

    callback_resp = client.post(
        f'/api/v1/actions/requests/{request_id}/callback',
        json={
            'eventType': 'delivery_update',
            'providerStatus': 'completed',
            'externalRef': 'ext-r4-success',
        },
    )
    assert callback_resp.status_code == 202

    job_resp = client.get(f'/api/v1/jobs/{job_id}')
    assert job_resp.status_code == 200
    job_payload = job_resp.get_json()['data']
    assert job_payload['jobStatus'] == 'succeeded'
    assert job_payload['recommendedOperation'] is None
    assert 'retry' not in job_payload['availableCommands']

    retry_resp = client.post(
        f'/api/v1/jobs/{job_id}/retry',
        json={'operator': 'ops', 'reason': 'should_block'},
        headers={'Idempotency-Key': 'retry-r4-success'},
    )
    assert retry_resp.status_code == 409
    error_payload = retry_resp.get_json()['error']
    assert error_payload['code'] == 'job_not_retryable'
