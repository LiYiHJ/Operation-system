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


def test_action_job_dead_letter_redrive_and_request_recovery_surface():
    client = _build_client()
    create_resp = client.post('/api/v1/actions/requests', json={'actionCode': 'price_update', 'batchRef': 'batch-async-r3', 'canonicalSku': 'SKU-R3', 'requestedBy': 'evan'})
    request_id = create_resp.get_json()['data']['requestId']
    client.post(f'/api/v1/actions/requests/{request_id}/submit', json={'operator': 'evan'})
    client.post(f'/api/v1/actions/requests/{request_id}/approve', json={'operator': 'lead'})

    push_resp = client.post(
        f'/api/v1/actions/requests/{request_id}/push',
        json={'operator': 'ops', 'channel': 'mock_push_adapter', 'idempotencyKey': 'idem-async-r3'},
        headers={'X-Trace-Id': 'trc_async_r3'},
    )
    job_id = push_resp.get_json()['data']['jobId']

    dead_letter_resp = client.post(f'/api/v1/jobs/{job_id}/dead-letter', json={'operator': 'ops', 'reason': 'manual_quarantine'})
    assert dead_letter_resp.status_code == 202
    dead_letter_payload = dead_letter_resp.get_json()['data']
    assert dead_letter_payload['jobStatus'] == 'dead_letter'
    assert dead_letter_payload['deadLettered'] is True

    recovery_resp = client.get(f'/api/v1/actions/requests/{request_id}/recovery')
    assert recovery_resp.status_code == 200
    recovery_payload = recovery_resp.get_json()['data']
    assert recovery_payload['summary']['deadLetterJobs'] == 1
    assert recovery_payload['summary']['redriveableJobs'] == 1
    assert recovery_payload['items'][0]['recommendedOperation'] == 'redrive'

    redrive_resp = client.post(f'/api/v1/jobs/{job_id}/redrive', json={'operator': 'ops', 'reason': 'manual_redrive'})
    assert redrive_resp.status_code == 202
    redrive_payload = redrive_resp.get_json()['data']
    assert redrive_payload['jobStatus'] == 'queued'
    assert redrive_payload['redriveCount'] == 1

    events_resp = client.get(f'/api/v1/jobs/{job_id}/events')
    assert events_resp.status_code == 200
    events_payload = events_resp.get_json()['data']
    event_types = [item['eventType'] for item in events_payload['events']]
    assert 'job_dead_lettered' in event_types
    assert 'job_redriven' in event_types
