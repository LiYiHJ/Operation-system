from __future__ import annotations

import importlib.util
from pathlib import Path

def _load_module(module_name: str, filename: str):
    target = Path(__file__).resolve().parents[2] / 'src' / 'ecom_v51' / 'services' / filename
    spec = importlib.util.spec_from_file_location(module_name, target)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module

BusinessKeyInferenceService = _load_module('business_key_inference_service', 'business_key_inference_service.py').BusinessKeyInferenceService


def test_business_key_inference_does_not_die_when_sku_missing_for_orders():
    service = BusinessKeyInferenceService()
    payload = {'datasetKind': 'orders', 'quarantineCount': 0, 'fieldMappings': [
        {'targetField': 'order_id'}, {'targetField': 'line_no'}, {'targetField': 'price'}, {'targetField': 'quantity'}, {'targetField': 'date'},
    ]}
    candidates = service.infer_candidates(dataset_kind='orders', payload=payload)
    assert candidates[0]['strategyCode'] == 'order_id+line_no'
    assert candidates[0]['keyViabilityScore'] >= 0.6
