from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ecom_v51.api.app import create_app
from ecom_v51.api.routes.v1 import batches as v1_batches
from ecom_v51.api.routes import import_route


class DummyBatchService:
    CONTRACT_VERSION = 'p0a.v1'

    def list_recent_batches(self, limit: int = 20):
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'source': 'ingest_batch',
            'total': 1,
            'items': [
                {
                    'batchId': 3,
                    'workspaceBatchId': 'ws-000001',
                    'sessionId': 1,
                    'datasetKind': 'orders',
                    'importProfile': 'ozon_orders_report',
                    'batchStatus': 'imported',
                    'transportStatus': 'passed',
                    'semanticStatus': 'passed',
                    'importabilityStatus': 'passed',
                    'importedRows': 1372,
                    'quarantineCount': 0,
                    'contractVersion': self.CONTRACT_VERSION,
                }
            ],
        }

    def get_batch_detail(self, batch_ref: str):
        if str(batch_ref) != '3':
            return None
        return {
            'batchId': 3,
            'workspaceBatchId': 'ws-000001',
            'sessionId': 1,
            'datasetKind': 'orders',
            'importProfile': 'ozon_orders_report',
            'contractVersion': self.CONTRACT_VERSION,
            'batchStatus': 'imported',
            'transportStatus': 'passed',
            'semanticStatus': 'passed',
            'importabilityStatus': 'passed',
            'confirmSnapshot': {
                'contractVersion': self.CONTRACT_VERSION,
                'mappingSummary': {
                    'mappedCount': 39,
                    'unmappedCount': 8,
                },
            },
            'fieldMappings': [
                {'sourceHeaderKey': 'Динамика__dup1', 'mappingStatus': 'dynamic_companion'},
                {'sourceHeaderKey': 'Артикул', 'mappingStatus': 'mapped'},
            ],
            'eventTimeline': [
                {'eventType': 'parse', 'batchStatus': 'validated'},
                {'eventType': 'confirm', 'batchStatus': 'imported'},
            ],
        }

    def get_batch_timeline(self, batch_ref: str):
        if str(batch_ref) != '3':
            return None
        events = [
            {'eventType': 'parse', 'batchStatus': 'validated'},
            {'eventType': 'confirm', 'batchStatus': 'imported'},
        ]
        return {
            'batchId': 3,
            'workspaceBatchId': 'ws-000001',
            'sessionId': 1,
            'contractVersion': self.CONTRACT_VERSION,
            'total': 2,
            'events': events,
            'eventTimeline': events,
        }

    def get_batch_quarantine_summary(self, batch_ref: str):
        if str(batch_ref) != '3':
            return None
        return {
            'batchId': 3,
            'workspaceBatchId': 'ws-000001',
            'contractVersion': self.CONTRACT_VERSION,
            'quarantineCount': 0,
            'importabilityStatus': 'passed',
            'reasonList': [],
        }


class DummyWorkspace:
    def get_batch(self, session_id: int):
        return None

    def get_batch_by_workspace_id(self, workspace_batch_id: str):
        return None

    def list_batches(self, limit: int = 20):
        return {'source': 'workspace_store', 'total': 0, 'items': []}


def _build_client(monkeypatch):
    batch_service = DummyBatchService()
    monkeypatch.setattr(v1_batches, 'batch_service', batch_service)
    monkeypatch.setattr(import_route, '_get_batch_service', lambda: batch_service)
    monkeypatch.setattr(import_route, 'batch_workspace', DummyWorkspace())
    app = create_app('development')
    return app.test_client()


def test_v1_batches_list_reads_formalized_source(monkeypatch):
    client = _build_client(monkeypatch)

    response = client.get('/api/v1/batches?limit=5')
    assert response.status_code == 200
    payload = response.get_json()

    assert payload['success'] is True
    assert payload['data']['source'] == 'ingest_batch'
    assert payload['data']['items'][0]['contractVersion'] == 'p0a.v1'


def test_v1_batch_detail_timeline_quarantine_are_consistent(monkeypatch):
    client = _build_client(monkeypatch)

    detail_response = client.get('/api/v1/batches/3')
    assert detail_response.status_code == 200
    detail_payload = detail_response.get_json()['data']
    assert detail_payload['confirmSnapshot']['mappingSummary']['mappedCount'] == 39
    assert detail_payload['fieldMappings'][0]['sourceHeaderKey'] == 'Динамика__dup1'

    timeline_response = client.get('/api/v1/batches/3/timeline')
    assert timeline_response.status_code == 200
    timeline_payload = timeline_response.get_json()['data']
    assert timeline_payload['total'] == 2
    assert len(timeline_payload['events']) == 2

    quarantine_response = client.get('/api/v1/batches/3/quarantine-summary')
    assert quarantine_response.status_code == 200
    quarantine_payload = quarantine_response.get_json()['data']
    assert quarantine_payload['quarantineCount'] == 0
    assert quarantine_payload['importabilityStatus'] == 'passed'
