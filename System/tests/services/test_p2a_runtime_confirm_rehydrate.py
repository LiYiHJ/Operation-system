from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ecom_v51.services.batch_runtime_service import BatchRuntimeService


class DummyImportService:
    def __init__(self, source_path: Path) -> None:
        self.source_path = source_path
        self.parsed_calls: list[str] = []
        self.confirm_calls: list[int] = []

    def get_session_result(self, session_id: int):
        return None

    def parse_import_file(self, file_path: str, shop_id: int = 1, operator: str = 'frontend_user'):
        self.parsed_calls.append(file_path)
        return {
            'sessionId': 44,
            'fileName': Path(file_path).name,
            'selectedSheet': 'Sheet1',
            'status': 'success',
            'finalStatus': 'passed',
            'mappedCount': 3,
            'unmappedCount': 0,
            'mappingCoverage': 1.0,
            'mappedConfidence': 0.99,
            'fieldMappings': [],
            'semanticGateReasons': [],
            'riskOverrideReasons': [],
            'topUnmappedHeaders': [],
            'batchSnapshot': {
                'contractVersion': 'p2a.v1',
                'batchStatus': 'validated',
                'transportStatus': 'passed',
                'semanticStatus': 'passed',
                'importabilityStatus': 'passed',
            },
        }

    def confirm_import(self, session_id: int, shop_id: int, manual_overrides=None, operator: str = 'frontend_user'):
        self.confirm_calls.append(session_id)
        return {
            'status': 'success',
            'success': True,
            'importedRows': 12,
            'errorRows': 0,
            'quarantineCount': 1,
            'importabilityStatus': 'risk',
            'importabilityReasons': ['partial_quarantine'],
            'errors': [],
            'warnings': [],
            'batchSnapshot': {
                'contractVersion': 'p2a.v1',
                'batchStatus': 'partially_imported',
                'transportStatus': 'passed',
                'semanticStatus': 'passed',
                'importabilityStatus': 'risk',
                'quarantineCount': 1,
                'importedRows': 12,
            },
            'runtimeAudit': {},
        }


class DummyWorkspaceService:
    def __init__(self) -> None:
        self.register_confirm_calls: list[dict] = []
        self.attach_calls: list[dict] = []

    def register_confirm(self, **kwargs):
        self.register_confirm_calls.append(kwargs)
        return {
            'workspaceBatchId': 'ws-000044',
            'dbBatchId': 44,
            'formalBatchId': 21,
        }

    def attach_formal_batch_id(self, **kwargs):
        self.attach_calls.append(kwargs)
        return kwargs

    def get_batch_by_workspace_id(self, workspace_batch_id: str):
        return None


class DummyBatchService:
    def __init__(self, source_path: Path) -> None:
        self.source_path = source_path
        self.saved_confirm_calls: list[dict] = []
        self.audit_events: list[tuple[int, str, dict]] = []
        self.raw_payload_calls: list[dict] = []
        self.updated_jobs: list[tuple[int, dict]] = []

    def get_batch_detail(self, batch_ref: str):
        if str(batch_ref) != '21':
            return None
        return {
            'batchId': 21,
            'workspaceBatchId': 'ws-000021',
            'sessionId': 21,
            'datasetKind': 'orders',
            'importProfile': 'ozon_orders_report',
            'shopId': 1,
            'sourceMode': 'upload',
            'sourceObjects': [{'filePath': str(self.source_path)}],
            'rawRecords': [],
            'manualOverrides': [],
        }

    def create_job(self, **kwargs):
        return {'jobId': 701}

    def update_job(self, job_id: int, **kwargs):
        self.updated_jobs.append((job_id, kwargs))
        return {'jobId': job_id, **kwargs}

    def get_job(self, job_ref: str):
        return {'jobId': int(job_ref), 'jobCode': f'job_{job_ref}'}

    def save_confirm_result(self, **kwargs):
        self.saved_confirm_calls.append(kwargs)
        return {'batchId': 21}

    def record_raw_payload(self, **kwargs):
        self.raw_payload_calls.append(kwargs)
        return None

    def append_audit_event(self, batch_id: int, event_type: str, payload: dict):
        self.audit_events.append((batch_id, event_type, payload))
        return None


def test_confirm_batch_rehydrates_missing_session_and_reuses_original_batch(tmp_path: Path):
    source_path = tmp_path / 'sample.csv'
    source_path.write_text('sku,orders\nA,1\n', encoding='utf-8')

    import_service = DummyImportService(source_path)
    workspace_service = DummyWorkspaceService()
    batch_service = DummyBatchService(source_path)
    runtime = BatchRuntimeService(
        root_dir=tmp_path,
        import_service=import_service,
        workspace_service=workspace_service,
        batch_service=batch_service,
    )

    payload = runtime.confirm_batch(
        batch_ref='21',
        operator='evan',
        gate_mode='manual_continue',
        notes='round2',
        trace_id='trace-round2',
        idempotency_key='idem-round2',
        manual_overrides=[],
    )

    assert payload['status'] == 'completed'
    assert payload['batchId'] == 21
    assert payload['workspaceBatchId'] == 'ws-000021'
    assert payload['runtimeAudit']['sessionMode'] == 'rehydrated'
    assert payload['runtimeAudit']['requestedSessionId'] == 21
    assert payload['runtimeAudit']['confirmedSessionId'] == 44

    assert import_service.parsed_calls == [str(source_path)]
    assert import_service.confirm_calls == [44]

    saved = batch_service.saved_confirm_calls[0]
    assert saved['workspace_batch_id'] == 'ws-000021'
    assert saved['legacy_import_batch_id'] == 21
    assert saved['session_id'] == 44

    event_types = [event_type for _, event_type, _ in batch_service.audit_events]
    assert 'confirm_session_rehydrated' in event_types
    assert 'confirm' in event_types


def test_confirm_batch_still_fails_when_session_missing_and_source_missing(tmp_path: Path):
    class MissingSourceBatchService(DummyBatchService):
        def get_batch_detail(self, batch_ref: str):
            detail = super().get_batch_detail(batch_ref)
            detail['sourceObjects'] = []
            return detail

    source_path = tmp_path / 'missing.csv'
    import_service = DummyImportService(source_path)
    workspace_service = DummyWorkspaceService()
    batch_service = MissingSourceBatchService(source_path)
    runtime = BatchRuntimeService(
        root_dir=tmp_path,
        import_service=import_service,
        workspace_service=workspace_service,
        batch_service=batch_service,
    )

    try:
        runtime.confirm_batch(
            batch_ref='21',
            operator='evan',
            gate_mode='manual_continue',
            notes='round2',
            trace_id='trace-round2',
            idempotency_key=None,
            manual_overrides=[],
        )
    except ValueError as exc:
        assert str(exc) == 'session_missing_use_replay'
    else:
        raise AssertionError('expected ValueError(session_missing_use_replay)')
