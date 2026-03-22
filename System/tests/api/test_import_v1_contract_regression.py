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
            'contractVersion': self.CONTRACT_VERSION,
            'batchStatus': 'imported',
            'confirmSnapshot': {
                'contractVersion': self.CONTRACT_VERSION,
                'datasetKind': 'orders',
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
            'total': len(events),
            'eventTimeline': events,
            'events': events,
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
    dummy_service = DummyBatchService()
    monkeypatch.setattr(v1_batches, 'batch_service', dummy_service)
    monkeypatch.setattr(import_route, '_get_batch_service', lambda: dummy_service)
    monkeypatch.setattr(import_route, 'batch_workspace', DummyWorkspace())
    app = create_app('development')
    return app.test_client()


def test_v1_batch_detail_exposes_consistent_contract(monkeypatch):
    client = _build_client(monkeypatch)

    response = client.get('/api/v1/batches/3')
    assert response.status_code == 200
    payload = response.get_json()

    assert payload['success'] is True
    assert payload['data']['contractVersion'] == 'p0a.v1'
    assert payload['data']['confirmSnapshot']['contractVersion'] == 'p0a.v1'
    assert payload['data']['confirmSnapshot']['mappingSummary']['mappedCount'] == 39
    assert payload['data']['fieldMappings'][0]['sourceHeaderKey'] == 'Динамика__dup1'


def test_v1_batch_timeline_exposes_events_and_total(monkeypatch):
    client = _build_client(monkeypatch)

    response = client.get('/api/v1/batches/3/timeline')
    assert response.status_code == 200
    payload = response.get_json()

    assert payload['success'] is True
    assert payload['data']['contractVersion'] == 'p0a.v1'
    assert payload['data']['total'] == 2
    assert len(payload['data']['events']) == 2
    assert len(payload['data']['eventTimeline']) == 2


def test_legacy_import_routes_delegate_to_formalized_batch(monkeypatch):
    client = _build_client(monkeypatch)

    detail_response = client.get('/api/import/batches/3')
    assert detail_response.status_code == 200
    detail_payload = detail_response.get_json()
    assert detail_payload['contractVersion'] == 'p0a.v1'
    assert detail_payload['confirmSnapshot']['mappingSummary']['mappedCount'] == 39

    audit_response = client.get('/api/import/batches/3/audit')
    assert audit_response.status_code == 200
    audit_payload = audit_response.get_json()
    assert audit_payload['contractVersion'] == 'p0a.v1'
    assert audit_payload['total'] == 2
