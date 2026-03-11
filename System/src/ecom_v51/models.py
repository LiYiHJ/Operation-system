from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(slots=True)
class ImportBatchDiagnosis:
    file_name: str
    detected_header_row: int | None
    platform: str
    mapped_fields: int
    unmapped_fields: list[str]
    key_field: str | None
    row_error_count: int
    status: Literal["success", "partial", "failed"]
    suggestions: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ProfitInput:
    sale_price: float
    list_price: float
    variable_rate_total: float
    fixed_cost_total: float


@dataclass(slots=True)
class ProfitResult:
    net_profit: float
    net_margin: float
    is_loss: bool
    break_even_price: float
    break_even_discount_ratio: float


@dataclass(slots=True)
class DiscountSimulation:
    discount_ratio: float
    deal_price: float
    net_profit: float
    net_margin: float
    is_loss: bool


@dataclass(slots=True)
class StrategyTask:
    strategy_type: Literal[
        "pricing", "ads", "inventory", "conversion", "risk_control"
    ]
    level: Literal["shop", "category", "sku"]
    priority: Literal["P0", "P1", "P2", "P3"]
    issue_summary: str
    recommended_action: str
    observation_metrics: list[str]


@dataclass(slots=True)
class SkuSnapshot:
    sku: str
    impressions: int
    card_visits: int
    add_to_cart: int
    orders: int
    ad_spend: float
    ad_revenue: float
    stock_total: int
    days_of_supply: float
    rating: float
    return_rate: float
    cancel_rate: float
    sale_price: float
    list_price: float
    variable_rate_total: float
    fixed_cost_total: float


@dataclass(slots=True)
class SkuWarRoomReport:
    sku: str
    funnel: dict[str, float]
    net_profit: float
    net_margin: float
    break_even_price: float
    discount_simulations: list[DiscountSimulation]
    strategy_tasks: list[StrategyTask]
