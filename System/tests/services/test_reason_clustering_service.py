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

ReasonClusteringService = _load_module('reason_clustering_service', 'reason_clustering_service.py').ReasonClusteringService


def test_reason_clustering_maps_human_text_to_standard_reason_codes():
    service = ReasonClusteringService()
    buckets = service.cluster(['SKU 不能为空', 'order date format invalid', 'unknown currency code: RUB?', 'SKU 不能为空'])
    codes = {item['reasonCode'] for item in buckets}
    assert 'MISSING_PRIMARY_KEY' in codes
    assert 'BAD_DATE' in codes
    assert 'UNKNOWN_CURRENCY' in codes
