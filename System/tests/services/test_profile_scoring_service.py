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

ProfileScoringService = _load_module('profile_scoring_service', 'profile_scoring_service.py').ProfileScoringService


def test_profile_scoring_prefers_orders_when_order_like_headers_present():
    service = ProfileScoringService()
    registry = {'datasets': [
        {'datasetKind': 'orders', 'importProfile': 'orders', 'requiredCoreFields': ['order_id', 'line_no', 'sku'], 'optionalCommonFields': ['price', 'quantity', 'date'], 'entityKeyField': 'sku'},
        {'datasetKind': 'ads', 'importProfile': 'ads', 'requiredCoreFields': ['campaign_id', 'date'], 'optionalCommonFields': ['spend', 'clicks'], 'entityKeyField': 'sku'},
        {'datasetKind': 'reviews', 'importProfile': 'reviews', 'requiredCoreFields': ['product_id', 'review_id'], 'optionalCommonFields': ['rating', 'review_date'], 'entityKeyField': 'product_id'},
    ]}
    parse_result = {'datasetKind': 'orders', 'importProfile': 'orders', 'mappingCoverage': 0.82, 'mappedCount': 6, 'unmappedCount': 1, 'fieldMappings': [
        {'targetField': 'order_id'}, {'targetField': 'line_no'}, {'targetField': 'price'}, {'targetField': 'quantity'}, {'targetField': 'date'}, {'targetField': 'sku'},
    ]}
    candidates = service.score_candidates(registry_datasets=registry['datasets'], parse_result=parse_result)
    assert candidates[0]['profileCode'] == 'orders'
    assert candidates[0]['score'] > candidates[1]['score']
