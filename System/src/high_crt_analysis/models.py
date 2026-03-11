from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal

Dimension = Literal["conversion", "retention", "traction"]


@dataclass(slots=True)
class ProductScores:
    """CRT 三个维度评分，范围建议 0-100。"""

    conversion: float
    retention: float
    traction: float

    def normalized(self) -> "ProductScores":
        """将所有指标限制在 0-100。"""
        return ProductScores(
            conversion=max(0, min(100, self.conversion)),
            retention=max(0, min(100, self.retention)),
            traction=max(0, min(100, self.traction)),
        )

    def as_dict(self) -> Dict[str, float]:
        return {
            "conversion": self.conversion,
            "retention": self.retention,
            "traction": self.traction,
        }


@dataclass(slots=True)
class ProductProfile:
    """产品基础信息及 CRT 评分输入。"""

    name: str
    category: str
    target_users: str
    scores: ProductScores
    notes: List[str] = field(default_factory=list)


@dataclass(slots=True)
class DiagnosisItem:
    """单维度诊断结果。"""

    dimension: Dimension
    score: float
    health: Literal["healthy", "watch", "critical"]
    observation: str
    root_causes: List[str]


@dataclass(slots=True)
class PriorityItem:
    """改进优先级事项。"""

    dimension: Dimension
    initiative: str
    impact: int
    effort: int
    priority_score: float


@dataclass(slots=True)
class ActionPlan:
    """分阶段行动计划。"""

    phase: Literal["0-30天", "31-60天", "61-90天"]
    goals: List[str]


@dataclass(slots=True)
class AnalysisResult:
    """高 CRT 系统化分析结果。"""

    product_name: str
    weighted_score: float
    grade: str
    maturity_stage: str
    dimension_breakdown: Dict[str, float]
    diagnosis: List[DiagnosisItem]
    priorities: List[PriorityItem]
    action_plan_90d: List[ActionPlan]
    summary: str
