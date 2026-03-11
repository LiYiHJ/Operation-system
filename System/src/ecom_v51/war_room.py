from __future__ import annotations

from .models import ProfitInput, SkuSnapshot, SkuWarRoomReport
from .profit_solver import ProfitSolver
from .strategy import StrategyEngine


class WarRoomService:
    def __init__(self) -> None:
        self.profit_solver = ProfitSolver()
        self.strategy_engine = StrategyEngine()

    def build_report(self, snapshot: SkuSnapshot) -> SkuWarRoomReport:
        ctr = snapshot.card_visits / snapshot.impressions if snapshot.impressions else 0.0
        add_to_cart_rate = snapshot.add_to_cart / snapshot.card_visits if snapshot.card_visits else 0.0
        order_rate = snapshot.orders / snapshot.add_to_cart if snapshot.add_to_cart else 0.0
        roas = snapshot.ad_revenue / snapshot.ad_spend if snapshot.ad_spend else 0.0

        profit_input = ProfitInput(
            sale_price=snapshot.sale_price,
            list_price=snapshot.list_price,
            variable_rate_total=snapshot.variable_rate_total,
            fixed_cost_total=snapshot.fixed_cost_total,
        )
        current_profit = self.profit_solver.solve_current(profit_input)

        tasks = self.strategy_engine.generate_for_sku(
            ctr=ctr,
            add_to_cart_rate=add_to_cart_rate,
            order_rate=order_rate,
            net_margin=current_profit.net_margin,
            roas=roas,
            days_of_supply=snapshot.days_of_supply,
            return_rate=snapshot.return_rate,
            rating=snapshot.rating,
        )

        discount_simulations = self.profit_solver.simulate_discounts(
            profit_input,
            ratios=[0.95, 0.9, 0.85],
        )

        return SkuWarRoomReport(
            sku=snapshot.sku,
            funnel={
                "ctr": round(ctr, 4),
                "add_to_cart_rate": round(add_to_cart_rate, 4),
                "order_rate": round(order_rate, 4),
            },
            net_profit=current_profit.net_profit,
            net_margin=current_profit.net_margin,
            break_even_price=current_profit.break_even_price,
            discount_simulations=discount_simulations,
            strategy_tasks=tasks,
        )
