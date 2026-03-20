from __future__ import annotations

from typing import Any, Dict, Optional

from .contracts import BatchSnapshot, MappingSummary


class IngestionOrchestrator:
    """
    P0 轻量编排层：
    - 当前不替代 ImportService
    - 只负责把 parse/confirm 结果统一成 batch snapshot
    - 为后续文件导入 / API 同步共用同一批次契约做准备
    """

    CONTRACT_VERSION = "p0.v1"

    def build_parse_snapshot(
        self,
        parse_result: Dict[str, Any],
        dataset_kind: Optional[str] = None,
    ) -> BatchSnapshot:
        dataset = dataset_kind or str(parse_result.get("datasetKind") or "orders")
        return BatchSnapshot(
            contractVersion=self.CONTRACT_VERSION,
            datasetKind=dataset,
            batchStatus=str(parse_result.get("batchStatus") or "validated"),
            transportStatus=str(parse_result.get("transportStatus") or "failed"),
            semanticStatus=str(parse_result.get("semanticStatus") or "failed"),
            importabilityStatus="failed",
            mappingSummary=MappingSummary(
                mappedCount=int(parse_result.get("mappedCount") or 0),
                unmappedCount=int(parse_result.get("unmappedCount") or 0),
                mappingCoverage=float(parse_result.get("mappingCoverage") or 0.0),
                mappedConfidence=float(parse_result.get("mappedConfidence") or 0.0),
                mappedCanonicalFields=list(parse_result.get("mappedCanonicalFields") or []),
                topUnmappedHeaders=list(parse_result.get("topUnmappedHeaders") or []),
            ),
            quarantineCount=0,
            importedRows=0,
            auditSummary={
                "sessionId": parse_result.get("sessionId"),
                "fileName": parse_result.get("fileName"),
                "finalStatus": parse_result.get("finalStatus"),
            },
        )

    def build_confirm_snapshot(
        self,
        parse_result: Dict[str, Any],
        confirm_result: Dict[str, Any],
    ) -> BatchSnapshot:
        dataset = str(
            confirm_result.get("datasetKind")
            or parse_result.get("datasetKind")
            or "orders"
        )
        return BatchSnapshot(
            contractVersion=self.CONTRACT_VERSION,
            datasetKind=dataset,
            batchStatus=str(confirm_result.get("batchStatus") or "failed"),
            transportStatus=str(confirm_result.get("transportStatus") or "failed"),
            semanticStatus=str(confirm_result.get("semanticStatus") or "failed"),
            importabilityStatus=str(confirm_result.get("importabilityStatus") or "failed"),
            mappingSummary=MappingSummary(
                mappedCount=int(parse_result.get("mappedCount") or 0),
                unmappedCount=int(parse_result.get("unmappedCount") or 0),
                mappingCoverage=float(parse_result.get("mappingCoverage") or 0.0),
                mappedConfidence=float(parse_result.get("mappedConfidence") or 0.0),
                mappedCanonicalFields=list(parse_result.get("mappedCanonicalFields") or []),
                topUnmappedHeaders=list(parse_result.get("topUnmappedHeaders") or []),
            ),
            quarantineCount=int(confirm_result.get("quarantineCount") or 0),
            importedRows=int(confirm_result.get("importedRows") or 0),
            auditSummary=dict(confirm_result.get("runtimeAudit") or {}),
        )
