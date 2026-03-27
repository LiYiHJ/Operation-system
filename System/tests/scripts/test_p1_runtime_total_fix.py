from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _load_module(rel_path: str, name: str):
    path = ROOT / rel_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_rehydrate_script_prefers_formal_batch_id_and_unwraps_envelope():
    module = _load_module('scripts/p1_round1_rehydrate_batch.py', 'p1_rehydrate_batch_script')
    envelope = {'success': True, 'data': {'items': [{'batchId': 1}]}, 'traceId': 'trc_x'}
    assert module._unwrap_api_payload(envelope) == {'items': [{'batchId': 1}]}

    confirm_body = {'formalBatchId': 1, 'batchId': 17, 'persistedBatchId': 17}
    recent_items = [{'batchId': 1, 'workspaceBatchId': 'ws-000003'}]
    assert module._resolve_formal_batch_id(confirm_body, recent_items, 'ws-000003') == 1


def test_rehydrate_checks_accepts_wrapped_payload_and_empty_reason_buckets():
    module = _load_module('scripts/run_p1_round1_rehydrate_checks.py', 'p1_rehydrate_checks_script')
    envelope = {'success': True, 'data': {'reasonBuckets': []}, 'traceId': 'trc_x'}
    assert module._unwrap_api_payload(envelope) == {'reasonBuckets': []}
