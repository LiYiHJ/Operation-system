from __future__ import annotations

from .models import DiscountSimulation, ProfitInput, ProfitResult


class ProfitSolver:
    """V5.1 利润中心求解器。"""

    @staticmethod
    def solve_current(payload: ProfitInput) -> ProfitResult:
        v = payload.variable_rate_total
        f = payload.fixed_cost_total
        p = payload.sale_price

        net_profit = p * (1 - v) - f
        net_margin = (net_profit / p) if p else 0.0
        break_even = f / (1 - v) if v < 1 else float("inf")
        break_even_discount = break_even / payload.list_price if payload.list_price else float("inf")

        return ProfitResult(
            net_profit=round(net_profit, 4),
            net_margin=round(net_margin, 4),
            is_loss=net_profit < 0,
            break_even_price=round(break_even, 4),
            break_even_discount_ratio=round(break_even_discount, 4),
        )

    @staticmethod
    def target_profit_price(target_profit: float, v: float, f: float) -> float:
        return (target_profit + f) / (1 - v)

    @staticmethod
    def target_margin_price(target_margin: float, v: float, f: float) -> float:
        if target_margin >= 1 - v:
            raise ValueError("target margin is infeasible under current variable rates")
        return f / (1 - v - target_margin)

    @staticmethod
    def target_roi_price(target_roi: float, v: float, f: float) -> float:
        return f * (1 + target_roi) / (1 - v)

    @staticmethod
    def simulate_discounts(payload: ProfitInput, ratios: list[float]) -> list[DiscountSimulation]:
        rows: list[DiscountSimulation] = []
        for ratio in ratios:
            deal_price = payload.list_price * ratio
            net_profit = deal_price * (1 - payload.variable_rate_total) - payload.fixed_cost_total
            net_margin = (net_profit / deal_price) if deal_price else 0.0
            rows.append(
                DiscountSimulation(
                    discount_ratio=ratio,
                    deal_price=round(deal_price, 4),
                    net_profit=round(net_profit, 4),
                    net_margin=round(net_margin, 4),
                    is_loss=net_profit < 0,
                )
            )
        return rows
