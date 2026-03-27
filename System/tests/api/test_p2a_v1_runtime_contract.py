from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ecom_v51.api.app import create_app
from ecom_v51.api.routes.v1 import batches as v1_batches
from ecom_v51.api.routes.v1 import import_ops as v1_import_ops
from ecom_v51.api.routes.v1 import jobs as v1_jobs


class DummyBatchService:
    CONTRACT_VERSION = 'p2a.v1'

    def list_recent_batches(self, limit: int = 20, shop_id: int | None = None, dataset_kind: str | None = None, status: str | None = None):
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'source': 'ingest_batch',
            'total': 1,
            'items': [{
                'batchId': 21,
                'workspaceBatchId': 'ws-000021',
                'sessionId': 21,
                'datasetKind': dataset_kind or 'orders',
                'importProfile': 'ozon_orders_report',
                'batchStatus': status or 'imported',
                'shopId': shop_id or 1,
                'contractVersion': self.CONTRACT_VERSION,
            }],
        }

    def get_batch_detail(self, batch_ref: str):
        if str(batch_ref) not in {'21', '22'}:
            return None
        return {
            'batchId': int(batch_ref),
            'workspaceBatchId': f'ws-0000{batch_ref}',
            'sessionId': int(batch_ref),
            'datasetKind': 'orders',
            'importProfile': 'ozon_orders_report',
            'contractVersion': self.CONTRACT_VERSION,
            'rawRecords': [{'rawStage': 'raw_parse', 'payload': {'preview': True}}],
            'eventTimeline': [{'eventType': 'parse'}, {'eventType': 'confirm'}, {'eventType': 'replay_requested'}],
            'reasonBuckets': [],
            'manualOverrides': [],
            'sourceObjects': [{'filePath': str(ROOT / 'sample_data' / 'p0_csv_scene_from_cn.csv')}],
        }

    def get_batch_timeline(self, batch_ref: str):
        return {
            'batchId': int(batch_ref),
            'contractVersion': self.CONTRACT_VERSION,
            'events': [{'eventType': 'parse'}, {'eventType': 'confirm'}, {'eventType': 'replay_requested'}],
            'eventTimeline': [{'eventType': 'parse'}, {'eventType': 'confirm'}, {'eventType': 'replay_requested'}],
            'total': 3,
        }

    def get_batch_quarantine_summary(self, batch_ref: str):
        return {
            'batchId': int(batch_ref),
            'contractVersion': self.CONTRACT_VERSION,
            'quarantineCount': 0,
            'reasonBuckets': [],
        }

    def append_audit_event(self, batch_id: int, event_type: str, payload: dict):
        return None


class DummyRuntimeService:
    def run_upload(self, **kwargs):
        return {
            'jobId': 701,
            'jobCode': 'job_701',
            'batchId': 21,
            'workspaceBatchId': 'ws-000021',
            'sessionId': 21,
            'status': 'completed',
            'contractVersion': 'p2a.v1',
        }

    def confirm_batch(self, **kwargs):
        return {
            'jobId': 702,
            'jobCode': 'job_702',
            'batchId': 21,
            'workspaceBatchId': 'ws-000021',
            'importedRows': 12,
            'quarantinedRows': 1,
            'importabilityStatus': 'partial',
            'runtimeAudit': {'gateMode': 'manual_continue'},
            'status': 'completed',
            'contractVersion': 'p2a.v1',
        }

    def replay_batch(self, **kwargs):
        return {
            'jobId': 703,
            'jobCode': 'job_703',
            'originalBatchId': 21,
            'batchId': 22,
            'workspaceBatchId': 'ws-000022',
            'status': 'completed',
            'contractVersion': 'p2a.v1',
        }

    def get_job(self, job_ref: str):
        mapping = {
            '701': {'jobId': 701, 'status': 'completed', 'jobType': 'upload', 'batchId': 21, 'timeline': [{'eventType': 'queued'}, {'eventType': 'completed'}]},
            '702': {'jobId': 702, 'status': 'completed', 'jobType': 'confirm', 'batchId': 21, 'timeline': [{'eventType': 'queued'}, {'eventType': 'completed'}]},
            '703': {'jobId': 703, 'status': 'completed', 'jobType': 'replay', 'batchId': 22, 'timeline': [{'eventType': 'queued'}, {'eventType': 'completed'}]},
        }
        return mapping.get(str(job_ref))


def _build_client(monkeypatch):
    dummy_batch = DummyBatchService()
    dummy_runtime = DummyRuntimeService()
    monkeypatch.setattr(v1_batches, '_get_batch_service', lambda: dummy_batch)
    monkeypatch.setattr(v1_batches, '_get_runtime_service', lambda: dummy_runtime)
    monkeypatch.setattr(v1_import_ops, '_get_runtime_service', lambda: dummy_runtime)
    monkeypatch.setattr(v1_jobs, '_get_runtime_service', lambda: dummy_runtime)
    app = create_app('development')
    return app.test_client()


def test_v1_import_upload_and_job_contract(monkeypatch):
    client = _build_client(monkeypatch)

    response = client.post('/api/v1/import/upload', json={'filePath': str(ROOT / 'sample_data' / 'p0_csv_scene_from_cn.csv'), 'shopId': 1})
    assert response.status_code == 202
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['batchId'] == 21
    assert payload['data']['jobId'] == 701

    job_response = client.get('/api/v1/jobs/701')
    assert job_response.status_code == 200
    job_payload = job_response.get_json()
    assert job_payload['data']['status'] == 'completed'
    assert job_payload['data']['jobType'] == 'upload'


def test_v1_confirm_replay_and_detail_contract(monkeypatch):
    client = _build_client(monkeypatch)

    confirm_response = client.post('/api/v1/batches/21/confirm', json={'operator': 'evan', 'gateMode': 'manual_continue'})
    assert confirm_response.status_code == 202
    confirm_payload = confirm_response.get_json()
    assert confirm_payload['data']['jobId'] == 702
    assert confirm_payload['data']['runtimeAudit']['gateMode'] == 'manual_continue'

    replay_response = client.post('/api/v1/batches/21/replay', json={'operator': 'evan'})
    assert replay_response.status_code == 202
    replay_payload = replay_response.get_json()
    assert replay_payload['data']['jobId'] == 703
    assert replay_payload['data']['batchId'] == 22

    recent_response = client.get('/api/v1/batches?shopId=1&datasetKind=orders&status=imported')
    assert recent_response.status_code == 200
    recent_payload = recent_response.get_json()
    assert recent_payload['data']['items'][0]['batchId'] == 21

    detail_response = client.get('/api/v1/batches/22')
    assert detail_response.status_code == 200
    detail_payload = detail_response.get_json()
    assert detail_payload['data']['batchId'] == 22
    assert isinstance(detail_payload['data']['rawRecords'], list)

    timeline_response = client.get('/api/v1/batches/22/timeline')
    assert timeline_response.status_code == 200
    assert timeline_response.get_json()['data']['total'] == 3
