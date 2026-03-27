from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal

BatchStatus = Literal[
    "uploaded",
    "parsed",
    "mapped",
    "validated",
    "imported",
    "failed",
]
TransportStatus = Literal["passed", "failed"]
SemanticStatus = Literal["passed", "risk", "failed"]
ImportabilityStatus = Literal["passed", "risk", "failed"]


@dataclass
class MappingSummary:
    mappedCount: int = 0
    unmappedCount: int = 0
    mappingCoverage: float = 0.0
    mappedConfidence: float = 0.0
    mappedCanonicalFields: List[str] = field(default_factory=list)
    topUnmappedHeaders: List[str] = field(default_factory=list)


@dataclass
class BatchSnapshot:
    contractVersion: str
    datasetKind: str
    batchStatus: BatchStatus | str
    transportStatus: TransportStatus | str
    semanticStatus: SemanticStatus | str
    importabilityStatus: ImportabilityStatus | str
    mappingSummary: MappingSummary
    quarantineCount: int = 0
    importedRows: int = 0
    auditSummary: Dict[str, Any] = field(default_factory=dict)
