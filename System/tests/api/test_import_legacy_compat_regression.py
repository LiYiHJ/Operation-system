from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ecom_v51.api.app import create_app
from ecom_v51.api.routes import import_route
from ecom_v51.api.routes.v1 import batches as v1_batches


class DummyBatchService:
    CONTRACT_VERSION = 'p0a.v1'

    def __init__(self) -> None:
        self.detail = {
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
                'datasetKind': 'orders',
                'importProfile': 'ozon_orders_report',
                'batchStatus': 'imported',
                'mappingSummary': {
                    'mappedCount': 39,
                    'unmappedCount': 8,
                    'mappingCoverage': 0.83,
                    'mappedConfidence': 0.525,
                    'mappedCanonicalFields': ['product_name', 'sku'],
                    'topUnmappedHeaders': ['SKU'],
                },
            },
            'fieldMappings': [
                {
                    'sourceHeader': 'Динамика',
                    'sourceHeaderKey': 'Динамика__dup1',
                    'sourceHeaderOrdinal': 1,
                    'sourceHeaderDuplicateCount': 26,
                    'mappingStatus': 'dynamic_companion',
                    'targetField': None,
                },
                {
                    'sourceHeader': 'Артикул',
                    'sourceHeaderKey': 'Артикул',
                    'sourceHeaderOrdinal': 1,
                    'sourceHeaderDuplicateCount': 1,
                    'mappingStatus': 'mapped',
                    'targetField': 'sku',
                },
            ],
            'eventTimeline': [
                {'eventType': 'parse', 'batchStatus': 'validated'},
                {'eventType': 'confirm', 'batchStatus': 'imported'},
            ],
        }

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
        if str(batch_ref) in {'3', 'ws-000001'}:
            return dict(self.detail)
        return None

    def get_batch_timeline(self, batch_ref: str):
        if str(batch_ref) not in {'3', 'ws-000001'}:
            return None
        events = list(self.detail['eventTimeline'])
        return {
            'batchId': 3,
            'workspaceBatchId': 'ws-000001',
            'sessionId': 1,
            'contractVersion': self.CONTRACT_VERSION,
            'total': len(events),
            'eventTimeline': events,
            'events': events,
        }

    def get_batch_quarantine_summary(self, batch_ref: str):
        if str(batch_ref) not in {'3', 'ws-000001'}:
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
    def list_batches(self, limit: int = 20):
        return {'source': 'workspace_store', 'total': 0, 'items': []}

    def get_batch(self, session_id: int):
        return None

    def get_batch_by_workspace_id(self, workspace_batch_id: str):
        return None


def _build_client(monkeypatch):
    batch_service = DummyBatchService()
    monkeypatch.setattr(v1_batches, 'batch_service', batch_service)
    monkeypatch.setattr(import_route, '_get_batch_service', lambda: batch_service)
    monkeypatch.setattr(import_route, 'batch_workspace', DummyWorkspace())
    app = create_app('development')
    return app.test_client()


def test_legacy_import_batches_list_prefers_formalized_source(monkeypatch):
    client = _build_client(monkeypatch)

    response = client.get('/api/import/batches?limit=5')
    assert response.status_code == 200
    payload = response.get_json()

    assert payload['source'] == 'ingest_batch'
    assert payload['total'] == 1
    assert payload['items'][0]['contractVersion'] == 'p0a.v1'
    assert payload['items'][0]['batchStatus'] == 'imported'


def test_legacy_workspace_detail_delegates_to_formalized_batch(monkeypatch):
    client = _build_client(monkeypatch)

    response = client.get('/api/import/batches/workspace/ws-000001')
    assert response.status_code == 200
    payload = response.get_json()

    assert payload['batchId'] == 3
    assert payload['workspaceBatchId'] == 'ws-000001'
    assert payload['contractVersion'] == 'p0a.v1'
    assert payload['confirmSnapshot']['mappingSummary']['mappedCount'] == 39


def test_legacy_audit_route_preserves_formalized_timeline(monkeypatch):
    client = _build_client(monkeypatch)

    response = client.get('/api/import/batches/3/audit')
    assert response.status_code == 200
    payload = response.get_json()

    assert payload['contractVersion'] == 'p0a.v1'
    assert payload['total'] == 2
    assert payload['events'][0]['eventType'] == 'parse'
    assert payload['events'][1]['eventType'] == 'confirm'
