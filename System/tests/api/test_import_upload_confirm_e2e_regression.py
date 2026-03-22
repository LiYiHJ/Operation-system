from __future__ import annotations

import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ecom_v51.api.app import create_app
from ecom_v51.api.routes import import_route
from ecom_v51.api.routes.v1 import batches as v1_batches


class FakeWorkspace:
    def __init__(self) -> None:
        self.by_session = {}
        self.by_workspace = {}

    def register_parse(self, session_id: int, parse_result: dict, shop_id: int, operator: str, source_mode: str):
        payload = {
            'workspaceBatchId': 'ws-000001',
            'dbBatchId': 1,
            'sessionId': session_id,
            'datasetKind': parse_result.get('datasetKind'),
            'importProfile': parse_result.get('importProfile'),
            'sourceMode': source_mode,
            'fileName': parse_result.get('fileName'),
            'parseResultMeta': dict(parse_result),
            'parseSnapshot': dict(parse_result.get('batchSnapshot') or {}),
            'finalSnapshot': dict(parse_result.get('batchSnapshot') or {}),
            'eventTimeline': [{'eventType': 'parse', 'batchStatus': 'validated'}],
        }
        self.by_session[session_id] = payload
        self.by_workspace['ws-000001'] = payload
        return {'workspaceBatchId': 'ws-000001', 'dbBatchId': 1}

    def register_confirm(self, session_id: int, parse_result: dict, confirm_result: dict, shop_id: int, operator: str):
        payload = self.by_session[session_id]
        payload['confirmResultMeta'] = dict(confirm_result)
        payload['confirmSnapshot'] = dict(confirm_result.get('batchSnapshot') or {})
        payload['finalSnapshot'] = dict(confirm_result.get('batchSnapshot') or {})
        payload['eventTimeline'] = [
            {'eventType': 'parse', 'batchStatus': 'validated'},
            {'eventType': 'confirm', 'batchStatus': 'imported'},
        ]
        return {'workspaceBatchId': 'ws-000001', 'dbBatchId': 1}

    def get_batch(self, session_id: int):
        return self.by_session.get(session_id)

    def get_batch_by_workspace_id(self, workspace_batch_id: str):
        return self.by_workspace.get(workspace_batch_id)

    def list_batches(self, limit: int = 20):
        return {'source': 'workspace_store', 'total': len(self.by_session), 'items': list(self.by_session.values())[:limit]}


