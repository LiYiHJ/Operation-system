from __future__ import annotations

from ecom_v51.api.app import create_app
from ecom_v51.api.routes.v1 import batches as batches_module
from ecom_v51.api.routes.v1 import jobs as jobs_module


def test_v1_batches_filters_and_raw_records(monkeypatch):
    app = create_app('development')
    client = app.test_client()

    monkeypatch.setattr(
        batches_module.batch_service,
        'list_recent_batches',
        lambda limit=20: {
            'contractVersion': 'p2a.v1',
            'items': [
                {'batchId': 1, 'datasetKind': 'orders', 'importabilityStatus': 'passed', 'sourceMode': 'upload'},
                {'batchId': 2, 'datasetKind': 'ads', 'importabilityStatus': 'failed', 'sourceMode': 'server_file'},
            ],
            'total': 2,
        },
    )
    monkeypatch.setattr(
        batches_module.runtime_query_service,
        'get_batch_raw_records',
        lambda batch_ref, limit=50: {'batchId': int(batch_ref), 'items': [{'rawRecordId': 1}], 'total': 1, 'contractVersion': 'p2a.v1'},
    )

    resp = client.get('/api/v1/batches?datasetKind=orders')
    payload = resp.get_json()
    assert resp.status_code == 200
    assert payload['data']['total'] == 1
    assert payload['data']['items'][0]['datasetKind'] == 'orders'

    raw_resp = client.get('/api/v1/batches/1/raw-records?limit=10')
    raw_payload = raw_resp.get_json()
    assert raw_resp.status_code == 200
    assert raw_payload['data']['total'] == 1


def test_v1_jobs_detail_and_events(monkeypatch):
    app = create_app('development')
    client = app.test_client()

    monkeypatch.setattr(
        jobs_module.runtime_query_service,
        'get_job_detail',
        lambda job_ref: {'jobId': 7, 'status': 'completed', 'timeline': [{'eventType': 'completed'}], 'contractVersion': 'p2a.v1'},
    )
    monkeypatch.setattr(
        jobs_module.runtime_query_service,
        'get_job_events',
        lambda job_ref: {'jobId': 7, 'events': [{'eventType': 'completed'}], 'total': 1, 'contractVersion': 'p2a.v1'},
    )

    resp = client.get('/api/v1/jobs/7')
    payload = resp.get_json()
    assert resp.status_code == 200
    assert payload['data']['jobId'] == 7
    assert payload['data']['status'] == 'completed'

    events_resp = client.get('/api/v1/jobs/7/events')
    events_payload = events_resp.get_json()
    assert events_resp.status_code == 200
    assert events_payload['data']['total'] == 1
