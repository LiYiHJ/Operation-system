from __future__ import annotations

import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ecom_v51.api.app import create_app
from ecom_v51.api.routes import import_route


def _make_client():
    app = create_app('development')
    app.config['TESTING'] = True
    return app.test_client()


def test_import_upload_route_surfaces_top_level_mapping_metrics(monkeypatch):
    client = _make_client()
    upload_result = {
        'sessionId': 11,
        'mappedCount': 3,
        'unmappedCount': 1,
        'mappingCoverage': 0.75,
        'mappedConfidence': 0.88,
        'confidence': 0.88,
        'semanticMetrics': {
            'mappingCoverage': 0.75,
            'mappedConfidence': 0.88,
        },
    }

    monkeypatch.setattr(import_route.import_service, 'parse_import_file', lambda *args, **kwargs: upload_result)

    response = client.post(
        '/api/import/upload',
        data={
            'file': (io.BytesIO(b'fake,xlsx,content'), 'contract.xlsx'),
            'shop_id': '7',
            'operator': 'pytest',
        },
        content_type='multipart/form-data',
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['mappedCount'] == upload_result['mappedCount']
    assert payload['unmappedCount'] == upload_result['unmappedCount']
    assert payload['mappingCoverage'] == upload_result['mappingCoverage']
    assert payload['mappedConfidence'] == upload_result['mappedConfidence']
    assert payload['semanticMetrics'] == upload_result['semanticMetrics']
    if 'confidence' in payload:
        assert payload['confidence'] == payload['mappedConfidence']


def test_import_confirm_route_keeps_top_level_mapping_metrics_after_manual_override(monkeypatch):
    client = _make_client()
    confirm_result = {
        'status': 'success',
        'batchId': 22,
        'mappedCount': 4,
        'unmappedCount': 0,
        'mappingCoverage': 1.0,
        'mappedConfidence': 0.97,
        'confidence': 0.97,
        'mappedCanonicalFields': ['sku', 'price'],
        'topUnmappedHeaders': [],
    }

    monkeypatch.setattr(import_route.import_service, 'confirm_import', lambda *args, **kwargs: dict(confirm_result))

    response = client.post(
        '/api/import/confirm',
        json={
            'sessionId': 22,
            'shopId': 7,
            'manualOverrides': [{'originalField': 'SKU', 'standardField': 'sku'}],
            'operator': 'pytest',
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['mappedCount'] == confirm_result['mappedCount']
    assert payload['unmappedCount'] == confirm_result['unmappedCount']
    assert payload['mappingCoverage'] == confirm_result['mappingCoverage']
    assert payload['mappedConfidence'] == confirm_result['mappedConfidence']
    assert payload['mappedCanonicalFields'] == confirm_result['mappedCanonicalFields']
    assert payload['topUnmappedHeaders'] == confirm_result['topUnmappedHeaders']
    if 'confidence' in payload:
        assert payload['confidence'] == payload['mappedConfidence']
