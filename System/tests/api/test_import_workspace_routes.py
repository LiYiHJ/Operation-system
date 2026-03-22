from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ecom_v51.api.app import create_app
from ecom_v51.api.routes import import_route


class DummyWorkspace:
    def list_batches(self, limit: int = 20):
        return {
            'contractVersion': 'p1.v1',
            'source': 'workspace_store',
            'total': 1,
            'items': [
                {
                    'workspaceBatchId': 'ws-000001',
                    'sessionId': 1,
                    'datasetKind': 'orders',
                    'batchStatus': 'validated',
                }
            ],
        }

    def get_batch(self, session_id: int):
        if session_id != 1:
            return None
        return {
            'workspaceBatchId': 'ws-000001',
            'sessionId': 1,
            'finalSnapshot': {
                'contractVersion': 'p1.v1',
                'datasetKind': 'orders',
                'batchStatus': 'validated',
                'transportStatus': 'passed',
                'semanticStatus': 'passed',
                'importabilityStatus': 'risk',
                'quarantineCount': 0,
                'importedRows': 0,
            },
        }


def test_import_batches_list_and_detail(monkeypatch):
    monkeypatch.setattr(import_route, 'batch_workspace', DummyWorkspace())
    app = create_app('development')
    client = app.test_client()

    list_resp = client.get('/api/import/batches?limit=5')
    assert list_resp.status_code == 200
    list_payload = list_resp.get_json()
    assert list_payload['source'] == 'workspace_store'
    assert list_payload['items'][0]['workspaceBatchId'] == 'ws-000001'

    detail_resp = client.get('/api/import/batches/1')
    assert detail_resp.status_code == 200
    detail_payload = detail_resp.get_json()
    assert detail_payload['workspaceBatchId'] == 'ws-000001'
    assert detail_payload['finalSnapshot']['batchStatus'] == 'validated'
