from __future__ import annotations

from typing import Any, Dict, Optional

from .contracts import BatchSnapshot, MappingSummary


class IngestionOrchestrator:
    """
    轻量编排层：
    - 不替代 ImportService
    - 负责把 parse/confirm 结果统一成 batch snapshot
    - 兼容新旧版本调用签名
    """

    CONTRACT_VERSION = "p1.v1"

    def _coerce_mapping_summary(self, parse_result: Dict[str, Any]) -> MappingSummary:
        source = dict(parse_result.get("mappingSummary") or {})
        return MappingSummary(
            mappedCount=int(source.get("mappedCount") or parse_result.get("mappedCount") or 0),
            unmappedCount=int(source.get("unmappedCount") or parse_result.get("unmappedCount") or 0),
            mappingCoverage=float(source.get("mappingCoverage") or parse_result.get("mappingCoverage") or 0.0),
            mappedConfidence=float(source.get("mappedConfidence") or parse_result.get("mappedConfidence") or 0.0),
            mappedCanonicalFields=list(source.get("mappedCanonicalFields") or parse_result.get("mappedCanonicalFields") or []),
            topUnmappedHeaders=list(source.get("topUnmappedHeaders") or parse_result.get("topUnmappedHeaders") or []),
        )

    def build_parse_snapshot(
        self,
        parse_result: Dict[str, Any],
        dataset_kind: Optional[str] = None,
        import_profile: Optional[str] = None,
    ) -> BatchSnapshot:
        dataset = str(dataset_kind or parse_result.get("datasetKind") or "orders")
        profile = str(import_profile or parse_result.get("importProfile") or dataset)
        audit = dict(parse_result.get("auditSummary") or {})
        audit.update({
            "sessionId": parse_result.get("sessionId"),
            "fileName": parse_result.get("fileName"),
            "finalStatus": parse_result.get("finalStatus"),
            "importProfile": profile,
        })
        return BatchSnapshot(
            contractVersion=self.CONTRACT_VERSION,
            datasetKind=dataset,
            batchStatus=str(parse_result.get("batchStatus") or "validated"),
            transportStatus=str(parse_result.get("transportStatus") or (parse_result.get("batchSnapshot") or {}).get("transportStatus") or "failed"),
            semanticStatus=str(parse_result.get("semanticStatus") or (parse_result.get("batchSnapshot") or {}).get("semanticStatus") or "failed"),
            importabilityStatus=str(parse_result.get("importabilityStatus") or (parse_result.get("batchSnapshot") or {}).get("importabilityStatus") or "failed"),
            mappingSummary=self._coerce_mapping_summary(parse_result),
            quarantineCount=int(parse_result.get("quarantineCount") or 0),
            importedRows=int(parse_result.get("importedRows") or 0),
            auditSummary=audit,
        )

    def build_confirm_snapshot(
        self,
        parse_result: Dict[str, Any],
        confirm_result: Dict[str, Any],
        dataset_kind: Optional[str] = None,
        import_profile: Optional[str] = None,
    ) -> BatchSnapshot:
        dataset = str(
            dataset_kind
            or confirm_result.get("datasetKind")
            or parse_result.get("datasetKind")
            or (parse_result.get("auditSummary") or {}).get("datasetKind")
            or "orders"
        )
        profile = str(
            import_profile
            or confirm_result.get("importProfile")
            or parse_result.get("importProfile")
            or (parse_result.get("auditSummary") or {}).get("importProfile")
            or dataset
        )
        audit = dict(confirm_result.get("runtimeAudit") or {})
        audit.update({
            "importProfile": profile,
            "status": confirm_result.get("status"),
            "success": confirm_result.get("success"),
        })
        return BatchSnapshot(
            contractVersion=self.CONTRACT_VERSION,
            datasetKind=dataset,
            batchStatus=str(confirm_result.get("batchStatus") or "failed"),
            transportStatus=str(confirm_result.get("transportStatus") or parse_result.get("transportStatus") or (parse_result.get("batchSnapshot") or {}).get("transportStatus") or "failed"),
            semanticStatus=str(confirm_result.get("semanticStatus") or parse_result.get("semanticStatus") or (parse_result.get("batchSnapshot") or {}).get("semanticStatus") or "failed"),
            importabilityStatus=str(confirm_result.get("importabilityStatus") or "failed"),
            mappingSummary=self._coerce_mapping_summary(parse_result),
            quarantineCount=int(confirm_result.get("quarantineCount") or 0),
            importedRows=int(confirm_result.get("importedRows") or 0),
            auditSummary=audit,
        )