class FakeBatchService:
    CONTRACT_VERSION = 'p0a.v1'

    def __init__(self) -> None:
        self.detail = None
        self.timeline = None
        self.quarantine = None

    def _normalize_field_mappings(self, parse_result: dict):
        source_headers = [
            'Динамика',
            'Динамика',
            'Артикул',
        ]
        normalized = []
        seen = {}
        total = {h: source_headers.count(h) for h in source_headers}
        for idx, header in enumerate(source_headers, start=1):
            seen[header] = seen.get(header, 0) + 1
            key = f'{header}__dup{seen[header]}' if total[header] > 1 else header
            normalized.append({
                'sourceHeader': header,
                'sourceHeaderKey': key,
                'sourceHeaderOrdinal': seen[header],
                'sourceHeaderDuplicateCount': total[header],
                'mappingStatus': 'dynamic_companion' if header == 'Динамика' else 'mapped',
                'targetField': None if header == 'Динамика' else 'sku',
            })
        return normalized

    def save_parse_result(self, session_id: int, parse_result: dict, shop_id: int, operator: str, source_mode: str, workspace_batch_id: str | None = None, legacy_import_batch_id: int | None = None):
        field_mappings = self._normalize_field_mappings(parse_result)
        self.detail = {
            'batchId': 3,
            'workspaceBatchId': workspace_batch_id or 'ws-000001',
            'sessionId': session_id,
            'datasetKind': 'orders',
            'importProfile': 'ozon_orders_report',
            'contractVersion': self.CONTRACT_VERSION,
            'batchStatus': 'validated',
            'transportStatus': 'passed',
            'semanticStatus': 'passed',
            'importabilityStatus': 'risk',
            'parseSnapshot': dict(parse_result.get('batchSnapshot') or {}),
            'confirmSnapshot': {
                'contractVersion': self.CONTRACT_VERSION,
                'mappingSummary': {
                    'mappedCount': 0,
                    'unmappedCount': 0,
                    'mappingCoverage': 0.0,
                    'mappedConfidence': 0.0,
                    'mappedCanonicalFields': [],
                    'topUnmappedHeaders': [],
                },
            },
            'fieldMappings': field_mappings,
            'eventTimeline': [{'eventType': 'parse', 'batchStatus': 'validated'}],
        }
        self.timeline = {
            'batchId': 3,
            'workspaceBatchId': workspace_batch_id or 'ws-000001',
            'sessionId': session_id,
            'contractVersion': self.CONTRACT_VERSION,
            'total': 1,
            'eventTimeline': [{'eventType': 'parse', 'batchStatus': 'validated'}],
            'events': [{'eventType': 'parse', 'batchStatus': 'validated'}],
        }
        self.quarantine = {
            'batchId': 3,
            'workspaceBatchId': workspace_batch_id or 'ws-000001',
            'contractVersion': self.CONTRACT_VERSION,
            'quarantineCount': 0,
            'importabilityStatus': 'risk',
            'reasonList': [],
        }
        return {'batchId': 3, 'workspaceBatchId': workspace_batch_id or 'ws-000001'}

    def save_confirm_result(self, session_id: int, parse_result: dict, confirm_result: dict, shop_id: int, operator: str, manual_overrides: list | None = None, workspace_batch_id: str | None = None, legacy_import_batch_id: int | None = None):
        field_mappings = list(self.detail['fieldMappings'])
        self.detail.update({
            'batchStatus': 'imported',
            'importabilityStatus': 'passed',
            'importedRows': 1372,
            'quarantineCount': 0,
            'confirmSnapshot': {
                'contractVersion': self.CONTRACT_VERSION,
                'datasetKind': 'orders',
                'importProfile': 'ozon_orders_report',
                'batchStatus': 'imported',
                'importabilityStatus': 'passed',
                'mappingSummary': {
                    'mappedCount': 1,
                    'unmappedCount': 2,
                    'mappingCoverage': 0.33,
                    'mappedConfidence': 0.99,
                    'mappedCanonicalFields': ['sku'],
                    'topUnmappedHeaders': ['Динамика'],
                },
            },
            'fieldMappings': field_mappings,
            'eventTimeline': [
                {'eventType': 'parse', 'batchStatus': 'validated'},
                {'eventType': 'confirm', 'batchStatus': 'imported'},
            ],
        })
        self.timeline.update({
            'total': 2,
            'eventTimeline': [
                {'eventType': 'parse', 'batchStatus': 'validated'},
                {'eventType': 'confirm', 'batchStatus': 'imported'},
            ],
            'events': [
                {'eventType': 'parse', 'batchStatus': 'validated'},
                {'eventType': 'confirm', 'batchStatus': 'imported'},
            ],
        })
        self.quarantine.update({
            'quarantineCount': 0,
            'importabilityStatus': 'passed',
            'reasonList': [],
        })
        return {'batchId': 3, 'workspaceBatchId': workspace_batch_id or 'ws-000001'}

    def list_recent_batches(self, limit: int = 20):
        if not self.detail:
            return {'contractVersion': self.CONTRACT_VERSION, 'source': 'ingest_batch', 'total': 0, 'items': []}
        return {
            'contractVersion': self.CONTRACT_VERSION,
            'source': 'ingest_batch',
            'total': 1,
            'items': [{
                'batchId': 3,
                'workspaceBatchId': self.detail['workspaceBatchId'],
                'sessionId': self.detail['sessionId'],
                'datasetKind': 'orders',
                'importProfile': 'ozon_orders_report',
                'batchStatus': self.detail['batchStatus'],
                'transportStatus': 'passed',
                'semanticStatus': 'passed',
                'importabilityStatus': self.detail['importabilityStatus'],
                'importedRows': self.detail.get('importedRows', 0),
                'quarantineCount': self.detail.get('quarantineCount', 0),
                'contractVersion': self.CONTRACT_VERSION,
            }],
        }

    def get_batch_detail(self, batch_ref: str):
        if not self.detail:
            return None
        if str(batch_ref) in {'3', self.detail['workspaceBatchId']}:
            return dict(self.detail)
        return None

    def get_batch_timeline(self, batch_ref: str):
        if not self.timeline:
            return None
        if str(batch_ref) in {'3', self.timeline['workspaceBatchId']}:
            return dict(self.timeline)
        return None

    def get_batch_quarantine_summary(self, batch_ref: str):
        if not self.quarantine:
            return None
        if str(batch_ref) in {'3', self.quarantine['workspaceBatchId']}:
            return dict(self.quarantine)
        return None


