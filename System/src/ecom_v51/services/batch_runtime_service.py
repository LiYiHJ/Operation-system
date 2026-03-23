from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from ecom_v51.services.batch_service import BatchService
from ecom_v51.services.import_batch_workspace import ImportBatchWorkspaceService
from ecom_v51.services.import_service import ImportService


class BatchRuntimeService:
    CONTRACT_VERSION = 'p2a.v1'

    def __init__(
        self,
        *,
        root_dir: Path,
        import_service: ImportService,
        workspace_service: ImportBatchWorkspaceService,
        batch_service: BatchService,
    ) -> None:
        self.root_dir = Path(root_dir)
        self.import_service = import_service
        self.workspace_service = workspace_service
        self.batch_service = batch_service
        self.upload_dir = self.root_dir / 'uploads'
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _clean_str(value: Any, default: str = '') -> str:
        text = str(value or '').strip()
        return text or default

    def _build_safe_upload_filename(self, raw_filename: str | None) -> str:
        raw_filename = str(raw_filename or '').strip()
        fallback_name = f"upload-{Path.cwd().name}-{hashlib.md5(raw_filename.encode('utf-8', errors='ignore')).hexdigest()[:10]}"
        candidate = secure_filename(raw_filename) if raw_filename else ''
        original_suffix = Path(raw_filename).suffix if raw_filename else ''
        if candidate:
            candidate_path = Path(candidate)
            if not candidate_path.suffix and original_suffix:
                return f"{candidate_path.name}{original_suffix}"
            return candidate
        return f"{fallback_name}{original_suffix}" if original_suffix else fallback_name

    @staticmethod
    def _unwrap_payload(payload: Any) -> Dict[str, Any]:
        if isinstance(payload, dict):
            return payload
        return {}

    @staticmethod
    def _choose_batch_id(*candidates: Any) -> Optional[int]:
        for candidate in candidates:
            try:
                if candidate not in (None, ''):
                    return int(candidate)
            except Exception:
                continue
        return None

    @staticmethod
    def _hash_file(file_path: Path) -> tuple[str, str]:
        digest = hashlib.sha256()
        with file_path.open('rb') as fh:
            while True:
                chunk = fh.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        source_hash = digest.hexdigest()
        source_signature = f"{file_path.name}:{file_path.stat().st_size}:{source_hash[:16]}"
        return source_hash, source_signature

    @staticmethod
    def _preview_text(payload: Dict[str, Any]) -> str:
        preview_rows = payload.get('previewRows') or payload.get('preview') or []
        if not isinstance(preview_rows, list):
            preview_rows = []
        snippets: List[str] = []
        for row in preview_rows[:3]:
            try:
                snippets.append(json.dumps(row, ensure_ascii=False))
            except Exception:
                snippets.append(str(row))
        return '\n'.join(snippets)[:4000]

    def _persist_parse_chain(
        self,
        *,
        parse_result: Dict[str, Any],
        shop_id: int,
        operator: str,
        source_mode: str,
        file_path: Optional[Path],
        trace_id: str,
    ) -> Dict[str, Any]:
        session_id = int(parse_result.get('sessionId') or 0)
        persisted = self.workspace_service.register_parse(
            session_id=session_id,
            parse_result=parse_result,
            shop_id=shop_id,
            operator=operator,
            source_mode=source_mode,
        )
        parse_result['workspaceBatchId'] = persisted.get('workspaceBatchId')
        parse_result['persistedBatchId'] = persisted.get('dbBatchId')
        parse_result['legacyImportBatchId'] = persisted.get('dbBatchId')
        formalized = self.batch_service.save_parse_result(
            session_id=session_id,
            parse_result=parse_result,
            shop_id=shop_id,
            operator=operator,
            source_mode=source_mode,
            workspace_batch_id=persisted.get('workspaceBatchId'),
            legacy_import_batch_id=persisted.get('dbBatchId'),
        )
        formal_batch_id = self._choose_batch_id(
            formalized.get('batchId'),
            persisted.get('formalBatchId'),
            persisted.get('dbBatchId'),
        )
        if formal_batch_id is not None:
            self.workspace_service.attach_formal_batch_id(
                session_id=session_id,
                workspace_batch_id=persisted.get('workspaceBatchId'),
                formal_batch_id=formal_batch_id,
            )
            parse_result['batchId'] = formal_batch_id
            parse_result['formalBatchId'] = formal_batch_id
            parse_result['formalized'] = True

        source_hash = source_signature = None
        if file_path and file_path.exists():
            source_hash, source_signature = self._hash_file(file_path)
        if formal_batch_id is not None:
            self.batch_service.record_raw_payload(
                batch_id=formal_batch_id,
                raw_stage='raw_parse',
                payload={
                    'traceId': trace_id,
                    'datasetKind': parse_result.get('datasetKind'),
                    'importProfile': parse_result.get('importProfile'),
                    'status': parse_result.get('status'),
                    'finalStatus': parse_result.get('finalStatus'),
                    'fieldMappings': list(parse_result.get('fieldMappings') or [])[:20],
                    'topUnmappedHeaders': list(parse_result.get('topUnmappedHeaders') or []),
                    'batchSnapshot': dict(parse_result.get('batchSnapshot') or {}),
                    'sourcePath': str(file_path) if file_path else None,
                    'filePath': str(file_path) if file_path else None,
                    'fileName': parse_result.get('fileName'),
                    'fileSize': file_path.stat().st_size if file_path and file_path.exists() else None,
                },
                source_name=parse_result.get('fileName'),
                source_mode=source_mode,
                source_hash=source_hash,
                source_signature=source_signature,
                preview_text=self._preview_text(parse_result),
            )
            self.batch_service.append_audit_event(
                formal_batch_id,
                'replay_parse' if source_mode == 'replay' else 'parse',
                {
                    'eventType': 'replay_parse' if source_mode == 'replay' else 'parse',
                    'traceId': trace_id,
                    'batchId': formal_batch_id,
                    'workspaceBatchId': persisted.get('workspaceBatchId'),
                    'sessionId': session_id,
                    'batchStatus': (parse_result.get('batchSnapshot') or {}).get('batchStatus'),
                    'importabilityStatus': (parse_result.get('batchSnapshot') or {}).get('importabilityStatus'),
                    'status': parse_result.get('status'),
                },
            )
        return {
            'persisted': persisted,
            'formalized': formalized,
            'formalBatchId': formal_batch_id,
            'sourceHash': source_hash,
            'sourceSignature': source_signature,
        }

    def _persist_confirm_chain(
        self,
        *,
        parse_result: Dict[str, Any],
        confirm_result: Dict[str, Any],
        shop_id: int,
        operator: str,
        manual_overrides: List[Dict[str, Any]],
        trace_id: str,
        source_mode: str,
        file_path: Optional[Path],
    ) -> Dict[str, Any]:
        session_id = int(parse_result.get('sessionId') or 0)
        persisted = self.workspace_service.register_confirm(
            session_id=session_id,
            parse_result=parse_result,
            confirm_result=confirm_result,
            shop_id=shop_id,
            operator=operator,
        )
        formalized = self.batch_service.save_confirm_result(
            session_id=session_id,
            parse_result=parse_result,
            confirm_result=confirm_result,
            shop_id=shop_id,
            operator=operator,
            manual_overrides=manual_overrides,
            workspace_batch_id=persisted.get('workspaceBatchId'),
            legacy_import_batch_id=persisted.get('dbBatchId'),
        )
        formal_batch_id = self._choose_batch_id(
            confirm_result.get('formalBatchId'),
            confirm_result.get('batchId'),
            formalized.get('batchId'),
            persisted.get('formalBatchId'),
            persisted.get('dbBatchId'),
        )
        if formal_batch_id is not None:
            self.workspace_service.attach_formal_batch_id(
                session_id=session_id,
                workspace_batch_id=persisted.get('workspaceBatchId'),
                formal_batch_id=formal_batch_id,
            )
            confirm_result['batchId'] = formal_batch_id
            confirm_result['formalBatchId'] = formal_batch_id
            confirm_result['formalized'] = True

        source_hash = source_signature = None
        if file_path and file_path.exists():
            source_hash, source_signature = self._hash_file(file_path)
        if formal_batch_id is not None:
            self.batch_service.record_raw_payload(
                batch_id=formal_batch_id,
                raw_stage='normalized_confirm',
                payload={
                    'traceId': trace_id,
                    'status': confirm_result.get('status'),
                    'success': confirm_result.get('success'),
                    'importedRows': confirm_result.get('importedRows'),
                    'quarantineCount': confirm_result.get('quarantineCount'),
                    'errors': list(confirm_result.get('errors') or []),
                    'batchSnapshot': dict(confirm_result.get('batchSnapshot') or {}),
                    'importabilityReasons': list(confirm_result.get('importabilityReasons') or []),
                    'sourcePath': str(file_path) if file_path else None,
                    'filePath': str(file_path) if file_path else None,
                    'fileName': parse_result.get('fileName'),
                },
                source_name=parse_result.get('fileName'),
                source_mode=source_mode,
                source_hash=source_hash,
                source_signature=source_signature,
                preview_text=self._preview_text(confirm_result),
            )
            self.batch_service.append_audit_event(
                formal_batch_id,
                'replay_confirm' if source_mode == 'replay' else 'confirm',
                {
                    'eventType': 'replay_confirm' if source_mode == 'replay' else 'confirm',
                    'traceId': trace_id,
                    'batchId': formal_batch_id,
                    'workspaceBatchId': persisted.get('workspaceBatchId'),
                    'sessionId': session_id,
                    'batchStatus': (confirm_result.get('batchSnapshot') or {}).get('batchStatus') or confirm_result.get('batchStatus'),
                    'importabilityStatus': (confirm_result.get('batchSnapshot') or {}).get('importabilityStatus') or confirm_result.get('importabilityStatus'),
                    'status': confirm_result.get('status'),
                    'importedRows': confirm_result.get('importedRows') or 0,
                    'quarantineCount': confirm_result.get('quarantineCount') or 0,
                },
            )
        return {
            'persisted': persisted,
            'formalized': formalized,
            'formalBatchId': formal_batch_id,
            'sourceHash': source_hash,
            'sourceSignature': source_signature,
        }

    def _candidate_source_paths(self, detail: Dict[str, Any]) -> List[Path]:
        candidates: List[Path] = []
        for source in detail.get('sourceObjects') or []:
            file_path = str(source.get('filePath') or '').strip()
            if file_path:
                candidates.append(Path(file_path).expanduser())
            content_meta = dict(source.get('contentMeta') or {})
            meta_path = str(content_meta.get('sourcePath') or '').strip()
            if meta_path:
                candidates.append(Path(meta_path).expanduser())
        for raw_record in detail.get('rawRecords') or []:
            payload = dict(raw_record.get('payload') or {})
            file_path = str(payload.get('sourcePath') or payload.get('filePath') or '').strip()
            if file_path:
                candidates.append(Path(file_path).expanduser())
        workspace_batch_id = detail.get('workspaceBatchId')
        if workspace_batch_id:
            persisted = self.workspace_service.get_batch_by_workspace_id(str(workspace_batch_id)) or {}
            file_path = str(persisted.get('filePath') or '').strip()
            if file_path:
                candidates.append(Path(file_path).expanduser())
        return candidates

    def _get_source_path(self, detail: Dict[str, Any]) -> Optional[Path]:
        for candidate in self._candidate_source_paths(detail):
            try:
                resolved = candidate.resolve()
            except Exception:
                resolved = candidate
            if resolved.exists() and resolved.is_file():
                return resolved
        return None

    def get_job(self, job_ref: str) -> Optional[Dict[str, Any]]:
        return self.batch_service.get_job(job_ref)

    def run_upload(
        self,
        *,
        file_storage: FileStorage | None = None,
        file_path: str | None = None,
        shop_id: int,
        operator: str,
        dataset_kind: str | None,
        import_profile: str | None,
        trace_id: str,
        idempotency_key: str | None,
        source_mode: str = 'upload',
    ) -> Dict[str, Any]:
        request_payload = {
            'shopId': shop_id,
            'operator': operator,
            'datasetKind': dataset_kind,
            'profileCode': import_profile,
            'sourceMode': source_mode,
            'filePath': file_path,
            'fileName': getattr(file_storage, 'filename', None),
        }
        job = self.batch_service.create_job(
            job_type='upload',
            operator=operator,
            trace_id=trace_id,
            idempotency_key=idempotency_key,
            request_payload=request_payload,
        )
        job_id = int(job.get('jobId'))
        self.batch_service.update_job(job_id, status='running', event_type='accepted')

        selected_path: Optional[Path] = None
        try:
            if file_storage is not None:
                safe_name = self._build_safe_upload_filename(file_storage.filename)
                selected_path = self.upload_dir / safe_name
                file_storage.save(selected_path)
            elif file_path:
                selected_path = Path(file_path).expanduser().resolve()
            if not selected_path or not selected_path.exists() or not selected_path.is_file():
                raise FileNotFoundError('source_file_not_found')

            parse_result = self.import_service.parse_import_file(str(selected_path), shop_id=shop_id, operator=operator)
            parse_result['sourceMode'] = source_mode
            parse_result['filePath'] = str(selected_path)
            parse_result['fileName'] = parse_result.get('fileName') or selected_path.name
            parse_result['fileSize'] = parse_result.get('fileSize') or selected_path.stat().st_size
            if dataset_kind:
                parse_result['datasetKind'] = dataset_kind
            if import_profile:
                parse_result['importProfile'] = import_profile
            parse_info = self._persist_parse_chain(
                parse_result=parse_result,
                shop_id=shop_id,
                operator=operator,
                source_mode=source_mode,
                file_path=selected_path,
                trace_id=trace_id,
            )
            result_payload = {
                'batchId': parse_info.get('formalBatchId'),
                'workspaceBatchId': parse_result.get('workspaceBatchId'),
                'sessionId': parse_result.get('sessionId'),
                'status': 'completed',
                'sourceHash': parse_info.get('sourceHash'),
                'sourceSignature': parse_info.get('sourceSignature'),
                'contractVersion': self.CONTRACT_VERSION,
            }
            self.batch_service.update_job(
                job_id,
                status='completed',
                batch_id=parse_info.get('formalBatchId'),
                result_payload=result_payload,
            )
            return {
                **result_payload,
                'jobId': job_id,
                'jobCode': self.batch_service.get_job(str(job_id)).get('jobCode'),
            }
        except Exception as exc:
            self.batch_service.update_job(job_id, status='failed', error_message=str(exc))
            raise

    def confirm_batch(
        self,
        *,
        batch_ref: str,
        operator: str,
        gate_mode: str,
        notes: str,
        trace_id: str,
        idempotency_key: str | None,
        manual_overrides: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        detail = self.batch_service.get_batch_detail(batch_ref)
        if not detail:
            raise ValueError('batch_not_found')
        session_id = int(detail.get('sessionId') or 0)
        if not session_id:
            raise ValueError('batch_session_missing')
        parse_result = self.import_service.get_session_result(session_id)
        if not parse_result:
            raise ValueError('session_missing_use_replay')
        shop_id = int(detail.get('shopId') or 1)
        manual_overrides = list(manual_overrides or [])
        job = self.batch_service.create_job(
            job_type='confirm',
            batch_id=self._choose_batch_id(detail.get('batchId')),
            operator=operator,
            trace_id=trace_id,
            idempotency_key=idempotency_key,
            request_payload={
                'batchRef': batch_ref,
                'gateMode': gate_mode,
                'notes': notes,
                'manualOverrides': manual_overrides,
            },
        )
        job_id = int(job.get('jobId'))
        self.batch_service.update_job(job_id, status='running', event_type='confirm_started')
        try:
            confirm_result = self.import_service.confirm_import(
                session_id=session_id,
                shop_id=shop_id,
                manual_overrides=manual_overrides,
                operator=operator,
            )
            file_path = self._get_source_path(detail)
            confirm_info = self._persist_confirm_chain(
                parse_result=parse_result,
                confirm_result=confirm_result,
                shop_id=shop_id,
                operator=operator,
                manual_overrides=manual_overrides,
                trace_id=trace_id,
                source_mode=str(parse_result.get('sourceMode') or detail.get('sourceMode') or 'upload'),
                file_path=file_path,
            )
            result_payload = {
                'batchId': confirm_info.get('formalBatchId'),
                'workspaceBatchId': confirm_result.get('workspaceBatchId'),
                'importedRows': confirm_result.get('importedRows'),
                'quarantinedRows': confirm_result.get('quarantineCount'),
                'importabilityStatus': confirm_result.get('importabilityStatus'),
                'runtimeAudit': {
                    'gateMode': gate_mode,
                    'notes': notes,
                },
                'status': 'completed',
                'contractVersion': self.CONTRACT_VERSION,
            }
            self.batch_service.update_job(job_id, status='completed', batch_id=confirm_info.get('formalBatchId'), result_payload=result_payload)
            return {
                **result_payload,
                'jobId': job_id,
                'jobCode': self.batch_service.get_job(str(job_id)).get('jobCode'),
            }
        except Exception as exc:
            self.batch_service.update_job(job_id, status='failed', error_message=str(exc))
            raise

    def replay_batch(
        self,
        *,
        batch_ref: str,
        operator: str,
        trace_id: str,
        idempotency_key: str | None,
        notes: str,
    ) -> Dict[str, Any]:
        detail = self.batch_service.get_batch_detail(batch_ref)
        if not detail:
            raise ValueError('batch_not_found')
        source_path = self._get_source_path(detail)
        if not source_path:
            raise ValueError('replay_source_not_found')
        shop_id = int(detail.get('shopId') or 1)
        dataset_kind = self._clean_str(detail.get('datasetKind')) or None
        import_profile = self._clean_str(detail.get('importProfile')) or None
        manual_overrides = [dict(item.get('payload') or {}) for item in (detail.get('manualOverrides') or []) if isinstance(item, dict)]
        original_batch_id = self._choose_batch_id(detail.get('batchId'))
        job = self.batch_service.create_job(
            job_type='replay',
            batch_id=original_batch_id,
            operator=operator,
            trace_id=trace_id,
            idempotency_key=idempotency_key,
            request_payload={
                'batchRef': batch_ref,
                'sourcePath': str(source_path),
                'notes': notes,
            },
        )
        job_id = int(job.get('jobId'))
        self.batch_service.update_job(job_id, status='running', event_type='replay_started')
        try:
            parse_result = self.import_service.parse_import_file(str(source_path), shop_id=shop_id, operator=operator)
            parse_result['sourceMode'] = 'replay'
            if dataset_kind:
                parse_result['datasetKind'] = dataset_kind
            if import_profile:
                parse_result['importProfile'] = import_profile
            parse_info = self._persist_parse_chain(
                parse_result=parse_result,
                shop_id=shop_id,
                operator=operator,
                source_mode='replay',
                file_path=source_path,
                trace_id=trace_id,
            )
            confirm_result = self.import_service.confirm_import(
                session_id=int(parse_result.get('sessionId') or 0),
                shop_id=shop_id,
                manual_overrides=manual_overrides,
                operator=operator,
            )
            confirm_info = self._persist_confirm_chain(
                parse_result=parse_result,
                confirm_result=confirm_result,
                shop_id=shop_id,
                operator=operator,
                manual_overrides=manual_overrides,
                trace_id=trace_id,
                source_mode='replay',
                file_path=source_path,
            )
            result_payload = {
                'originalBatchId': original_batch_id,
                'batchId': confirm_info.get('formalBatchId') or parse_info.get('formalBatchId'),
                'workspaceBatchId': confirm_result.get('workspaceBatchId') or parse_result.get('workspaceBatchId'),
                'status': 'completed',
                'notes': notes,
                'contractVersion': self.CONTRACT_VERSION,
            }
            self.batch_service.update_job(job_id, status='completed', batch_id=result_payload.get('batchId'), result_payload=result_payload)
            if original_batch_id:
                self.batch_service.append_audit_event(
                    original_batch_id,
                    'replay_requested',
                    {
                        'eventType': 'replay_requested',
                        'jobId': job_id,
                        'traceId': trace_id,
                        'targetBatchId': result_payload.get('batchId'),
                        'notes': notes,
                    },
                )
            return {
                **result_payload,
                'jobId': job_id,
                'jobCode': self.batch_service.get_job(str(job_id)).get('jobCode'),
            }
        except Exception as exc:
            self.batch_service.update_job(job_id, status='failed', error_message=str(exc))
            raise
