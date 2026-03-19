from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(".")
CONFIG_DIR = ROOT / "config"


COST_COMPONENT_REGISTRY = {
    "version": "p0-v1",
    "components": [
        {
            "code": "purchase_cost",
            "label": "采购成本",
            "allocLevel": "sku",
            "sourceMode": ["manual", "import", "rule"],
            "requiredPhase": "P1",
            "mutable": True,
        },
        {
            "code": "packaging_cost",
            "label": "包装成本",
            "allocLevel": "sku",
            "sourceMode": ["manual", "rule"],
            "requiredPhase": "P1",
            "mutable": True,
        },
        {
            "code": "first_mile_cost",
            "label": "头程成本",
            "allocLevel": "sku",
            "sourceMode": ["manual", "import", "rule"],
            "requiredPhase": "P1",
            "mutable": True,
        },
        {
            "code": "landed_cost",
            "label": "落地成本",
            "allocLevel": "sku",
            "sourceMode": ["manual", "import", "rule"],
            "requiredPhase": "P1",
            "mutable": True,
        },
        {
            "code": "platform_commission",
            "label": "平台佣金",
            "allocLevel": "order_line",
            "sourceMode": ["api", "import", "rule"],
            "requiredPhase": "P1",
            "mutable": False,
        },
        {
            "code": "payment_fee",
            "label": "支付费",
            "allocLevel": "order_line",
            "sourceMode": ["api", "import", "rule"],
            "requiredPhase": "P1",
            "mutable": False,
        },
        {
            "code": "fulfillment_cost",
            "label": "履约成本",
            "allocLevel": "order_line",
            "sourceMode": ["api", "import", "rule", "manual"],
            "requiredPhase": "P1",
            "mutable": True,
        },
        {
            "code": "ad_cost",
            "label": "广告成本",
            "allocLevel": "sku",
            "sourceMode": ["api", "import"],
            "requiredPhase": "P1",
            "mutable": False,
        },
        {
            "code": "refund_reserve",
            "label": "退款/售后准备",
            "allocLevel": "sku",
            "sourceMode": ["rule", "manual"],
            "requiredPhase": "P3",
            "mutable": True,
        },
        {
            "code": "rating_risk_reserve",
            "label": "评分风险准备",
            "allocLevel": "sku",
            "sourceMode": ["rule", "manual"],
            "requiredPhase": "P3",
            "mutable": True,
        },
        {
            "code": "inventory_risk_reserve",
            "label": "库存风险准备",
            "allocLevel": "sku",
            "sourceMode": ["rule", "manual"],
            "requiredPhase": "P3",
            "mutable": True,
        },
        {
            "code": "fx_risk_reserve",
            "label": "汇率风险准备",
            "allocLevel": "shop",
            "sourceMode": ["rule", "manual"],
            "requiredPhase": "P3",
            "mutable": True,
        },
    ],
}

PROFIT_METRIC_REGISTRY = {
    "version": "p0-v1",
    "metrics": [
        {
            "code": "gross_revenue",
            "label": "毛收入",
            "phase": "P1",
            "strategyConsumable": True,
            "dependsOn": ["order_amount"],
        },
        {
            "code": "net_revenue",
            "label": "净收入",
            "phase": "P1",
            "strategyConsumable": True,
            "dependsOn": ["gross_revenue", "refund_reserve"],
        },
        {
            "code": "base_contribution_profit",
            "label": "基础贡献利润",
            "phase": "P1",
            "strategyConsumable": True,
            "dependsOn": [
                "gross_revenue",
                "landed_cost",
                "platform_commission",
                "payment_fee",
                "fulfillment_cost",
            ],
        },
        {
            "code": "profit_after_ads",
            "label": "广告后利润",
            "phase": "P1",
            "strategyConsumable": True,
            "dependsOn": ["base_contribution_profit", "ad_cost"],
        },
        {
            "code": "risk_adjusted_profit",
            "label": "风险调整后利润",
            "phase": "P3",
            "strategyConsumable": True,
            "dependsOn": [
                "profit_after_ads",
                "refund_reserve",
                "rating_risk_reserve",
                "inventory_risk_reserve",
                "fx_risk_reserve",
            ],
        },
        {
            "code": "profit_margin_base",
            "label": "基础利润率",
            "phase": "P1",
            "strategyConsumable": True,
            "dependsOn": ["base_contribution_profit", "gross_revenue"],
        },
        {
            "code": "profit_margin_after_ads",
            "label": "广告后利润率",
            "phase": "P1",
            "strategyConsumable": True,
            "dependsOn": ["profit_after_ads", "gross_revenue"],
        },
        {
            "code": "profit_margin_risk_adjusted",
            "label": "风险调整后利润率",
            "phase": "P3",
            "strategyConsumable": True,
            "dependsOn": ["risk_adjusted_profit", "gross_revenue"],
        },
        {
            "code": "profit_band",
            "label": "利润档位",
            "phase": "P2",
            "strategyConsumable": True,
            "dependsOn": ["profit_margin_after_ads", "risk_adjusted_profit"],
        },
    ],
    "pricingFields": [
        {"code": "floor_price", "label": "底价", "phase": "P1"},
        {"code": "target_price", "label": "目标价", "phase": "P1"},
        {"code": "ceiling_price", "label": "上限价", "phase": "P1"},
    ],
}


def _dump(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main() -> None:
    _dump(CONFIG_DIR / "cost_component_registry.json", COST_COMPONENT_REGISTRY)
    _dump(CONFIG_DIR / "profit_metric_registry.json", PROFIT_METRIC_REGISTRY)
    print("written:", CONFIG_DIR / "cost_component_registry.json")
    print("written:", CONFIG_DIR / "profit_metric_registry.json")


if __name__ == "__main__":
    main()