def _build_client(monkeypatch, tmp_path):
    session_store = {}
    workspace = FakeWorkspace()
    batch_service = FakeBatchService()

    def fake_parse_import_file(file_path: str, shop_id: int = 1, operator: str = 'frontend_user'):
        result = {
            'sessionId': 11,
            'fileName': 'orders.xlsx',
            'datasetKind': 'orders',
            'importProfile': 'ozon_orders_report',
            'status': 'success',
            'finalStatus': 'passed',
            'mappedCount': 1,
            'unmappedCount': 2,
            'mappingCoverage': 0.33,
            'mappedConfidence': 0.99,
            'selectedSheet': 'Sheet1',
            'topUnmappedHeaders': ['Динамика'],
            'fieldMappings': [
                {'originalField': 'Динамика', 'dynamicCompanion': True},
                {'originalField': 'Динамика', 'dynamicCompanion': True},
                {'originalField': 'Артикул', 'standardField': 'sku', 'confidence': 0.99},
            ],
            'batchSnapshot': {
                'contractVersion': 'p0a.v1',
                'datasetKind': 'orders',
                'importProfile': 'ozon_orders_report',
                'batchStatus': 'validated',
                'transportStatus': 'passed',
                'semanticStatus': 'passed',
                'importabilityStatus': 'risk',
            },
        }
        session_store[11] = dict(result)
        return result

    def fake_get_session_result(session_id: int):
        return session_store.get(session_id, {})

    def fake_confirm_import(session_id: int, shop_id: int, manual_overrides: list | None = None, operator: str = 'frontend_user'):
        return {
            'status': 'success',
            'importedRows': 1372,
            'quarantineCount': 0,
            'errors': [],
            'warnings': [],
            'importabilityStatus': 'passed',
            'importabilityReasons': [],
        }

    monkeypatch.setattr(import_route.import_service, 'parse_import_file', fake_parse_import_file)
    monkeypatch.setattr(import_route.import_service, 'get_session_result', fake_get_session_result)
    monkeypatch.setattr(import_route.import_service, 'confirm_import', fake_confirm_import)
    monkeypatch.setattr(import_route, '_resolve_dataset_contract', lambda dataset_kind, import_profile: {'datasetKind': 'orders', 'importProfile': 'ozon_orders_report'})
    monkeypatch.setattr(import_route, '_attach_parse_contract', lambda result, contract: {**result, 'datasetKind': 'orders', 'importProfile': 'ozon_orders_report', 'batchStatus': 'validated', 'contractVersion': 'p0a.v1', 'batchSnapshot': {'contractVersion': 'p0a.v1', 'datasetKind': 'orders', 'importProfile': 'ozon_orders_report', 'batchStatus': 'validated', 'transportStatus': 'passed', 'semanticStatus': 'passed', 'importabilityStatus': 'risk'}})
    monkeypatch.setattr(import_route, '_attach_confirm_contract', lambda parse_result, result, contract: {**result, 'datasetKind': 'orders', 'importProfile': 'ozon_orders_report', 'batchStatus': 'imported', 'contractVersion': 'p0a.v1', 'batchSnapshot': {'contractVersion': 'p0a.v1', 'datasetKind': 'orders', 'importProfile': 'ozon_orders_report', 'batchStatus': 'imported', 'transportStatus': 'passed', 'semanticStatus': 'passed', 'importabilityStatus': 'passed'}})
    monkeypatch.setattr(import_route, 'batch_workspace', workspace)
    monkeypatch.setattr(import_route, '_get_batch_service', lambda: batch_service)
    monkeypatch.setattr(v1_batches, 'batch_service', batch_service)
    monkeypatch.setattr(import_route, 'UPLOAD_FOLDER', tmp_path)

    app = create_app('development')
    return app.test_client()


def test_upload_confirm_detail_end_to_end(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    upload_response = client.post(
        '/api/import/upload',
        data={
            'file': (io.BytesIO(b'test-orders'), 'orders.xlsx'),
            'shop_id': '1',
            'operator': 'pytest_user',
            'dataset_kind': 'orders',
            'import_profile': 'ozon_orders_report',
        },
        content_type='multipart/form-data',
    )
    assert upload_response.status_code == 200
    upload_payload = upload_response.get_json()
    assert upload_payload['formalized'] is True
    assert upload_payload['formalBatchId'] == 3
    assert upload_payload['workspaceBatchId'] == 'ws-000001'

    confirm_response = client.post(
        '/api/import/confirm',
        json={
            'sessionId': 11,
            'shopId': 1,
            'operator': 'pytest_user',
            'datasetKind': 'orders',
            'importProfile': 'ozon_orders_report',
            'manualOverrides': [],
        },
    )
    assert confirm_response.status_code == 200
    confirm_payload = confirm_response.get_json()
    assert confirm_payload['formalized'] is True
    assert confirm_payload['formalBatchId'] == 3
    assert confirm_payload['batchStatus'] == 'imported'
    assert confirm_payload['importabilityStatus'] == 'passed'

    detail_response = client.get('/api/v1/batches/3')
    assert detail_response.status_code == 200
    detail_payload = detail_response.get_json()['data']
    assert detail_payload['contractVersion'] == 'p0a.v1'
    assert detail_payload['confirmSnapshot']['mappingSummary']['mappedCount'] == 1
    assert detail_payload['fieldMappings'][0]['sourceHeaderKey'] == 'Динамика__dup1'
    assert detail_payload['fieldMappings'][1]['sourceHeaderKey'] == 'Динамика__dup2'

    list_response = client.get('/api/import/batches?limit=5')
    assert list_response.status_code == 200
    list_payload = list_response.get_json()
    assert list_payload['source'] == 'ingest_batch'
    assert list_payload['items'][0]['batchStatus'] == 'imported'
