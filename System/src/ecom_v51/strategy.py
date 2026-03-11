from __future__ import annotations

from .models import StrategyTask


class StrategyEngine:
    def generate_for_sku(
        self,
        *,
        ctr: float,
        add_to_cart_rate: float,
        order_rate: float,
        net_margin: float,
        roas: float,
        days_of_supply: float,
        return_rate: float,
        rating: float,
    ) -> list[StrategyTask]:
        tasks: list[StrategyTask] = []

        if net_margin < 0:
            tasks.append(
                StrategyTask(
                    strategy_type="pricing",
                    level="sku",
                    priority="P0",
                    issue_summary="商品处于亏损状态",
                    recommended_action="使用目标净利润求解器反推售价，或降低固定成本后再促销",
                    observation_metrics=["net_profit", "net_margin", "break_even_price"],
                )
            )

        if ctr < 0.015:
            tasks.append(
                StrategyTask(
                    strategy_type="conversion",
                    level="sku",
                    priority="P1",
                    issue_summary="曝光到点击转化偏低",
                    recommended_action="优化首图与标题关键词，先修内容再加广告",
                    observation_metrics=["ctr", "card_visits"],
                )
            )

        if roas < 2.0:
            tasks.append(
                StrategyTask(
                    strategy_type="ads",
                    level="sku",
                    priority="P1",
                    issue_summary="广告效率低于阈值",
                    recommended_action="降投低效词并收敛投放，保留高转化词包",
                    observation_metrics=["roas", "ad_spend", "ad_revenue"],
                )
            )

        if days_of_supply < 7:
            tasks.append(
                StrategyTask(
                    strategy_type="inventory",
                    level="sku",
                    priority="P0",
                    issue_summary="缺货风险高",
                    recommended_action="进入补货池并锁定3-7天安全库存",
                    observation_metrics=["days_of_supply", "stock_total"],
                )
            )

        if return_rate > 0.15 or rating < 3.8:
            tasks.append(
                StrategyTask(
                    strategy_type="risk_control",
                    level="sku",
                    priority="P1",
                    issue_summary="售后风险偏高",
                    recommended_action="排查差评原因并修复描述偏差/质量问题",
                    observation_metrics=["return_rate", "rating"],
                )
            )

        if not tasks:
            tasks.append(
                StrategyTask(
                    strategy_type="pricing",
                    level="sku",
                    priority="P3",
                    issue_summary="核心指标稳定",
                    recommended_action="维持当前策略并按周复盘",
                    observation_metrics=["net_margin", "roas", "days_of_supply"],
                )
            )

        return tasks
