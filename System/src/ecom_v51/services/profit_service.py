from __future__ import annotations

from dataclasses import asdict

from ecom_v51.models import ProfitInput
from ecom_v51.profit_solver import ProfitSolver


class ProfitService:
    def __init__(self) -> None:
        self.solver = ProfitSolver()

    def default_case(self) -> ProfitInput:
        return ProfitInput(
            sale_price=119.0,
            list_price=129.0,
            variable_rate_total=0.31,
            fixed_cost_total=72.0,
        )

    def dashboard(self) -> dict[str, object]:
        payload = self.default_case()
        current = self.solver.solve_current(payload)
        discounts = self.solver.simulate_discounts(payload, [0.95, 0.9, 0.85])
        return {
            "input": asdict(payload),
            "current": asdict(current),
            "discounts": [asdict(x) for x in discounts],
        }

    def solve(
        self,
        *,
        mode: str,
        target_value: float,
        sale_price: float,
        list_price: float,
        variable_rate_total: float,
        fixed_cost_total: float,
    ) -> dict[str, object]:
        payload = ProfitInput(
            sale_price=sale_price,
            list_price=list_price,
            variable_rate_total=variable_rate_total,
            fixed_cost_total=fixed_cost_total,
        )
        current = self.solver.solve_current(payload)

        if mode == "target_profit":
            suggested_price = self.solver.target_profit_price(target_value, variable_rate_total, fixed_cost_total)
        elif mode == "target_margin":
            suggested_price = self.solver.target_margin_price(target_value, variable_rate_total, fixed_cost_total)
        elif mode == "target_roi":
            suggested_price = self.solver.target_roi_price(target_value, variable_rate_total, fixed_cost_total)
        else:
            raise ValueError("unsupported solve mode")

        simulate_payload = ProfitInput(
            sale_price=suggested_price,
            list_price=list_price,
            variable_rate_total=variable_rate_total,
            fixed_cost_total=fixed_cost_total,
        )
        suggested_result = self.solver.solve_current(simulate_payload)
        return {
            "input": asdict(payload),
            "current": asdict(current),
            "mode": mode,
            "target_value": target_value,
            "suggested_price": round(suggested_price, 4),
            "suggested_result": asdict(suggested_result),
            "discounts": [
                asdict(x)
                for x in self.solver.simulate_discounts(payload, [0.95, 0.9, 0.85, 0.8])
            ],
        }
