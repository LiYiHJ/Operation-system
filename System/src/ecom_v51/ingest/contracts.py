from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal

DatasetKind = Literal[
    "orders",
    "ads",
    "reviews",
    "refunds_returns",
    "inventory_snapshots",
    "price_snapshots",
    "store_health",
    "cost_config",
    "execution_results",
]

BatchStatus = Literal[
    "uploaded",
    "parsed",
    "mapped",
    "validated",
    "blocked",
    "imported",
    "partially_imported",
    "failed",
]

TransportStatus = Literal["passed", "failed"]
SemanticStatus = Literal["passed", "risk", "failed"]
ImportabilityStatus = Literal["passed", "risk", "failed"]


@dataclass
class GateSnapshot:
    transportStatus: TransportStatus = "failed"
    semanticStatus: SemanticStatus = "failed"
    importabilityStatus: ImportabilityStatus = "failed"
    reasons: List[str] = field(default_factory=list)
    riskOverrideReasons: List[str] = field(default_factory=list)
    acceptanceReasons: List[str] = field(default_factory=list)
    quarantineCount: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MappingSummary:
    mappedCount: int = 0
    unmappedCount: int = 0
    mappingCoverage: float = 0.0
    mappedConfidence: float = 0.0
    mappedCanonicalFields: List[str] = field(default_factory=list)
    topUnmappedHeaders: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BatchSnapshot:
    contractVersion: str
    datasetKind: str
    batchStatus: BatchStatus
    transportStatus: TransportStatus
    semanticStatus: SemanticStatus
    importabilityStatus: ImportabilityStatus
    mappingSummary: MappingSummary
    quarantineCount: int = 0
    importedRows: int = 0
    auditSummary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["mappingSummary"] = self.mappingSummary.to_dict()
        return payload
