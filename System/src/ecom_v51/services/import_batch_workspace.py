from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class ImportBatchWorkspaceService:
    """Durable batch workspace store.

    Phase 2:
    - keeps the current session-based parse/confirm flow working;
    - persists batch summaries and snapshots to disk so the workspace survives process restarts;
    - appends an event timeline so the workspace can render audit-oriented batch detail;
    - best-effort shadow writes summary information into ImportBatch / ImportBatchFile when DB is available.
    """

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = Path(root_dir)
        self.workspace_dir = self.root_dir / 'data' / 'import_batch_workspace'
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.workspace_dir / 'batch_index.json'

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).astimezone().isoformat()

    def _load_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            return default

    def _save_json(self, path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def _load_index(self) -> Dict[str, Any]:
        index = self._load_json(self.index_path, default={'version': 'p1.v2', 'items': []})
        if not isinstance(index, dict):
            index = {'version': 'p1.v2', 'items': []}
        items = index.get('items')
        if not isinstance(items, list):
            index['items'] = []
        return index

    def _save_index(self, index: Dict[str, Any]) -> None:
        items = index.get('items') or []
        items = sorted(items, key=lambda x: str(x.get('updatedAt') or ''), reverse=True)
        index = {'version': 'p1.v2', 'items': items}
        self._save_json(self.index_path, index)

    def _record_path(self, workspace_batch_id: str) -> Path:
        return self.workspace_dir / f'{workspace_batch_id}.json'

    @staticmethod
    def _trim_list(values: Any, limit: int = 10) -> List[Any]:
        if not isinstance(values, list):
            return []
        return values[: max(0, int(limit))]

    def _build_summary(self, record: Dict[str, Any]) -> Dict[str, Any]:
        snapshot = record.get('finalSnapshot') or record.get('parseSnapshot') or {}
        events = record.get('events') or []
        latest_event = events[-1] if events else {}
        confirm_meta = record.get('confirmResultMeta') or {}
        return {
            'workspaceBatchId': record.get('workspaceBatchId'),
            'dbBatchId': record.get('dbBatchId'),
            'formalBatchId': record.get('formalBatchId'),
            'sessionId': record.get('sessionId'),
            'datasetKind': record.get('datasetKind'),
            'importProfile': record.get('importProfile'),
            'fileName': record.get('fileName'),
            'sourceMode': record.get('sourceMode'),
            'shopId': record.get('shopId'),
            'operator': record.get('operator'),
            'createdAt': record.get('createdAt'),
            'updatedAt': record.get('updatedAt'),
            'batchStatus': snapshot.get('batchStatus'),
            'transportStatus': snapshot.get('transportStatus'),
            'semanticStatus': snapshot.get('semanticStatus'),
            'importabilityStatus': snapshot.get('importabilityStatus'),
            'importedRows': snapshot.get('importedRows') or 0,
            'quarantineCount': snapshot.get('quarantineCount') or 0,
            'lastEventType': latest_event.get('eventType'),
            'lastEventAt': latest_event.get('at'),
            'confirmStatus': confirm_meta.get('status'),
        }

    def _upsert_index_item(self, summary: Dict[str, Any]) -> None:
        index = self._load_index()
        items: List[Dict[str, Any]] = index.get('items') or []
        items = [x for x in items if int(x.get('sessionId') or -1) != int(summary.get('sessionId') or -2)]
        items.append(summary)
        index['items'] = items
        self._save_index(index)

    def _find_index_item(self, session_id: int) -> Optional[Dict[str, Any]]:
        index = self._load_index()
        for item in index.get('items') or []:
            if int(item.get('sessionId') or -1) == int(session_id):
                return item
        return None

    def _load_record_by_workspace_batch_id(self, workspace_batch_id: str) -> Optional[Dict[str, Any]]:
        workspace_batch_id = str(workspace_batch_id or '').strip()
        if not workspace_batch_id:
            return None
        record = self._load_json(self._record_path(workspace_batch_id), default=None)
        return record if isinstance(record, dict) else None

    def _load_record_by_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        item = self._find_index_item(session_id)
        if not item:
            return None
        return self._load_record_by_workspace_batch_id(str(item.get('workspaceBatchId') or '').strip())

    def _safe_dict(self, payload: Any) -> Dict[str, Any]:
        return payload if isinstance(payload, dict) else {}

    def _append_event(self, record: Dict[str, Any], event_type: str, payload: Dict[str, Any]) -> None:
        events = record.get('events')
        if not isinstance(events, list):
            events = []
        snapshot = self._safe_dict(payload.get('batchSnapshot'))
        event = {
            'eventType': event_type,
            'at': self._now_iso(),
            'status': payload.get('status'),
            'finalStatus': payload.get('finalStatus'),
            'batchStatus': snapshot.get('batchStatus') or payload.get('batchStatus'),
            'transportStatus': snapshot.get('transportStatus') or payload.get('transportStatus'),
            'semanticStatus': snapshot.get('semanticStatus') or payload.get('semanticStatus'),
            'importabilityStatus': snapshot.get('importabilityStatus') or payload.get('importabilityStatus'),
            'importedRows': snapshot.get('importedRows') or payload.get('importedRows') or 0,
            'quarantineCount': snapshot.get('quarantineCount') or payload.get('quarantineCount') or 0,
            'errorRows': payload.get('errorRows') or 0,
            'reasonSummary': {
                'errors': self._trim_list(payload.get('errors') or [], 6),
                'importabilityReasons': self._trim_list(payload.get('importabilityReasons') or [], 8),
                'semanticGateReasons': self._trim_list(payload.get('semanticGateReasons') or [], 8),
                'riskOverrideReasons': self._trim_list(payload.get('riskOverrideReasons') or [], 8),
                'topUnmappedHeaders': self._trim_list(payload.get('topUnmappedHeaders') or [], 8),
            },
        }
        events.append(event)
        record['events'] = events[-20:]

    def _sync_db_parse(self, record: Dict[str, Any], parse_result: Dict[str, Any]) -> Optional[int]:
        try:
            from ecom_v51.db.session import get_engine, get_session
            from ecom_v51.db.models import ImportBatch, ImportBatchFile

            engine = get_engine()
            ImportBatch.__table__.create(bind=engine, checkfirst=True)
            ImportBatchFile.__table__.create(bind=engine, checkfirst=True)

            existing_id = record.get('dbBatchId')
            snapshot = record.get('parseSnapshot') or {}
            with get_session() as session:
                batch = None
                if existing_id:
                    batch = session.get(ImportBatch, int(existing_id))
                if batch is None:
                    batch = ImportBatch(
                        source_type=str(record.get('sourceMode') or 'file'),
                        platform_code=str(record.get('platform') or 'generic'),
                        shop_id=(int(record.get('shopId')) if record.get('shopId') not in (None, '') else None),
                        started_at=datetime.now(timezone.utc),
                        finished_at=None,
                        status=str(snapshot.get('batchStatus') or 'mapped'),
                        success_count=0,
                        error_count=int(parse_result.get('unmappedCount') or 0),
                        message=f"workspaceBatchId={record.get('workspaceBatchId')};sessionId={record.get('sessionId')};dataset={record.get('datasetKind')};profile={record.get('importProfile')}",
                    )
                    session.add(batch)
                    session.flush()
                    session.add(ImportBatchFile(
                        batch_id=batch.id,
                        file_name=str(record.get('fileName') or 'unknown'),
                        sheet_name=str(parse_result.get('selectedSheet') or '') or None,
                        detected_header_row=int(parse_result.get('headerRow') or 0) or None,
                        detected_key_field=str((parse_result.get('diagnosis') or {}).get('keyField') or '') or None,
                        mapped_fields_json=(snapshot.get('mappingSummary') or {}),
                        unmapped_fields_json=list(parse_result.get('topUnmappedHeaders') or []),
                        status=str(snapshot.get('batchStatus') or 'mapped'),
                    ))
                else:
                    batch.status = str(snapshot.get('batchStatus') or batch.status)
                    batch.error_count = int(parse_result.get('unmappedCount') or batch.error_count)
                session.flush()
                return int(batch.id)
        except Exception:
            return None

    def _sync_db_confirm(self, record: Dict[str, Any], confirm_result: Dict[str, Any]) -> Optional[int]:
        try:
            from ecom_v51.db.session import get_engine, get_session
            from ecom_v51.db.models import ImportBatch, ImportBatchFile

            engine = get_engine()
            ImportBatch.__table__.create(bind=engine, checkfirst=True)
            ImportBatchFile.__table__.create(bind=engine, checkfirst=True)

            batch_id = record.get('dbBatchId')
            if not batch_id:
                return None
            snapshot = record.get('finalSnapshot') or record.get('confirmSnapshot') or {}
            with get_session() as session:
                batch = session.get(ImportBatch, int(batch_id))
                if batch is None:
                    return None
                batch.status = str(snapshot.get('batchStatus') or batch.status)
                batch.success_count = int(confirm_result.get('importedRows') or batch.success_count)
                batch.error_count = int(confirm_result.get('errorRows') or batch.error_count)
                batch.finished_at = datetime.now(timezone.utc)
                batch.message = f"workspaceBatchId={record.get('workspaceBatchId')};sessionId={record.get('sessionId')};confirmed=true"
                batch_file = (
                    session.query(ImportBatchFile)
                    .filter(ImportBatchFile.batch_id == batch.id)
                    .order_by(ImportBatchFile.id.desc())
                    .first()
                )
                if batch_file is not None:
                    batch_file.status = str(snapshot.get('batchStatus') or batch_file.status)
                    batch_file.mapped_fields_json = snapshot.get('mappingSummary') or batch_file.mapped_fields_json
                    batch_file.unmapped_fields_json = list(confirm_result.get('topUnmappedHeaders') or batch_file.unmapped_fields_json or [])
                session.flush()
                return int(batch.id)
        except Exception:
            return None

    def register_parse(
        self,
        *,
        session_id: int,
        parse_result: Dict[str, Any],
        shop_id: int,
        operator: str,
        source_mode: str = 'upload',
    ) -> Dict[str, Any]:
        record = self._load_record_by_session(session_id) or {}
        workspace_batch_id = str(record.get('workspaceBatchId') or f'ws-{session_id:06d}')
        snapshot = self._safe_dict(parse_result.get('batchSnapshot'))
        now = self._now_iso()
        record.update({
            'workspaceBatchId': workspace_batch_id,
            'sessionId': int(session_id),
            'datasetKind': parse_result.get('datasetKind') or 'orders',
            'importProfile': parse_result.get('importProfile') or parse_result.get('datasetKind') or 'orders',
            'fileName': parse_result.get('fileName') or Path(str(parse_result.get('filePath') or '')).name or record.get('fileName'),
            'filePath': parse_result.get('filePath') or record.get('filePath'),
            'fileSize': parse_result.get('fileSize'),
            'platform': parse_result.get('platform') or 'generic',
            'sourceMode': source_mode,
            'shopId': int(shop_id),
            'operator': operator,
            'createdAt': record.get('createdAt') or now,
            'updatedAt': now,
            'parseSnapshot': snapshot,
            'confirmSnapshot': None,
            'finalSnapshot': snapshot,
            'confirmResultMeta': {},
            'parseResultMeta': {
                'totalRows': parse_result.get('totalRows'),
                'totalColumns': parse_result.get('totalColumns'),
                'status': parse_result.get('status'),
                'finalStatus': parse_result.get('finalStatus'),
                'mappedCount': parse_result.get('mappedCount'),
                'unmappedCount': parse_result.get('unmappedCount'),
                'mappingCoverage': parse_result.get('mappingCoverage'),
                'mappedConfidence': parse_result.get('mappedConfidence'),
                'selectedSheet': parse_result.get('selectedSheet'),
                'importabilityReasons': parse_result.get('importabilityReasons') or [],
                'semanticGateReasons': parse_result.get('semanticGateReasons') or [],
                'riskOverrideReasons': parse_result.get('riskOverrideReasons') or [],
                'topUnmappedHeaders': parse_result.get('topUnmappedHeaders') or [],
            },
        })
        self._append_event(record, 'parse', parse_result)
        db_id = self._sync_db_parse(record, parse_result)
        if db_id:
            record['dbBatchId'] = int(db_id)
        self._save_json(self._record_path(workspace_batch_id), record)
        summary = self._build_summary(record)
        self._upsert_index_item(summary)
        return summary

    def register_confirm(
        self,
        *,
        session_id: int,
        parse_result: Dict[str, Any],
        confirm_result: Dict[str, Any],
        shop_id: int,
        operator: str,
    ) -> Dict[str, Any]:
        record = self._load_record_by_session(session_id)
        if record is None:
            self.register_parse(
                session_id=session_id,
                parse_result=parse_result,
                shop_id=shop_id,
                operator=operator,
                source_mode=str(parse_result.get('sourceMode') or 'upload'),
            )
            record = self._load_record_by_session(session_id) or {}
        now = self._now_iso()
        snapshot = self._safe_dict(confirm_result.get('batchSnapshot'))
        record.update({
            'workspaceBatchId': record.get('workspaceBatchId') or f'ws-{session_id:06d}',
            'sessionId': int(session_id),
            'datasetKind': confirm_result.get('datasetKind') or parse_result.get('datasetKind') or 'orders',
            'importProfile': confirm_result.get('importProfile') or parse_result.get('importProfile') or 'orders',
            'shopId': int(shop_id),
            'operator': operator,
            'updatedAt': now,
            'confirmSnapshot': snapshot,
            'finalSnapshot': snapshot or record.get('parseSnapshot') or {},
            'confirmResultMeta': {
                'status': confirm_result.get('status'),
                'success': confirm_result.get('success'),
                'importedRows': confirm_result.get('importedRows'),
                'errorRows': confirm_result.get('errorRows'),
                'quarantineCount': confirm_result.get('quarantineCount'),
                'factLoadErrors': confirm_result.get('factLoadErrors'),
                'errors': confirm_result.get('errors') or [],
                'importabilityReasons': confirm_result.get('importabilityReasons') or [],
            },
        })
        self._append_event(record, 'confirm', confirm_result)
        db_id = self._sync_db_confirm(record, confirm_result)
        if db_id:
            record['dbBatchId'] = int(db_id)
        self._save_json(self._record_path(str(record['workspaceBatchId'])), record)
        summary = self._build_summary(record)
        self._upsert_index_item(summary)
        return summary


    def attach_formal_batch_id(
        self,
        *,
        session_id: int | None = None,
        workspace_batch_id: str | None = None,
        formal_batch_id: int | None = None,
    ) -> Optional[Dict[str, Any]]:
        if formal_batch_id in (None, ''):
            return None
        record: Optional[Dict[str, Any]] = None
        if workspace_batch_id:
            record = self._load_record_by_workspace_batch_id(str(workspace_batch_id))
        if record is None and session_id not in (None, ''):
            try:
                record = self._load_record_by_session(int(session_id))
            except Exception:
                record = None
        if record is None:
            return None
        record['formalBatchId'] = int(formal_batch_id)
        record['updatedAt'] = self._now_iso()
        self._save_json(self._record_path(str(record['workspaceBatchId'])), record)
        summary = self._build_summary(record)
        self._upsert_index_item(summary)
        return summary

    def get_batch(self, session_id: int) -> Optional[Dict[str, Any]]:
        record = self._load_record_by_session(session_id)
        if record is None:
            return None
        return self._detail_payload(record)

    def get_batch_by_workspace_id(self, workspace_batch_id: str) -> Optional[Dict[str, Any]]:
        record = self._load_record_by_workspace_batch_id(workspace_batch_id)
        if record is None:
            return None
        return self._detail_payload(record)

    def _detail_payload(self, record: Dict[str, Any]) -> Dict[str, Any]:
        summary = self._build_summary(record)
        return {
            **summary,
            'batchId': record.get('formalBatchId') or record.get('dbBatchId'),
            'formalBatchId': record.get('formalBatchId'),
            'parseSnapshot': record.get('parseSnapshot') or None,
            'confirmSnapshot': record.get('confirmSnapshot') or None,
            'finalSnapshot': record.get('finalSnapshot') or record.get('confirmSnapshot') or record.get('parseSnapshot') or None,
            'parseResultMeta': record.get('parseResultMeta') or {},
            'confirmResultMeta': record.get('confirmResultMeta') or {},
            'eventTimeline': record.get('events') or [],
        }

    def list_batches(self, limit: int = 20) -> Dict[str, Any]:
        index = self._load_index()
        items = index.get('items') or []
        items = sorted(items, key=lambda x: str(x.get('updatedAt') or ''), reverse=True)
        return {
            'contractVersion': 'p1.v2',
            'source': 'workspace_store',
            'items': items[: max(1, int(limit))],
            'total': len(items),
        }
