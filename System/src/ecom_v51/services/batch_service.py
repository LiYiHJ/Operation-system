from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, inspect, select

from ecom_v51.db.ingest_models import (
    BatchAuditEvent,
    BatchBusinessKeyCandidate,
    BatchFieldMapping,
    BatchGateResult,
    BatchManualOverride,
    BatchProfileCandidate,
    BatchQuarantineRow,
    IngestBatch,
    JobEvent,
    RawRecord,
    ReplayJob,
    IngestSourceObject,
    RegistryDataset,
    RegistryField,
    RegistryGatePolicy,
    RegistryProfile,
)
from ecom_v51.db.session import get_engine, get_session
from ecom_v51.registry.dataset_registry import DatasetRegistryService
from ecom_v51.services.business_key_inference_service import BusinessKeyInferenceService
from ecom_v51.services.import_batch_workspace import ImportBatchWorkspaceService
from ecom_v51.services.importability_score_builder import ImportabilityScoreBuilder
from ecom_v51.services.profile_scoring_service import ProfileScoringService
from ecom_v51.services.reason_clustering_service import ReasonClusteringService


class BatchService:
    CONTRACT_VERSION = 'p2a.v1'
    ALGORITHM_VERSION = 'p1.v1'

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = Path(root_dir)
        self.registry_service = DatasetRegistryService(self.root_dir)
        self.workspace_service = ImportBatchWorkspaceService(self.root_dir)
        self.profile_scoring_service = ProfileScoringService()
        self.business_key_inference_service = BusinessKeyInferenceService()
        self.importability_score_builder = ImportabilityScoreBuilder()
        self.reason_clustering_service = ReasonClusteringService()


    @staticmethod
    def _available_table_names() -> set[str]:
        try:
            return set(inspect(get_engine()).get_table_names())
        except Exception:
            return set()


    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).astimezone().isoformat()

    @staticmethod
    def _int_or_none(value: Any) -> Optional[int]:
        if value in (None, ''):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _int_or_zero(value: Any) -> int:
        if value in (None, ''):
            return 0
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _clean_str(value: Any, default: str = '') -> str:
        text = str(value or '').strip()
        return text or default

    @staticmethod
    def _normalize_mapping_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        raw_items: List[Dict[str, Any]] = []
        duplicate_counter: Dict[str, int] = {}
        for item in payload.get('fieldMappings') or []:
            if not isinstance(item, dict):
                continue
            source_header = str(item.get('originalField') or item.get('sourceHeader') or '').strip()
            if not source_header:
                continue
            raw_items.append(item)
            duplicate_counter[source_header] = duplicate_counter.get(source_header, 0) + 1

        seen_counter: Dict[str, int] = {}
        items: List[Dict[str, Any]] = []
        for column_index, item in enumerate(raw_items, start=1):
            source_header = str(item.get('originalField') or item.get('sourceHeader') or '').strip()
            seen_counter[source_header] = seen_counter.get(source_header, 0) + 1
            duplicate_index = seen_counter[source_header]
            duplicate_total = duplicate_counter.get(source_header, 1)

            if duplicate_total > 1:
                source_header_key = f"{source_header}__dup{duplicate_index}"
            else:
                source_header_key = source_header

            target_field = str(item.get('standardField') or item.get('targetField') or '').strip() or None
            confidence = item.get('confidence')
            try:
                confidence_value = int(float(confidence)) if confidence not in (None, '') else None
            except (TypeError, ValueError):
                confidence_value = None
            mapping_status = 'mapped' if target_field else 'unmapped'
            if item.get('dynamicCompanion'):
                mapping_status = 'dynamic_companion'
            items.append({
                'sourceHeader': source_header_key,
                'sourceHeaderDisplay': source_header,
                'sourceHeaderOrdinal': duplicate_index,
                'sourceHeaderDuplicateCount': duplicate_total,
                'sourceColumnIndex': column_index,
                'targetField': target_field,
                'confidence': confidence_value,
                'mappingStatus': mapping_status,
                'mappingMeta': {
                    'sampleValues': list(item.get('sampleValues') or []),
                    'notes': list(item.get('notes') or []),
                    'dynamicCompanion': item.get('dynamicCompanion'),
                    'excludeFromSemanticGate': bool(item.get('excludeFromSemanticGate') or False),
                    'compressedHeader': item.get('compressedHeader'),
                    'normalizedField': item.get('normalizedField'),
                    'mappingSource': item.get('mappingSource'),
                    'reasons': list(item.get('reasons') or []),
                    'conflicts': list(item.get('conflicts') or []),
                    'isManual': bool(item.get('isManual') or False),
                    'sourceHeaderDisplay': source_header,
                    'sourceHeaderOrdinal': duplicate_index,
                    'sourceHeaderDuplicateCount': duplicate_total,
                    'sourceColumnIndex': column_index,
                },
            })
        return items

    def _upsert_batch_core(
        self,
        *,
        session,
        session_id: int,
        dataset_kind: str,
        import_profile: str,
        source_mode: str,
        source_name: str,
        shop_id: int | None,
        operator: str,
        contract_version: str,
        batch_status: str,
        transport_status: str,
        semantic_status: str,
        importability_status: str,
        imported_rows: int,
        quarantine_count: int,
        raw_parse_meta: Dict[str, Any],
        raw_confirm_meta: Dict[str, Any],
        parse_snapshot: Dict[str, Any],
        confirm_snapshot: Dict[str, Any],
        final_snapshot: Dict[str, Any],
        workspace_batch_id: str | None = None,
        legacy_import_batch_id: int | None = None,
    ) -> IngestBatch:
        batch = None
        normalized_workspace_batch_id = self._clean_str(workspace_batch_id) or None
        if normalized_workspace_batch_id:
            batch = session.execute(
                select(IngestBatch).where(IngestBatch.workspace_batch_id == normalized_workspace_batch_id)
            ).scalar_one_or_none()
        if batch is None and session_id:
            batch = session.execute(
                select(IngestBatch).where(IngestBatch.legacy_session_id == session_id)
            ).scalar_one_or_none()
        if batch is None:
            batch = IngestBatch(
                workspace_batch_id=normalized_workspace_batch_id,
                legacy_session_id=session_id or None,
                legacy_import_batch_id=legacy_import_batch_id,
                dataset_kind=dataset_kind,
                import_profile=import_profile,
                source_mode=source_mode,
                source_name=source_name,
                platform=None,
                shop_id=shop_id,
                operator=operator,
                contract_version=contract_version,
                batch_status=batch_status,
                transport_status=transport_status,
                semantic_status=semantic_status,
                importability_status=importability_status,
                imported_rows=imported_rows,
                quarantine_count=quarantine_count,
                raw_parse_meta=raw_parse_meta,
                raw_confirm_meta=raw_confirm_meta,
                parse_snapshot=parse_snapshot,
                confirm_snapshot=confirm_snapshot,
                final_snapshot=final_snapshot,
            )
            session.add(batch)
            session.flush()
            return batch

        batch.workspace_batch_id = normalized_workspace_batch_id or batch.workspace_batch_id
        batch.legacy_session_id = session_id or batch.legacy_session_id
        batch.legacy_import_batch_id = legacy_import_batch_id or batch.legacy_import_batch_id
        batch.dataset_kind = dataset_kind
        batch.import_profile = import_profile
        batch.source_mode = source_mode
        batch.source_name = source_name
        batch.shop_id = shop_id
        batch.operator = operator
        batch.contract_version = contract_version
        batch.batch_status = batch_status
        batch.transport_status = transport_status
        batch.semantic_status = semantic_status
        batch.importability_status = importability_status
        batch.imported_rows = imported_rows
        batch.quarantine_count = quarantine_count
        batch.raw_parse_meta = raw_parse_meta
        batch.raw_confirm_meta = raw_confirm_meta
        batch.parse_snapshot = parse_snapshot
        batch.confirm_snapshot = confirm_snapshot
        batch.final_snapshot = final_snapshot
        session.flush()
        return batch

    def _upsert_source_object(
        self,
        *,
        session,
        batch_id: int,
        source_mode: str,
        file_name: str,
        file_path: str | None,
        file_size: int | None,
        selected_sheet: str | None,
    ) -> None:
        row = session.execute(
            select(IngestSourceObject).where(IngestSourceObject.batch_id == batch_id).order_by(IngestSourceObject.id.asc())
        ).scalars().first()
        payload = {
            'sourceMode': source_mode,
            'selectedSheet': selected_sheet or '',
        }
        if row is None:
            row = IngestSourceObject(
                batch_id=batch_id,
                object_type='file',
                file_name=file_name or None,
                file_path=file_path or None,
                file_size=file_size,
                content_meta=payload,
            )
            session.add(row)
            return
        row.object_type = 'file'
        row.file_name = file_name or row.file_name
        row.file_path = file_path or row.file_path
        row.file_size = file_size if file_size is not None else row.file_size
        row.content_meta = payload

    def _replace_gate_results(
        self,
        *,
        session,
        batch_id: int,
        parse_result: Dict[str, Any],
        confirm_result: Dict[str, Any] | None = None,
    ) -> None:
        session.execute(delete(BatchGateResult).where(BatchGateResult.batch_id == batch_id))
        confirm_result = confirm_result or {}
        gates = [
            {
                'gate_name': 'transport',
                'gate_status': self._clean_str((parse_result.get('batchSnapshot') or {}).get('transportStatus') or parse_result.get('transportStatus'), 'failed'),
                'reason_list': list(parse_result.get('errors') or []),
                'summary': {
                    'finalStatus': parse_result.get('finalStatus'),
                },
            },
            {
                'gate_name': 'semantic',
                'gate_status': self._clean_str((parse_result.get('batchSnapshot') or {}).get('semanticStatus') or parse_result.get('semanticStatus'), 'failed'),
                'reason_list': list(parse_result.get('semanticGateReasons') or []),
                'summary': {
                    'mappingCoverage': parse_result.get('mappingCoverage'),
                    'mappedConfidence': parse_result.get('mappedConfidence'),
                    'topUnmappedHeaders': list(parse_result.get('topUnmappedHeaders') or []),
                },
            },
            {
                'gate_name': 'importability',
                'gate_status': self._clean_str((confirm_result.get('batchSnapshot') or {}).get('importabilityStatus') or confirm_result.get('importabilityStatus') or (parse_result.get('batchSnapshot') or {}).get('importabilityStatus'), 'failed'),
                'reason_list': list(confirm_result.get('importabilityReasons') or parse_result.get('importabilityReasons') or []),
                'summary': {
                    'importedRows': self._int_or_zero(confirm_result.get('importedRows')),
                    'quarantineCount': self._int_or_zero(confirm_result.get('quarantineCount')),
                },
            },
        ]
        for item in gates:
            session.add(BatchGateResult(
                batch_id=batch_id,
                gate_name=item['gate_name'],
                gate_status=item['gate_status'],
                reason_list=item['reason_list'],
                summary=item['summary'],
            ))

    def _replace_field_mappings(self, *, session, batch_id: int, payload: Dict[str, Any]) -> None:
        session.execute(delete(BatchFieldMapping).where(BatchFieldMapping.batch_id == batch_id))
        for item in self._normalize_mapping_items(payload):
            session.add(BatchFieldMapping(
                batch_id=batch_id,
                source_header=item['sourceHeader'],
                target_field=item['targetField'],
                confidence=item['confidence'],
                mapping_status=item['mappingStatus'],
                mapping_meta=item['mappingMeta'],
            ))

    def _replace_manual_overrides(
        self,
        *,
        session,
        batch_id: int,
        manual_overrides: List[Dict[str, Any]],
        operator: str,
    ) -> None:
        session.execute(delete(BatchManualOverride).where(BatchManualOverride.batch_id == batch_id))
        for item in manual_overrides or []:
            if not isinstance(item, dict):
                continue
            session.add(BatchManualOverride(
                batch_id=batch_id,
                override_type=self._clean_str(item.get('type') or item.get('overrideType'), 'mapping_override'),
                reason=self._clean_str(item.get('reason')) or None,
                operator=operator or None,
                payload=item,
            ))

    def _replace_audit_event(
        self,
        *,
        session,
        batch_id: int,
        event_type: str,
        event_status: str,
        payload: Dict[str, Any],
    ) -> None:
        session.execute(delete(BatchAuditEvent).where(BatchAuditEvent.batch_id == batch_id, BatchAuditEvent.event_type == event_type))
        session.add(BatchAuditEvent(
            batch_id=batch_id,
            event_type=event_type,
            event_status=event_status or None,
            payload=payload,
        ))


    def _build_phase1_enrichment(
        self,
        *,
        dataset_kind: str,
        import_profile: str,
        parse_result: Dict[str, Any],
        confirm_result: Dict[str, Any] | None = None,
        field_mappings: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        payload = dict(parse_result or {})
        if field_mappings is not None:
            payload['fieldMappings'] = field_mappings
        payload['datasetKind'] = dataset_kind
        payload['importProfile'] = import_profile
        registry_payload = self.registry_service.list_datasets()
        registry_datasets = list(registry_payload.get('datasets') or [])
        profile_candidates = self.profile_scoring_service.score_candidates(
            registry_datasets=registry_datasets,
            parse_result=payload,
            selected_profile=import_profile,
            limit=3,
        )
        business_key_candidates = self.business_key_inference_service.infer_candidates(
            dataset_kind=dataset_kind,
            payload=payload,
            limit=4,
        )
        top_profile_confidence = float((profile_candidates[0].get('confidence') if profile_candidates else 50) or 50) / 100.0
        top_key_viability = float((business_key_candidates[0].get('keyViabilityScore') if business_key_candidates else 0.5) or 0.5)
        importability = self.importability_score_builder.build(
            parse_result=payload,
            confirm_result=confirm_result or {},
            profile_confidence=top_profile_confidence,
            key_viability_score=top_key_viability,
        )
        reason_inputs = list((confirm_result or {}).get('importabilityReasons') or [])
        if not reason_inputs:
            reason_inputs = list(payload.get('semanticGateReasons') or [])
        reason_buckets = self.reason_clustering_service.cluster(reason_inputs)
        return {
            'algorithmVersion': self.ALGORITHM_VERSION,
            'profileCandidates': profile_candidates,
            'businessKeyCandidates': business_key_candidates,
            'importabilityEvaluation': importability,
            'reasonBuckets': reason_buckets,
        }

    @staticmethod
    def _percent_to_int(value: Any) -> int:
        try:
            return int(round(float(value or 0) * 100))
        except (TypeError, ValueError):
            return 0

    def _replace_profile_candidates(self, *, session, batch_id: int, candidates: List[Dict[str, Any]]) -> None:
        session.execute(delete(BatchProfileCandidate).where(BatchProfileCandidate.batch_id == batch_id))
        for item in list(candidates or []):
            session.add(BatchProfileCandidate(
                batch_id=batch_id,
                dataset_kind=self._clean_str(item.get('datasetKind'), 'orders'),
                profile_code=self._clean_str(item.get('profileCode'), 'orders'),
                score=self._percent_to_int(item.get('score')),
                confidence=self._int_or_zero(item.get('confidence')),
                candidate_rank=self._int_or_zero(item.get('rank')) or 1,
                is_selected=bool(item.get('selected') or False),
                auto_bindable=bool(item.get('autoBindable') or False),
                requires_manual_confirm=bool(item.get('requiresManualConfirm') or False),
                reason_payload=dict(item.get('reasonPayload') or {}),
            ))

    def _replace_business_key_candidates(self, *, session, batch_id: int, candidates: List[Dict[str, Any]]) -> None:
        session.execute(delete(BatchBusinessKeyCandidate).where(BatchBusinessKeyCandidate.batch_id == batch_id))
        for item in list(candidates or []):
            session.add(BatchBusinessKeyCandidate(
                batch_id=batch_id,
                strategy_code=self._clean_str(item.get('strategyCode'), 'sku'),
                score=self._percent_to_int(item.get('score')),
                candidate_rank=self._int_or_zero(item.get('rank')) or 1,
                is_selected=bool(item.get('selected') or False),
                unresolved_rows=self._int_or_zero(item.get('unresolvedRows')),
                surrogate_key_rate=self._percent_to_int(item.get('surrogateKeyRate')),
                downstream_risk=self._percent_to_int(item.get('downstreamLoadabilityRisk')),
                reason_payload=dict(item.get('reasonPayload') or {}),
            ))

    def _replace_quarantine_rows(self, *, session, batch_id: int, buckets: List[Dict[str, Any]]) -> None:
        session.execute(delete(BatchQuarantineRow).where(BatchQuarantineRow.batch_id == batch_id))
        for index, item in enumerate(list(buckets or []), start=1):
            session.add(BatchQuarantineRow(
                batch_id=batch_id,
                row_index=None,
                reason_code=self._clean_str(item.get('reasonCode'), 'UNCLASSIFIED'),
                reason_cluster_code=self._clean_str(item.get('reasonClusterCode')) or None,
                is_auto_recoverable=bool(item.get('isAutoRecoverable') or False),
                payload={
                    'rank': index,
                    'count': self._int_or_zero(item.get('count')),
                    'examples': list(item.get('examples') or []),
                },
            ))

    @staticmethod
    def _serialize_profile_candidate(row: BatchProfileCandidate) -> Dict[str, Any]:
        return {
            'datasetKind': row.dataset_kind,
            'profileCode': row.profile_code,
            'score': round((row.score or 0) / 100.0, 4),
            'confidence': row.confidence,
            'rank': row.candidate_rank,
            'selected': bool(row.is_selected),
            'autoBindable': bool(row.auto_bindable),
            'requiresManualConfirm': bool(row.requires_manual_confirm),
            'reasonPayload': row.reason_payload or {},
        }

    @staticmethod
    def _serialize_business_key_candidate(row: BatchBusinessKeyCandidate) -> Dict[str, Any]:
        return {
            'strategyCode': row.strategy_code,
            'score': round((row.score or 0) / 100.0, 4),
            'keyViabilityScore': round((row.score or 0) / 100.0, 4),
            'rank': row.candidate_rank,
            'selected': bool(row.is_selected),
            'unresolvedRows': row.unresolved_rows,
            'surrogateKeyRate': round((row.surrogate_key_rate or 0) / 100.0, 4),
            'downstreamLoadabilityRisk': round((row.downstream_risk or 0) / 100.0, 4),
            'reasonPayload': row.reason_payload or {},
        }

    @staticmethod
    def _serialize_quarantine_bucket(row: BatchQuarantineRow) -> Dict[str, Any]:
        payload = dict(row.payload or {})
        return {
            'reasonCode': row.reason_code,
            'reasonClusterCode': row.reason_cluster_code or row.reason_code,
            'count': BatchService._int_or_zero(payload.get('count')),
            'examples': list(payload.get('examples') or []),
            'isAutoRecoverable': bool(row.is_auto_recoverable),
            'rank': BatchService._int_or_zero(payload.get('rank')),
        }

    def save_parse_result(
        self,
        *,
        session_id: int,
        parse_result: Dict[str, Any],
        shop_id: int,
        operator: str,
        source_mode: str = 'upload',
        workspace_batch_id: str | None = None,
        legacy_import_batch_id: int | None = None,
    ) -> Dict[str, Any]:
        parse_snapshot = dict(parse_result.get('batchSnapshot') or {})
        final_snapshot = dict(parse_snapshot or {})
        dataset_kind = self._clean_str(parse_result.get('datasetKind'), 'orders')
        import_profile = self._clean_str(parse_result.get('importProfile') or dataset_kind, dataset_kind)
        get_engine()
        with get_session() as session:
            batch = self._upsert_batch_core(
                session=session,
                session_id=session_id,
                dataset_kind=dataset_kind,
                import_profile=import_profile,
                source_mode=self._clean_str(source_mode, 'upload'),
                source_name=self._clean_str(parse_result.get('fileName')),
                shop_id=self._int_or_none(shop_id),
                operator=self._clean_str(operator),
                contract_version=self._clean_str(final_snapshot.get('contractVersion'), self.CONTRACT_VERSION),
                batch_status=self._clean_str(final_snapshot.get('batchStatus'), 'uploaded'),
                transport_status=self._clean_str(final_snapshot.get('transportStatus') or parse_result.get('transportStatus'), 'failed'),
                semantic_status=self._clean_str(final_snapshot.get('semanticStatus') or parse_result.get('semanticStatus'), 'failed'),
                importability_status=self._clean_str(final_snapshot.get('importabilityStatus'), 'risk'),
                imported_rows=self._int_or_zero(final_snapshot.get('importedRows')),
                quarantine_count=self._int_or_zero(final_snapshot.get('quarantineCount')),
                raw_parse_meta={
                    'status': parse_result.get('status'),
                    'finalStatus': parse_result.get('finalStatus'),
                    'mappedCount': parse_result.get('mappedCount'),
                    'unmappedCount': parse_result.get('unmappedCount'),
                    'mappingCoverage': parse_result.get('mappingCoverage'),
                    'mappedConfidence': parse_result.get('mappedConfidence'),
                    'selectedSheet': parse_result.get('selectedSheet'),
                    'topUnmappedHeaders': list(parse_result.get('topUnmappedHeaders') or []),
                    'semanticGateReasons': list(parse_result.get('semanticGateReasons') or []),
                    'riskOverrideReasons': list(parse_result.get('riskOverrideReasons') or []),
                },
                raw_confirm_meta={},
                parse_snapshot=parse_snapshot,
                confirm_snapshot={},
                final_snapshot=final_snapshot,
                workspace_batch_id=workspace_batch_id,
                legacy_import_batch_id=legacy_import_batch_id,
            )
            self._upsert_source_object(
                session=session,
                batch_id=batch.id,
                source_mode=self._clean_str(source_mode, 'upload'),
                file_name=self._clean_str(parse_result.get('fileName')),
                file_path=self._clean_str(parse_result.get('filePath')) or None,
                file_size=self._int_or_none(parse_result.get('fileSize')),
                selected_sheet=self._clean_str(parse_result.get('selectedSheet')) or None,
            )
            self._replace_field_mappings(session=session, batch_id=batch.id, payload=parse_result)
            self._replace_gate_results(session=session, batch_id=batch.id, parse_result=parse_result, confirm_result=None)
            self._replace_audit_event(
                session=session,
                batch_id=batch.id,
                event_type='parse',
                event_status=self._clean_str(parse_result.get('status'), 'partial'),
                payload={
                    'eventType': 'parse',
                    'at': self._now_iso(),
                    'status': parse_result.get('status'),
                    'finalStatus': parse_result.get('finalStatus'),
                    'batchStatus': final_snapshot.get('batchStatus'),
                    'transportStatus': final_snapshot.get('transportStatus') or parse_result.get('transportStatus'),
                    'semanticStatus': final_snapshot.get('semanticStatus') or parse_result.get('semanticStatus'),
                    'importabilityStatus': final_snapshot.get('importabilityStatus'),
                    'mappedCount': parse_result.get('mappedCount'),
                    'unmappedCount': parse_result.get('unmappedCount'),
                    'mappingCoverage': parse_result.get('mappingCoverage'),
                    'mappedConfidence': parse_result.get('mappedConfidence'),
                },
            )
            phase1 = self._build_phase1_enrichment(
                dataset_kind=dataset_kind,
                import_profile=import_profile,
                parse_result=parse_result,
                confirm_result=None,
                field_mappings=list(parse_result.get('fieldMappings') or []),
            )
            self._replace_profile_candidates(session=session, batch_id=batch.id, candidates=phase1.get('profileCandidates') or [])
            self._replace_business_key_candidates(session=session, batch_id=batch.id, candidates=phase1.get('businessKeyCandidates') or [])
            self._replace_quarantine_rows(session=session, batch_id=batch.id, buckets=phase1.get('reasonBuckets') or [])
            batch.raw_parse_meta = {**(batch.raw_parse_meta or {}), **phase1}
            session.flush()
            batch_id = batch.id
        return self.get_batch_detail(str(batch_id)) or {}

    def save_confirm_result(
        self,
        *,
        session_id: int,
        parse_result: Dict[str, Any],
        confirm_result: Dict[str, Any],
        shop_id: int,
        operator: str,
        manual_overrides: List[Dict[str, Any]] | None = None,
        workspace_batch_id: str | None = None,
        legacy_import_batch_id: int | None = None,
    ) -> Dict[str, Any]:
        parse_snapshot = dict(parse_result.get('batchSnapshot') or {})
        confirm_snapshot = dict(confirm_result.get('batchSnapshot') or {})
        final_snapshot = dict(confirm_snapshot or parse_snapshot)
        dataset_kind = self._clean_str(confirm_result.get('datasetKind') or parse_result.get('datasetKind'), 'orders')
        import_profile = self._clean_str(confirm_result.get('importProfile') or parse_result.get('importProfile') or dataset_kind, dataset_kind)
        get_engine()
        with get_session() as session:
            batch = self._upsert_batch_core(
                session=session,
                session_id=session_id,
                dataset_kind=dataset_kind,
                import_profile=import_profile,
                source_mode=self._clean_str(parse_result.get('sourceMode'), 'upload'),
                source_name=self._clean_str(parse_result.get('fileName')),
                shop_id=self._int_or_none(shop_id),
                operator=self._clean_str(operator),
                contract_version=self._clean_str(final_snapshot.get('contractVersion'), self.CONTRACT_VERSION),
                batch_status=self._clean_str(final_snapshot.get('batchStatus') or confirm_result.get('batchStatus'), 'failed'),
                transport_status=self._clean_str(final_snapshot.get('transportStatus') or confirm_result.get('transportStatus') or parse_result.get('transportStatus'), 'failed'),
                semantic_status=self._clean_str(final_snapshot.get('semanticStatus') or confirm_result.get('semanticStatus') or parse_result.get('semanticStatus'), 'failed'),
                importability_status=self._clean_str(final_snapshot.get('importabilityStatus') or confirm_result.get('importabilityStatus'), 'failed'),
                imported_rows=self._int_or_zero(confirm_result.get('importedRows')),
                quarantine_count=self._int_or_zero(confirm_result.get('quarantineCount')),
                raw_parse_meta={
                    'status': parse_result.get('status'),
                    'finalStatus': parse_result.get('finalStatus'),
                    'mappedCount': parse_result.get('mappedCount'),
                    'unmappedCount': parse_result.get('unmappedCount'),
                    'mappingCoverage': parse_result.get('mappingCoverage'),
                    'mappedConfidence': parse_result.get('mappedConfidence'),
                    'selectedSheet': parse_result.get('selectedSheet'),
                    'topUnmappedHeaders': list(parse_result.get('topUnmappedHeaders') or []),
                    'semanticGateReasons': list(parse_result.get('semanticGateReasons') or []),
                    'riskOverrideReasons': list(parse_result.get('riskOverrideReasons') or []),
                },
                raw_confirm_meta={
                    'status': confirm_result.get('status'),
                    'success': confirm_result.get('success'),
                    'importedRows': confirm_result.get('importedRows'),
                    'errorRows': confirm_result.get('errorRows'),
                    'quarantineCount': confirm_result.get('quarantineCount'),
                    'factLoadErrors': confirm_result.get('factLoadErrors'),
                    'errors': list(confirm_result.get('errors') or []),
                    'warnings': list(confirm_result.get('warnings') or []),
                    'importabilityReasons': list(confirm_result.get('importabilityReasons') or []),
                    'runtimeAudit': dict(confirm_result.get('runtimeAudit') or {}),
                },
                parse_snapshot=parse_snapshot,
                confirm_snapshot=confirm_snapshot,
                final_snapshot=final_snapshot,
                workspace_batch_id=workspace_batch_id,
                legacy_import_batch_id=legacy_import_batch_id,
            )
            self._upsert_source_object(
                session=session,
                batch_id=batch.id,
                source_mode=self._clean_str(parse_result.get('sourceMode'), 'upload'),
                file_name=self._clean_str(parse_result.get('fileName')),
                file_path=self._clean_str(parse_result.get('filePath')) or None,
                file_size=self._int_or_none(parse_result.get('fileSize')),
                selected_sheet=self._clean_str(parse_result.get('selectedSheet')) or None,
            )
            mapping_payload = dict(parse_result)
            if confirm_result.get('fieldMappings'):
                mapping_payload['fieldMappings'] = confirm_result.get('fieldMappings')
            self._replace_field_mappings(session=session, batch_id=batch.id, payload=mapping_payload)
            self._replace_gate_results(session=session, batch_id=batch.id, parse_result=parse_result, confirm_result=confirm_result)
            self._replace_manual_overrides(
                session=session,
                batch_id=batch.id,
                manual_overrides=list(manual_overrides or []),
                operator=self._clean_str(operator),
            )
            self._replace_audit_event(
                session=session,
                batch_id=batch.id,
                event_type='confirm',
                event_status=self._clean_str(confirm_result.get('status'), 'success'),
                payload={
                    'eventType': 'confirm',
                    'at': self._now_iso(),
                    'status': confirm_result.get('status'),
                    'batchStatus': final_snapshot.get('batchStatus') or confirm_result.get('batchStatus'),
                    'transportStatus': final_snapshot.get('transportStatus') or confirm_result.get('transportStatus'),
                    'semanticStatus': final_snapshot.get('semanticStatus') or confirm_result.get('semanticStatus'),
                    'importabilityStatus': final_snapshot.get('importabilityStatus') or confirm_result.get('importabilityStatus'),
                    'importedRows': confirm_result.get('importedRows'),
                    'quarantineCount': confirm_result.get('quarantineCount'),
                    'errorRows': confirm_result.get('errorRows'),
                    'importabilityReasons': list(confirm_result.get('importabilityReasons') or []),
                    'manualOverrideCount': len(list(manual_overrides or [])),
                },
            )
            phase1 = self._build_phase1_enrichment(
                dataset_kind=dataset_kind,
                import_profile=import_profile,
                parse_result=mapping_payload,
                confirm_result=confirm_result,
                field_mappings=list(mapping_payload.get('fieldMappings') or []),
            )
            self._replace_profile_candidates(session=session, batch_id=batch.id, candidates=phase1.get('profileCandidates') or [])
            self._replace_business_key_candidates(session=session, batch_id=batch.id, candidates=phase1.get('businessKeyCandidates') or [])
            self._replace_quarantine_rows(session=session, batch_id=batch.id, buckets=phase1.get('reasonBuckets') or [])
            batch.raw_parse_meta = {**(batch.raw_parse_meta or {}), **{k: v for k, v in phase1.items() if k != 'importabilityEvaluation'}}
            batch.raw_confirm_meta = {**(batch.raw_confirm_meta or {}), **phase1}
            session.flush()
            batch_id = batch.id
        return self.get_batch_detail(str(batch_id)) or {}

    def sync_registry_from_yaml(self) -> Dict[str, int]:
        registry = self.registry_service.list_datasets()
        datasets = registry.get('datasets') or []
        seeded = {'datasets': 0, 'profiles': 0, 'fields': 0, 'policies': 0}
        get_engine()
        with get_session() as session:
            for item in datasets:
                dataset = session.execute(
                    select(RegistryDataset).where(RegistryDataset.dataset_kind == str(item.get('datasetKind') or ''))
                ).scalar_one_or_none()
                if dataset is None:
                    dataset = RegistryDataset(
                        dataset_kind=str(item.get('datasetKind') or ''),
                        import_profile=str(item.get('importProfile') or item.get('datasetKind') or ''),
                        label=str(item.get('label') or item.get('datasetKind') or ''),
                        source_type=str(item.get('sourceType') or 'file'),
                        platform=str(item.get('platform') or 'generic'),
                        grain=str(item.get('grain') or ''),
                        loader_target=str(item.get('loaderTarget') or ''),
                        gate_policy=str(item.get('gatePolicy') or 'core_safe'),
                        schema_version=str(item.get('schemaVersion') or 'v1'),
                        entity_key_field=str(item.get('entityKeyField') or 'sku'),
                        is_active=True,
                    )
                    session.add(dataset)
                    session.flush()
                    seeded['datasets'] += 1
                else:
                    dataset.import_profile = str(item.get('importProfile') or dataset.import_profile)
                    dataset.label = str(item.get('label') or dataset.label)
                    dataset.source_type = str(item.get('sourceType') or dataset.source_type)
                    dataset.platform = str(item.get('platform') or dataset.platform)
                    dataset.grain = str(item.get('grain') or dataset.grain or '')
                    dataset.loader_target = str(item.get('loaderTarget') or dataset.loader_target or '')
                    dataset.gate_policy = str(item.get('gatePolicy') or dataset.gate_policy)
                    dataset.schema_version = str(item.get('schemaVersion') or dataset.schema_version)
                    dataset.entity_key_field = str(item.get('entityKeyField') or dataset.entity_key_field)
                    dataset.is_active = True

                profile = session.execute(
                    select(RegistryProfile).where(RegistryProfile.dataset_id == dataset.id, RegistryProfile.profile_code == dataset.import_profile)
                ).scalar_one_or_none()
                if profile is None:
                    session.add(RegistryProfile(
                        dataset_id=dataset.id,
                        profile_code=dataset.import_profile,
                        label=dataset.label,
                        platform=dataset.platform,
                        source_type=dataset.source_type,
                        is_active=True,
                    ))
                    seeded['profiles'] += 1

                existing_fields = {
                    row.field_name: row
                    for row in session.execute(select(RegistryField).where(RegistryField.dataset_id == dataset.id)).scalars().all()
                }
                for field_name in item.get('requiredCoreFields') or []:
                    if field_name not in existing_fields:
                        session.add(RegistryField(dataset_id=dataset.id, field_name=str(field_name), field_role='required_core', is_required=True))
                        seeded['fields'] += 1
                for field_name in item.get('optionalCommonFields') or []:
                    if field_name not in existing_fields:
                        session.add(RegistryField(dataset_id=dataset.id, field_name=str(field_name), field_role='optional_common', is_required=False))
                        seeded['fields'] += 1

                policy = session.execute(
                    select(RegistryGatePolicy).where(RegistryGatePolicy.policy_code == dataset.gate_policy)
                ).scalar_one_or_none()
                if policy is None:
                    session.add(RegistryGatePolicy(
                        policy_code=dataset.gate_policy,
                        label=dataset.gate_policy,
                        transport_rule={'status': 'required'},
                        semantic_rule={'status': 'required'},
                        importability_rule={'status': 'required'},
                    ))
                    seeded['policies'] += 1
        return seeded

    def list_registry_datasets(self) -> Dict[str, Any]:
        get_engine()
        with get_session() as session:
            rows = session.execute(select(RegistryDataset).order_by(RegistryDataset.id.asc())).scalars().all()
            if not rows:
                return {'contractVersion': self.CONTRACT_VERSION, 'datasets': []}
            datasets = []
            for row in rows:
                field_rows = session.execute(select(RegistryField).where(RegistryField.dataset_id == row.id)).scalars().all()
                datasets.append({
                    'datasetKind': row.dataset_kind,
                    'importProfile': row.import_profile,
                    'label': row.label,
                    'sourceType': row.source_type,
                    'platform': row.platform,
                    'grain': row.grain or '',
                    'requiredCoreFields': [f.field_name for f in field_rows if f.field_role == 'required_core'],
                    'optionalCommonFields': [f.field_name for f in field_rows if f.field_role == 'optional_common'],
                    'loaderTarget': row.loader_target or '',
                    'gatePolicy': row.gate_policy,
                    'schemaVersion': row.schema_version,
                    'entityKeyField': row.entity_key_field,
                })
            return {'contractVersion': self.CONTRACT_VERSION, 'datasets': datasets}

    def _ensure_ingest_batch_backfill(self, limit: int = 100) -> int:
        workspace_items = (self.workspace_service.list_batches(limit=max(limit, 1)).get('items') or [])[:limit]
        get_engine()
        created = 0

        def _legacy_status_to_gate(status: str) -> tuple[str, str, str]:
            normalized = self._clean_str(status, 'failed').lower()
            if normalized in {'imported', 'completed', 'success', 'done'}:
                return 'imported', 'passed', 'passed'
            if normalized in {'mapped', 'validated', 'partial', 'partially_imported'}:
                return 'validated', 'passed', 'risk'
            return 'failed', 'failed', 'failed'

        def _build_placeholder_mappings(mapped_summary: Dict[str, Any], unmapped_headers: List[Any]) -> List[Dict[str, Any]]:
            mapped_fields = list(mapped_summary.get('mappedCanonicalFields') or [])
            items: List[Dict[str, Any]] = []
            for idx, field_name in enumerate(mapped_fields, start=1):
                field_text = self._clean_str(field_name)
                if not field_text:
                    continue
                items.append({
                    'sourceHeader': f'legacy_{idx}_{field_text}',
                    'sourceHeaderDisplay': field_text,
                    'sourceColumnIndex': idx,
                    'targetField': field_text,
                    'confidence': self._int_or_zero(mapped_summary.get('mappedConfidence') or 90),
                    'mappingStatus': 'mapped',
                    'mappingMeta': {
                        'sourceHeaderDisplay': field_text,
                        'sourceHeaderOrdinal': 1,
                        'sourceHeaderDuplicateCount': 1,
                        'sourceColumnIndex': idx,
                        'isLegacyBackfill': True,
                    },
                })
            base_index = len(items)
            for offset, header in enumerate(list(unmapped_headers or []), start=1):
                header_text = self._clean_str(header)
                if not header_text:
                    continue
                items.append({
                    'sourceHeader': f'legacy_unmapped_{base_index + offset}',
                    'sourceHeaderDisplay': header_text,
                    'sourceColumnIndex': base_index + offset,
                    'targetField': None,
                    'confidence': None,
                    'mappingStatus': 'unmapped',
                    'mappingMeta': {
                        'sourceHeaderDisplay': header_text,
                        'sourceHeaderOrdinal': 1,
                        'sourceHeaderDuplicateCount': 1,
                        'sourceColumnIndex': base_index + offset,
                        'isLegacyBackfill': True,
                    },
                })
            return items

        with get_session() as session:
            if workspace_items:
                for item in workspace_items:
                    workspace_batch_id = str(item.get('workspaceBatchId') or '').strip()
                    if not workspace_batch_id:
                        continue
                    existing = session.execute(
                        select(IngestBatch).where(IngestBatch.workspace_batch_id == workspace_batch_id)
                    ).scalar_one_or_none()
                    if existing is not None:
                        continue
                    detail = self.workspace_service.get_batch_by_workspace_id(workspace_batch_id) or {}
                    final_snapshot = detail.get('finalSnapshot') or detail.get('confirmSnapshot') or detail.get('parseSnapshot') or {}
                    batch = IngestBatch(
                        workspace_batch_id=workspace_batch_id,
                        legacy_session_id=int(detail.get('sessionId') or 0) or None,
                        legacy_import_batch_id=int(detail.get('dbBatchId') or 0) or None,
                        dataset_kind=str(detail.get('datasetKind') or 'orders'),
                        import_profile=str(detail.get('importProfile') or detail.get('datasetKind') or 'orders'),
                        source_mode=str(detail.get('sourceMode') or 'upload'),
                        source_name=str(detail.get('fileName') or ''),
                        platform=None,
                        shop_id=int(detail.get('shopId') or 0) or None,
                        operator=str(detail.get('operator') or ''),
                        contract_version=str(final_snapshot.get('contractVersion') or self.CONTRACT_VERSION),
                        batch_status=str(final_snapshot.get('batchStatus') or detail.get('batchStatus') or 'uploaded'),
                        transport_status=str(final_snapshot.get('transportStatus') or detail.get('transportStatus') or 'failed'),
                        semantic_status=str(final_snapshot.get('semanticStatus') or detail.get('semanticStatus') or 'failed'),
                        importability_status=str(final_snapshot.get('importabilityStatus') or detail.get('importabilityStatus') or 'failed'),
                        imported_rows=int(final_snapshot.get('importedRows') or detail.get('importedRows') or 0),
                        quarantine_count=int(final_snapshot.get('quarantineCount') or detail.get('quarantineCount') or 0),
                        raw_parse_meta=detail.get('parseResultMeta') or {},
                        raw_confirm_meta=detail.get('confirmResultMeta') or {},
                        parse_snapshot=detail.get('parseSnapshot') or {},
                        confirm_snapshot=detail.get('confirmSnapshot') or {},
                        final_snapshot=final_snapshot or {},
                    )
                    session.add(batch)
                    session.flush()
                    session.add(IngestSourceObject(
                        batch_id=batch.id,
                        object_type='file',
                        file_name=str(detail.get('fileName') or ''),
                        file_path='',
                        file_size=None,
                        content_meta={'sourceMode': detail.get('sourceMode')},
                    ))
                    for gate_name, gate_status, reasons in [
                        ('transport', batch.transport_status, []),
                        ('semantic', batch.semantic_status, list((detail.get('parseResultMeta') or {}).get('semanticGateReasons') or [])),
                        ('importability', batch.importability_status, list((detail.get('confirmResultMeta') or {}).get('importabilityReasons') or [])),
                    ]:
                        session.add(BatchGateResult(
                            batch_id=batch.id,
                            gate_name=gate_name,
                            gate_status=gate_status,
                            reason_list=reasons,
                            summary={},
                        ))
                    for event in detail.get('eventTimeline') or []:
                        session.add(BatchAuditEvent(
                            batch_id=batch.id,
                            event_type=str(event.get('eventType') or 'event'),
                            event_status=str(event.get('status') or event.get('batchStatus') or ''),
                            payload=event,
                        ))
                    created += 1

            from ecom_v51.db.models import ImportBatch, ImportBatchFile

            legacy_rows = session.execute(
                select(ImportBatch).order_by(ImportBatch.id.desc()).limit(max(limit, 1))
            ).scalars().all()
            for legacy in legacy_rows:
                if session.execute(
                    select(IngestBatch).where(IngestBatch.legacy_import_batch_id == legacy.id)
                ).scalar_one_or_none() is not None:
                    continue

                batch_file = session.execute(
                    select(ImportBatchFile).where(ImportBatchFile.batch_id == legacy.id).order_by(ImportBatchFile.id.desc())
                ).scalars().first()

                mapped_summary: Dict[str, Any] = {}
                unmapped_headers: List[Any] = []
                selected_sheet = None
                file_name = None
                if batch_file is not None:
                    if isinstance(batch_file.mapped_fields_json, dict):
                        mapped_summary = dict(batch_file.mapped_fields_json)
                    unmapped_headers = list(batch_file.unmapped_fields_json or [])
                    selected_sheet = batch_file.sheet_name
                    file_name = batch_file.file_name

                dataset_kind = 'orders'
                import_profile = 'orders'
                platform = self._clean_str(getattr(legacy, 'platform_code', ''), 'generic')
                if platform == 'ozon':
                    import_profile = 'ozon_orders_report'
                batch_status, transport_status, semantic_status = _legacy_status_to_gate(getattr(legacy, 'status', 'failed'))
                importability_status = 'passed' if self._int_or_zero(getattr(legacy, 'success_count', 0)) > 0 else ('risk' if self._int_or_zero(getattr(legacy, 'error_count', 0)) > 0 else 'failed')

                parse_snapshot = {
                    'contractVersion': self.CONTRACT_VERSION,
                    'datasetKind': dataset_kind,
                    'batchStatus': 'validated' if batch_status != 'failed' else 'failed',
                    'transportStatus': transport_status,
                    'semanticStatus': semantic_status,
                    'importabilityStatus': 'risk' if batch_status != 'failed' else 'failed',
                    'quarantineCount': self._int_or_zero(getattr(legacy, 'error_count', 0)),
                    'importedRows': 0,
                    'mappingSummary': mapped_summary,
                }
                confirm_snapshot = {
                    'contractVersion': self.CONTRACT_VERSION,
                    'datasetKind': dataset_kind,
                    'batchStatus': batch_status,
                    'transportStatus': transport_status,
                    'semanticStatus': semantic_status,
                    'importabilityStatus': importability_status,
                    'quarantineCount': self._int_or_zero(getattr(legacy, 'error_count', 0)),
                    'importedRows': self._int_or_zero(getattr(legacy, 'success_count', 0)),
                    'mappingSummary': mapped_summary,
                }
                placeholder_mappings = _build_placeholder_mappings(mapped_summary, unmapped_headers)
                parse_meta = {
                    'status': batch_status,
                    'finalStatus': semantic_status,
                    'mappedCount': self._int_or_zero(mapped_summary.get('mappedCount') or len(mapped_summary.get('mappedCanonicalFields') or [])),
                    'unmappedCount': self._int_or_zero(mapped_summary.get('unmappedCount') or len(unmapped_headers)),
                    'mappingCoverage': mapped_summary.get('mappingCoverage'),
                    'mappedConfidence': mapped_summary.get('mappedConfidence'),
                    'selectedSheet': selected_sheet,
                    'topUnmappedHeaders': unmapped_headers,
                    'semanticGateReasons': [],
                    'riskOverrideReasons': [],
                }
                confirm_reasons = []
                if self._int_or_zero(getattr(legacy, 'error_count', 0)) > 0:
                    confirm_reasons.append('LEGACY_IMPORT_ERRORS')
                confirm_meta = {
                    'status': 'success' if batch_status != 'failed' else 'failed',
                    'success': batch_status != 'failed',
                    'importedRows': self._int_or_zero(getattr(legacy, 'success_count', 0)),
                    'errorRows': self._int_or_zero(getattr(legacy, 'error_count', 0)),
                    'quarantineCount': self._int_or_zero(getattr(legacy, 'error_count', 0)),
                    'factLoadErrors': self._int_or_zero(getattr(legacy, 'error_count', 0)),
                    'errors': [],
                    'warnings': [],
                    'importabilityReasons': confirm_reasons,
                    'runtimeAudit': {'legacyBackfill': True},
                }

                batch = IngestBatch(
                    workspace_batch_id=None,
                    legacy_session_id=None,
                    legacy_import_batch_id=legacy.id,
                    dataset_kind=dataset_kind,
                    import_profile=import_profile,
                    source_mode='legacy_db',
                    source_name=str(file_name or f'legacy-import-batch-{legacy.id}'),
                    platform=platform,
                    shop_id=getattr(legacy, 'shop_id', None),
                    operator='legacy_backfill',
                    contract_version=self.CONTRACT_VERSION,
                    batch_status=batch_status,
                    transport_status=transport_status,
                    semantic_status=semantic_status,
                    importability_status=importability_status,
                    imported_rows=self._int_or_zero(getattr(legacy, 'success_count', 0)),
                    quarantine_count=self._int_or_zero(getattr(legacy, 'error_count', 0)),
                    raw_parse_meta=parse_meta,
                    raw_confirm_meta=confirm_meta,
                    parse_snapshot=parse_snapshot,
                    confirm_snapshot=confirm_snapshot,
                    final_snapshot=confirm_snapshot,
                )
                session.add(batch)
                session.flush()

                session.add(IngestSourceObject(
                    batch_id=batch.id,
                    object_type='file',
                    file_name=str(file_name or f'legacy-import-batch-{legacy.id}.csv'),
                    file_path='',
                    file_size=None,
                    content_meta={'sourceMode': 'legacy_db', 'selectedSheet': selected_sheet or ''},
                ))

                for mapping_item in placeholder_mappings:
                    session.add(BatchFieldMapping(
                        batch_id=batch.id,
                        source_header=str(mapping_item.get('sourceHeader') or ''),
                        target_field=mapping_item.get('targetField'),
                        confidence=self._int_or_none(mapping_item.get('confidence')),
                        mapping_status=str(mapping_item.get('mappingStatus') or 'mapped'),
                        mapping_meta=dict(mapping_item.get('mappingMeta') or {}),
                    ))

                phase1 = self._build_phase1_enrichment(
                    dataset_kind=dataset_kind,
                    import_profile=import_profile,
                    parse_result={
                        **parse_meta,
                        'datasetKind': dataset_kind,
                        'importProfile': import_profile,
                        'fieldMappings': placeholder_mappings,
                        'batchSnapshot': parse_snapshot,
                    },
                    confirm_result={**confirm_meta, 'batchSnapshot': confirm_snapshot},
                    field_mappings=placeholder_mappings,
                )
                self._replace_profile_candidates(session=session, batch_id=batch.id, candidates=phase1.get('profileCandidates') or [])
                self._replace_business_key_candidates(session=session, batch_id=batch.id, candidates=phase1.get('businessKeyCandidates') or [])
                buckets = list(phase1.get('reasonBuckets') or [])
                if not buckets and self._int_or_zero(getattr(legacy, 'error_count', 0)) > 0:
                    buckets = [{
                        'reasonCode': 'LEGACY_IMPORT_ERRORS',
                        'reasonClusterCode': 'LEGACY_IMPORT_ERRORS',
                        'count': self._int_or_zero(getattr(legacy, 'error_count', 0)),
                        'examples': [self._clean_str(getattr(legacy, 'message', ''), 'legacy import batch backfill')],
                        'isAutoRecoverable': False,
                    }]
                self._replace_quarantine_rows(session=session, batch_id=batch.id, buckets=buckets)
                batch.raw_parse_meta = {**(batch.raw_parse_meta or {}), **{k: v for k, v in phase1.items() if k != 'importabilityEvaluation'}}
                batch.raw_confirm_meta = {**(batch.raw_confirm_meta or {}), **phase1}

                session.add(BatchAuditEvent(
                    batch_id=batch.id,
                    event_type='legacy_backfill',
                    event_status=batch_status,
                    payload={
                        'eventType': 'legacy_backfill',
                        'status': batch_status,
                        'batchStatus': batch_status,
                        'transportStatus': transport_status,
                        'semanticStatus': semantic_status,
                        'importabilityStatus': importability_status,
                        'importedRows': self._int_or_zero(getattr(legacy, 'success_count', 0)),
                        'quarantineCount': self._int_or_zero(getattr(legacy, 'error_count', 0)),
                    },
                ))
                created += 1

        return created

    @staticmethod
    def _summary_from_ingest_batch(batch: IngestBatch) -> Dict[str, Any]:
        snapshot = batch.final_snapshot or batch.confirm_snapshot or batch.parse_snapshot or {}
        return {
            'batchId': batch.id,
            'workspaceBatchId': batch.workspace_batch_id,
            'sessionId': batch.legacy_session_id,
            'legacyImportBatchId': batch.legacy_import_batch_id,
            'datasetKind': batch.dataset_kind,
            'importProfile': batch.import_profile,
            'sourceMode': batch.source_mode,
            'fileName': batch.source_name,
            'shopId': batch.shop_id,
            'operator': batch.operator,
            'createdAt': batch.created_at.isoformat() if batch.created_at else None,
            'updatedAt': batch.updated_at.isoformat() if batch.updated_at else None,
            'batchStatus': batch.batch_status,
            'transportStatus': batch.transport_status,
            'semanticStatus': batch.semantic_status,
            'importabilityStatus': batch.importability_status,
            'importedRows': batch.imported_rows,
            'quarantineCount': batch.quarantine_count,
            'contractVersion': batch.contract_version or BatchService.CONTRACT_VERSION,
        }

    @staticmethod
    def _serialize_field_mapping(row: BatchFieldMapping) -> Dict[str, Any]:
        meta = dict(row.mapping_meta or {})
        display_header = str(meta.get('sourceHeaderDisplay') or row.source_header)
        duplicate_total = BatchService._int_or_zero(meta.get('sourceHeaderDuplicateCount'))
        duplicate_ordinal = BatchService._int_or_zero(meta.get('sourceHeaderOrdinal'))
        payload = {
            'mappingId': row.id,
            'sourceHeader': display_header,
            'sourceHeaderKey': row.source_header,
            'sourceColumnIndex': BatchService._int_or_none(meta.get('sourceColumnIndex')),
            'sourceHeaderOrdinal': duplicate_ordinal or None,
            'sourceHeaderDuplicateCount': duplicate_total or None,
            'targetField': row.target_field,
            'confidence': row.confidence,
            'mappingStatus': row.mapping_status,
            'mappingMeta': meta,
            'isDuplicateHeader': duplicate_total > 1,
            'duplicateLabel': f"第{duplicate_ordinal}列" if duplicate_total > 1 and duplicate_ordinal else None,
        }
        return payload

    @staticmethod
    def _serialize_manual_override(row: BatchManualOverride) -> Dict[str, Any]:
        return {
            'overrideId': row.id,
            'overrideType': row.override_type,
            'reason': row.reason,
            'operator': row.operator,
            'payload': row.payload or {},
            'createdAt': row.created_at.isoformat() if row.created_at else None,
        }

    @staticmethod
    def _is_empty_mapping_summary(summary: Dict[str, Any] | None) -> bool:
        summary = dict(summary or {})
        if not summary:
            return True
        return (
            BatchService._int_or_zero(summary.get('mappedCount')) == 0
            and BatchService._int_or_zero(summary.get('unmappedCount')) == 0
            and float(summary.get('mappingCoverage') or 0.0) == 0.0
            and float(summary.get('mappedConfidence') or 0.0) == 0.0
            and not list(summary.get('mappedCanonicalFields') or [])
            and not list(summary.get('topUnmappedHeaders') or [])
        )

    @classmethod
    def _normalize_snapshot(
        cls,
        snapshot: Dict[str, Any] | None,
        *,
        contract_version: str,
        fallback_mapping_summary: Dict[str, Any] | None = None,
    ) -> Dict[str, Any] | None:
        if not snapshot:
            return None
        payload = dict(snapshot)
        payload['contractVersion'] = contract_version or cls.CONTRACT_VERSION
        if fallback_mapping_summary and cls._is_empty_mapping_summary(payload.get('mappingSummary')):
            payload['mappingSummary'] = dict(fallback_mapping_summary)
        return payload

    def list_recent_batches(
        self,
        limit: int = 20,
        *,
        shop_id: int | None = None,
        dataset_kind: str | None = None,
        status: str | None = None,
    ) -> Dict[str, Any]:
        self._ensure_ingest_batch_backfill(limit=max(limit, 20))
        get_engine()
        with get_session() as session:
            stmt = select(IngestBatch)
            if shop_id not in (None, ''):
                stmt = stmt.where(IngestBatch.shop_id == self._int_or_zero(shop_id))
            if dataset_kind:
                stmt = stmt.where(IngestBatch.dataset_kind == str(dataset_kind).strip())
            if status:
                stmt = stmt.where(IngestBatch.batch_status == str(status).strip())
            rows = session.execute(
                stmt.order_by(IngestBatch.updated_at.desc(), IngestBatch.id.desc()).limit(max(limit, 1))
            ).scalars().all()
            if rows:
                items = [self._summary_from_ingest_batch(row) for row in rows]
                return {
                    'contractVersion': self.CONTRACT_VERSION,
                    'source': 'ingest_batch',
                    'items': items,
                    'total': len(items),
                }
        return self.workspace_service.list_batches(limit=limit)

    def _resolve_batch(self, batch_ref: str) -> Optional[IngestBatch]:
        batch_ref = str(batch_ref or '').strip()
        if not batch_ref:
            return None
        self._ensure_ingest_batch_backfill(limit=100)
        get_engine()
        with get_session() as session:
            batch = None
            if batch_ref.isdigit():
                numeric_ref = int(batch_ref)
                batch = session.get(IngestBatch, numeric_ref)
                if batch is not None:
                    return batch
                batch = session.execute(select(IngestBatch).where(IngestBatch.legacy_session_id == numeric_ref)).scalar_one_or_none()
                if batch is not None:
                    return batch
                batch = session.execute(select(IngestBatch).where(IngestBatch.legacy_import_batch_id == numeric_ref)).scalar_one_or_none()
                if batch is not None:
                    return batch
            batch = session.execute(select(IngestBatch).where(IngestBatch.workspace_batch_id == batch_ref)).scalar_one_or_none()
            return batch

    def get_batch_detail(self, batch_ref: str) -> Optional[Dict[str, Any]]:
        batch = self._resolve_batch(batch_ref)
        if batch is None:
            return None
        table_names = self._available_table_names()
        get_engine()
        with get_session() as session:
            gate_rows = session.execute(select(BatchGateResult).where(BatchGateResult.batch_id == batch.id).order_by(BatchGateResult.id.asc())).scalars().all() if 'batch_gate_result' in table_names else []
            source_rows = session.execute(select(IngestSourceObject).where(IngestSourceObject.batch_id == batch.id).order_by(IngestSourceObject.id.asc())).scalars().all() if 'ingest_source_object' in table_names else []
            mapping_rows = session.execute(select(BatchFieldMapping).where(BatchFieldMapping.batch_id == batch.id).order_by(BatchFieldMapping.id.asc())).scalars().all() if 'batch_field_mapping' in table_names else []
            override_rows = session.execute(select(BatchManualOverride).where(BatchManualOverride.batch_id == batch.id).order_by(BatchManualOverride.id.asc())).scalars().all() if 'batch_manual_override' in table_names else []
            profile_rows = session.execute(select(BatchProfileCandidate).where(BatchProfileCandidate.batch_id == batch.id).order_by(BatchProfileCandidate.candidate_rank.asc(), BatchProfileCandidate.id.asc())).scalars().all() if 'batch_profile_candidate' in table_names else []
            key_rows = session.execute(select(BatchBusinessKeyCandidate).where(BatchBusinessKeyCandidate.batch_id == batch.id).order_by(BatchBusinessKeyCandidate.candidate_rank.asc(), BatchBusinessKeyCandidate.id.asc())).scalars().all() if 'batch_business_key_candidate' in table_names else []
            quarantine_rows = session.execute(select(BatchQuarantineRow).where(BatchQuarantineRow.batch_id == batch.id).order_by(BatchQuarantineRow.id.asc())).scalars().all() if 'batch_quarantine_row' in table_names else []
            raw_rows = session.execute(select(RawRecord).where(RawRecord.batch_id == batch.id).order_by(RawRecord.raw_stage.asc(), RawRecord.record_index.asc(), RawRecord.id.asc())).scalars().all() if 'raw_record' in table_names else []
            timeline = [row.payload for row in session.execute(select(BatchAuditEvent).where(BatchAuditEvent.batch_id == batch.id).order_by(BatchAuditEvent.id.asc())).scalars().all()] if 'batch_audit_event' in table_names else []
            contract_version = batch.contract_version or BatchService.CONTRACT_VERSION
            parse_snapshot = self._normalize_snapshot(batch.parse_snapshot, contract_version=contract_version)
            confirm_snapshot = self._normalize_snapshot(batch.confirm_snapshot, contract_version=contract_version, fallback_mapping_summary=(parse_snapshot or {}).get('mappingSummary'))
            final_snapshot = self._normalize_snapshot(batch.final_snapshot, contract_version=contract_version, fallback_mapping_summary=(confirm_snapshot or parse_snapshot or {}).get('mappingSummary'))
            serialized_mappings = [self._serialize_field_mapping(row) for row in mapping_rows]
            parse_meta = batch.raw_parse_meta or {}
            confirm_meta = batch.raw_confirm_meta or {}
            fallback_phase1 = self._build_phase1_enrichment(
                dataset_kind=batch.dataset_kind,
                import_profile=batch.import_profile,
                parse_result={**parse_meta, 'fieldMappings': serialized_mappings, 'datasetKind': batch.dataset_kind, 'importProfile': batch.import_profile, 'batchSnapshot': parse_snapshot or {}},
                confirm_result={**confirm_meta, 'batchSnapshot': final_snapshot or {}},
            )
            profile_candidates = [self._serialize_profile_candidate(row) for row in profile_rows] if profile_rows else list(fallback_phase1.get('profileCandidates') or [])
            business_key_candidates = [self._serialize_business_key_candidate(row) for row in key_rows] if key_rows else list(fallback_phase1.get('businessKeyCandidates') or [])
            reason_buckets = [self._serialize_quarantine_bucket(row) for row in quarantine_rows] if quarantine_rows else list(fallback_phase1.get('reasonBuckets') or [])
            importability_evaluation = dict(confirm_meta.get('importabilityEvaluation') or fallback_phase1.get('importabilityEvaluation') or {})
            return {
                **self._summary_from_ingest_batch(batch),
                'algorithmVersion': self.ALGORITHM_VERSION,
                'parseSnapshot': parse_snapshot,
                'confirmSnapshot': confirm_snapshot,
                'finalSnapshot': final_snapshot,
                'parseResultMeta': parse_meta,
                'confirmResultMeta': confirm_meta,
                'gateResults': [
                    {
                        'gateName': row.gate_name,
                        'gateStatus': row.gate_status,
                        'reasonList': row.reason_list or [],
                        'summary': row.summary or {},
                    }
                    for row in gate_rows
                ],
                'fieldMappings': serialized_mappings,
                'manualOverrides': [self._serialize_manual_override(row) for row in override_rows],
                'sourceObjects': [
                    {
                        'objectType': row.object_type,
                        'fileName': row.file_name,
                        'filePath': row.file_path,
                        'fileSize': row.file_size,
                        'contentMeta': row.content_meta or {},
                    }
                    for row in source_rows
                ],
                'rawRecords': [self._serialize_raw_record(row) for row in raw_rows],
                'eventTimeline': timeline,
                'profileCandidates': profile_candidates,
                'businessKeyCandidates': business_key_candidates,
                'importabilityEvaluation': importability_evaluation,
                'topQuarantineReasons': reason_buckets[:5],
                'reasonBuckets': reason_buckets,
            }

    def get_batch_timeline(self, batch_ref: str) -> Optional[Dict[str, Any]]:
        detail = self.get_batch_detail(batch_ref)
        if not detail:
            return None
        events = detail.get('eventTimeline') or []
        return {
            'batchId': detail.get('batchId'),
            'workspaceBatchId': detail.get('workspaceBatchId'),
            'sessionId': detail.get('sessionId'),
            'contractVersion': detail.get('contractVersion') or BatchService.CONTRACT_VERSION,
            'eventTimeline': events,
            'events': events,
            'total': len(events),
        }

    def get_batch_quarantine_summary(self, batch_ref: str) -> Optional[Dict[str, Any]]:
        detail = self.get_batch_detail(batch_ref)
        if not detail:
            return None
        final_snapshot = detail.get('finalSnapshot') or {}
        reason_buckets = list(detail.get('reasonBuckets') or detail.get('topQuarantineReasons') or [])
        return {
            'batchId': detail.get('batchId'),
            'workspaceBatchId': detail.get('workspaceBatchId'),
            
            'contractVersion': detail.get('contractVersion') or BatchService.CONTRACT_VERSION,
            'algorithmVersion': self.ALGORITHM_VERSION,
            'quarantineCount': int(final_snapshot.get('quarantineCount') or detail.get('quarantineCount') or 0),
            'importabilityStatus': final_snapshot.get('importabilityStatus') or detail.get('importabilityStatus'),
            'reasonList': [bucket.get('reasonCode') for bucket in reason_buckets],
            'reasonBuckets': reason_buckets,
            'topReasons': reason_buckets[:5],
        }


    @staticmethod
    def _serialize_raw_record(row: RawRecord) -> Dict[str, Any]:
        return {
            'rawRecordId': row.id,
            'batchId': row.batch_id,
            'rawStage': row.raw_stage,
            'recordIndex': row.record_index,
            'sourceName': row.source_name,
            'sourceMode': row.source_mode,
            'sourceHash': row.source_hash,
            'sourceSignature': row.source_signature,
            'previewText': row.preview_text,
            'payload': row.payload or {},
            'createdAt': row.created_at.isoformat() if row.created_at else None,
        }

    def append_audit_event(self, batch_id: int, event_type: str, payload: Dict[str, Any]) -> None:
        get_engine()
        with get_session() as session:
            session.add(BatchAuditEvent(batch_id=batch_id, event_type=event_type, payload=dict(payload or {})))

    def record_raw_payload(
        self,
        *,
        batch_id: int,
        raw_stage: str,
        payload: Dict[str, Any],
        source_name: str | None = None,
        source_mode: str | None = None,
        source_hash: str | None = None,
        source_signature: str | None = None,
        preview_text: str | None = None,
        record_index: int = 0,
    ) -> Optional[int]:
        get_engine()
        with get_session() as session:
            row = RawRecord(
                batch_id=batch_id,
                raw_stage=self._clean_str(raw_stage, 'parse'),
                record_index=self._int_or_zero(record_index),
                source_name=self._clean_str(source_name) or None,
                source_mode=self._clean_str(source_mode) or None,
                source_hash=self._clean_str(source_hash) or None,
                source_signature=self._clean_str(source_signature) or None,
                preview_text=self._clean_str(preview_text) or None,
                payload=dict(payload or {}),
            )
            session.add(row)
            session.flush()
            return row.id

    def create_job(
        self,
        *,
        job_type: str,
        batch_id: int | None = None,
        operator: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str | None = None,
        request_payload: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        job_code = f'job_{datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")}'
        get_engine()
        with get_session() as session:
            row = ReplayJob(
                job_code=job_code,
                batch_id=batch_id,
                job_type=self._clean_str(job_type, 'upload'),
                status='queued',
                trace_id=self._clean_str(trace_id) or None,
                idempotency_key=self._clean_str(idempotency_key) or None,
                operator=self._clean_str(operator) or None,
                request_payload=dict(request_payload or {}),
            )
            session.add(row)
            session.flush()
            job_id = row.id
        self.append_job_event(job_id, 'queued', {'batchId': batch_id, 'requestPayload': request_payload or {}})
        return self.get_job(str(job_id)) or {'jobId': job_id, 'jobCode': job_code, 'status': 'queued'}

    def append_job_event(self, job_id: int, event_type: str, payload: Dict[str, Any]) -> None:
        get_engine()
        with get_session() as session:
            session.add(JobEvent(job_id=job_id, event_type=event_type, payload=dict(payload or {})))

    def update_job(
        self,
        job_id: int,
        *,
        status: str,
        batch_id: int | None = None,
        result_payload: Dict[str, Any] | None = None,
        error_message: str | None = None,
        event_type: str | None = None,
    ) -> Optional[Dict[str, Any]]:
        get_engine()
        with get_session() as session:
            row = session.get(ReplayJob, int(job_id))
            if row is None:
                return None
            previous_status = row.status
            row.status = self._clean_str(status, previous_status)
            if batch_id not in (None, ''):
                row.batch_id = self._int_or_zero(batch_id)
            if previous_status == 'queued' and row.started_at is None:
                row.started_at = datetime.now(timezone.utc)
            if row.status in {'completed', 'failed'}:
                row.finished_at = datetime.now(timezone.utc)
            if result_payload is not None:
                row.result_payload = dict(result_payload or {})
            if error_message is not None:
                row.error_message = self._clean_str(error_message) or None
            session.flush()
            payload = {
                'batchId': row.batch_id,
                'status': row.status,
                'resultPayload': row.result_payload or {},
                'errorMessage': row.error_message,
            }
        self.append_job_event(int(job_id), event_type or row.status, payload)
        return self.get_job(str(job_id))

    def get_job(self, job_ref: str) -> Optional[Dict[str, Any]]:
        job_ref = str(job_ref or '').strip()
        if not job_ref:
            return None
        get_engine()
        with get_session() as session:
            row = None
            if job_ref.isdigit():
                row = session.get(ReplayJob, int(job_ref))
            if row is None:
                row = session.execute(select(ReplayJob).where(ReplayJob.job_code == job_ref)).scalar_one_or_none()
            if row is None:
                return None
            events = session.execute(select(JobEvent).where(JobEvent.job_id == row.id).order_by(JobEvent.id.asc())).scalars().all()
            return {
                'jobId': row.id,
                'jobCode': row.job_code,
                'batchId': row.batch_id,
                'jobType': row.job_type,
                'status': row.status,
                'traceId': row.trace_id,
                'idempotencyKey': row.idempotency_key,
                'operator': row.operator,
                'requestPayload': row.request_payload or {},
                'resultPayload': row.result_payload or {},
                'errorMessage': row.error_message,
                'startedAt': row.started_at.isoformat() if row.started_at else None,
                'finishedAt': row.finished_at.isoformat() if row.finished_at else None,
                'timeline': [
                    {
                        'eventType': event.event_type,
                        'payload': event.payload or {},
                        'createdAt': event.created_at.isoformat() if event.created_at else None,
                    }
                    for event in events
                ],
            }
    def replay_batch(
        self,
        *,
        batch_ref: str,
        trace_id: str | None = None,
        idempotency_key: str | None = None,
        operator: str | None = None,
        notes: str | None = None,
    ) -> Dict[str, Any]:
        batch_ref = str(batch_ref or "").strip()
        if not batch_ref:
            raise ValueError("batch_not_found")

        original_batch = self._resolve_batch(batch_ref)
        if original_batch is None:
            raise ValueError("batch_not_found")

        detail = self.get_batch_detail(str(original_batch.id)) or {}
        raw_records = list(detail.get("rawRecords") or [])
        if not raw_records:
            raise ValueError("replay_source_not_found")

        notes_value = self._clean_str(notes) or None
        request_payload = {
            "batchRef": str(original_batch.id),
            "notes": notes_value,
            "sourcePath": (
                (raw_records[0].get("payload") or {}).get("sourcePath")
                or (raw_records[0].get("payload") or {}).get("filePath")
                or detail.get("filePath")
            ),
        }

        job = self.create_job(
            job_type="replay",
            batch_id=original_batch.id,
            operator=self._clean_str(operator) or None,
            trace_id=self._clean_str(trace_id) or None,
            idempotency_key=self._clean_str(idempotency_key) or None,
            request_payload=request_payload,
        )
        job_id = self._int_or_zero(job.get("jobId"))
        job_code = job.get("jobCode")

        try:
            self.update_job(
                job_id,
                status="running",
                batch_id=original_batch.id,
                result_payload={},
                event_type="replay_started",
            )

            # 选一个最适合 replay 的 raw source
            source_row = None
            for row in raw_records:
                payload = dict(row.get("payload") or {})
                if payload.get("sourcePath") or payload.get("filePath") or row.get("sourceSignature") or row.get("sourceHash"):
                    source_row = row
                    break
            if source_row is None:
                source_row = raw_records[0]

            source_payload = dict(source_row.get("payload") or {})
            source_path = self._clean_str(
                source_payload.get("sourcePath")
                or source_payload.get("filePath")
                or detail.get("filePath")
            ) or None
            source_name = self._clean_str(
                source_row.get("sourceName")
                or source_payload.get("fileName")
                or detail.get("fileName")
                or original_batch.source_name
            ) or None
            source_hash = self._clean_str(
                source_row.get("sourceHash") or source_payload.get("sourceHash")
            ) or None
            source_signature = self._clean_str(
                source_row.get("sourceSignature") or source_payload.get("sourceSignature")
            ) or None

            parse_snapshot = dict(original_batch.parse_snapshot or {})
            confirm_snapshot = dict(original_batch.confirm_snapshot or {})
            final_snapshot = dict(original_batch.final_snapshot or confirm_snapshot or parse_snapshot)

            get_engine()
            with get_session() as session:
                replay_batch = IngestBatch(
                    workspace_batch_id=None,
                    legacy_session_id=None,
                    legacy_import_batch_id=original_batch.legacy_import_batch_id,
                    dataset_kind=original_batch.dataset_kind,
                    import_profile=original_batch.import_profile,
                    source_mode="replay",
                    source_name=source_name or original_batch.source_name,
                    platform=original_batch.platform,
                    shop_id=original_batch.shop_id,
                    operator=self._clean_str(operator) or original_batch.operator,
                    contract_version=self._clean_str(
                        original_batch.contract_version,
                        self.CONTRACT_VERSION,
                    ),
                    batch_status=self._clean_str(original_batch.batch_status, "imported"),
                    transport_status=self._clean_str(original_batch.transport_status, "passed"),
                    semantic_status=self._clean_str(original_batch.semantic_status, "passed"),
                    importability_status=self._clean_str(original_batch.importability_status, "passed"),
                    imported_rows=self._int_or_zero(original_batch.imported_rows),
                    quarantine_count=self._int_or_zero(original_batch.quarantine_count),
                    raw_parse_meta=dict(original_batch.raw_parse_meta or {}),
                    raw_confirm_meta=dict(original_batch.raw_confirm_meta or {}),
                    parse_snapshot=parse_snapshot,
                    confirm_snapshot=confirm_snapshot,
                    final_snapshot=final_snapshot,
                )
                session.add(replay_batch)
                session.flush()

                replay_batch.workspace_batch_id = f"ws-{int(replay_batch.id):06d}"

                session.add(
                    IngestSourceObject(
                        batch_id=replay_batch.id,
                        object_type="file",
                        file_name=source_name or original_batch.source_name,
                        file_path=source_path,
                        file_size=None,
                        content_meta={
                            "sourceHash": source_hash,
                            "sourceSignature": source_signature,
                            "originalBatchId": original_batch.id,
                            "jobId": job_id,
                            "replay": True,
                        },
                    )
                )

                session.add(
                    BatchAuditEvent(
                        batch_id=replay_batch.id,
                        event_type="replay",
                        event_status="running",
                        payload={
                            "eventType": "replay",
                            "status": "running",
                            "originalBatchId": original_batch.id,
                            "jobId": job_id,
                            "sourcePath": source_path,
                            "sourceName": source_name,
                            "sourceHash": source_hash,
                            "sourceSignature": source_signature,
                            "notes": notes_value,
                        },
                    )
                )

                session.add(
                    BatchAuditEvent(
                        batch_id=replay_batch.id,
                        event_type="replay_completed",
                        event_status="completed",
                        payload={
                            "eventType": "replay_completed",
                            "status": "completed",
                            "originalBatchId": original_batch.id,
                            "jobId": job_id,
                            "batchId": replay_batch.id,
                            "workspaceBatchId": replay_batch.workspace_batch_id,
                            "notes": notes_value,
                        },
                    )
                )

                session.flush()
                replay_batch_id = int(replay_batch.id)
                replay_workspace_batch_id = replay_batch.workspace_batch_id

            # 复制 raw records 到 replay batch
            for row in raw_records:
                self.record_raw_payload(
                    batch_id=replay_batch_id,
                    raw_stage=self._clean_str(row.get("rawStage"), "parse"),
                    payload=dict(row.get("payload") or {}),
                    source_name=self._clean_str(row.get("sourceName")) or source_name,
                    source_mode="replay",
                    source_hash=self._clean_str(row.get("sourceHash")) or source_hash,
                    source_signature=self._clean_str(row.get("sourceSignature")) or source_signature,
                    preview_text=self._clean_str(row.get("previewText")) or None,
                    record_index=self._int_or_zero(row.get("recordIndex")),
                )

            result = {
                "batchId": replay_batch_id,
                "contractVersion": self.CONTRACT_VERSION,
                "jobCode": job_code,
                "jobId": job_id,
                "notes": notes_value,
                "originalBatchId": original_batch.id,
                "status": "completed",
                "workspaceBatchId": replay_workspace_batch_id,
            }

            self.update_job(
                job_id,
                status="completed",
                batch_id=replay_batch_id,
                result_payload=result,
                event_type="completed",
            )
            return result

        except Exception as exc:
            self.update_job(
                job_id,
                status="failed",
                batch_id=original_batch.id,
                result_payload={},
                error_message=str(exc),
                event_type="failed",
            )
            raise
        