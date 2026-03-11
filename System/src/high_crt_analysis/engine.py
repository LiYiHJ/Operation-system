from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List

from .models import (
    ActionPlan,
    AnalysisResult,
    DiagnosisItem,
    PriorityItem,
    ProductProfile,
    ProductScores,
)


@dataclass(slots=True)
class WeightConfig:
    conversion: float = 0.4
    retention: float = 0.35
    traction: float = 0.25

    def as_dict(self) -> Dict[str, float]:
        return {
            "conversion": self.conversion,
            "retention": self.retention,
            "traction": self.traction,
        }


class AnalysisEngine:
    """高 CRT 产品分析系统引擎（诊断 + 优先级 + 行动计划）。"""

    def __init__(self, weights: WeightConfig | None = None) -> None:
        self.weights = weights or WeightConfig()

    def analyze(self, profile: ProductProfile) -> AnalysisResult:
        scores = profile.scores.normalized()

        weighted = (
            scores.conversion * self.weights.conversion
            + scores.retention * self.weights.retention
            + scores.traction * self.weights.traction
        )

        breakdown = {
            "conversion": round(scores.conversion * self.weights.conversion, 2),
            "retention": round(scores.retention * self.weights.retention, 2),
            "traction": round(scores.traction * self.weights.traction, 2),
        }

        diagnosis = self._diagnose(scores)
        priorities = self._build_priority_backlog(scores)
        action_plan = self._build_90d_plan(priorities)

        return AnalysisResult(
            product_name=profile.name,
            weighted_score=round(weighted, 2),
            grade=self._grade(weighted),
            maturity_stage=self._maturity_stage(weighted),
            dimension_breakdown=breakdown,
            diagnosis=diagnosis,
            priorities=priorities,
            action_plan_90d=action_plan,
            summary=self._summary(profile.name, weighted, diagnosis),
        )

    @staticmethod
    def to_dict(result: AnalysisResult) -> Dict[str, object]:
        return asdict(result)

    def _diagnose(self, scores: ProductScores) -> List[DiagnosisItem]:
        playbook = {
            "conversion": {
                "good": "转化路径顺畅，价值传达清晰。",
                "mid": "转化有波动，关键漏斗环节存在损耗。",
                "bad": "转化薄弱，用户从兴趣到付费断层明显。",
                "causes": ["价值表达不够聚焦", "注册/付费路径过长", "新客激励设计不足"],
            },
            "retention": {
                "good": "留存健康，核心场景已形成习惯。",
                "mid": "留存一般，部分用户在首周流失。",
                "bad": "留存偏低，复访驱动力不足。",
                "causes": ["首周激活不足", "缺少持续触发机制", "功能价值未被重复感知"],
            },
            "traction": {
                "good": "增长动能强，渠道效率较优。",
                "mid": "增长平稳但缺少爆发点。",
                "bad": "增长不足，获客与传播效率偏低。",
                "causes": ["渠道结构单一", "裂变机制弱", "品牌与内容协同不足"],
            },
        }

        items: List[DiagnosisItem] = []
        for dimension, score in scores.as_dict().items():
            if score >= 75:
                health = "healthy"
                observation = playbook[dimension]["good"]
            elif score >= 60:
                health = "watch"
                observation = playbook[dimension]["mid"]
            else:
                health = "critical"
                observation = playbook[dimension]["bad"]

            items.append(
                DiagnosisItem(
                    dimension=dimension,
                    score=round(score, 2),
                    health=health,
                    observation=observation,
                    root_causes=playbook[dimension]["causes"][:2 if health == "healthy" else 3],
                )
            )

        return items

    def _build_priority_backlog(self, scores: ProductScores) -> List[PriorityItem]:
        templates = {
            "conversion": "优化转化漏斗（落地页-注册-首购）",
            "retention": "搭建分层留存运营（首周激活+复访触达）",
            "traction": "建立增长复利机制（渠道归因+推荐裂变）",
        }
        items: List[PriorityItem] = []

        for dim, score in scores.as_dict().items():
            gap = 100 - score
            impact = min(10, max(1, int(round(gap / 10))))
            effort = 3 if score < 60 else 5 if score < 75 else 7
            priority_score = round((impact * 1.5) / effort, 2)

            items.append(
                PriorityItem(
                    dimension=dim,
                    initiative=templates[dim],
                    impact=impact,
                    effort=effort,
                    priority_score=priority_score,
                )
            )

        return sorted(items, key=lambda x: x.priority_score, reverse=True)

    @staticmethod
    def _build_90d_plan(priorities: List[PriorityItem]) -> List[ActionPlan]:
        top = priorities[:2]
        tail = priorities[2:]

        phase_1_goals = [
            f"诊断并修复 {item.dimension} 的关键瓶颈：{item.initiative}" for item in top
        ]
        phase_2_goals = [
            f"将 {item.dimension} 优化转为标准化实验，建立周度复盘看板" for item in top
        ]
        phase_3_goals = [
            f"扩展 {item.dimension} 增长动作并沉淀 SOP" for item in top + tail
        ]

        return [
            ActionPlan(phase="0-30天", goals=phase_1_goals),
            ActionPlan(phase="31-60天", goals=phase_2_goals),
            ActionPlan(phase="61-90天", goals=phase_3_goals),
        ]

    @staticmethod
    def _grade(score: float) -> str:
        if score >= 85:
            return "A"
        if score >= 75:
            return "B"
        if score >= 65:
            return "C"
        return "D"

    @staticmethod
    def _maturity_stage(score: float) -> str:
        if score >= 85:
            return "规模化增长期"
        if score >= 75:
            return "增长优化期"
        if score >= 65:
            return "产品市场匹配探索期"
        return "基础能力建设期"

    @staticmethod
    def _summary(product_name: str, score: float, diagnosis: List[DiagnosisItem]) -> str:
        critical_count = sum(1 for item in diagnosis if item.health == "critical")
        if critical_count == 0:
            return f"{product_name} 的 CRT 结构健康（{score:.2f} 分），建议转向规模化复制。"
        return (
            f"{product_name} 当前 CRT 总分 {score:.2f}，存在 {critical_count} 个关键薄弱维度，"
            "建议优先聚焦高优先级事项并按 90 天计划推进。"
        )
