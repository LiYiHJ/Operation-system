#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
"""
利润引擎 P1：registry bridge patch
"""

from pathlib import Path
import re
import shutil
import sys

ROOT = Path.cwd()

def fail(msg: str) -> None:
    print(msg)
    sys.exit(1)

def backup(path: Path) -> None:
    bak = path.with_suffix(path.suffix + ".bak_profit_registry_bridge_v1")
    if not bak.exists():
        shutil.copy2(path, bak)

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")

SERVICE_FILE_CONTENT = '''from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


class ProfitRegistryService:
    """读取利润引擎 registry 的轻量服务。"""

    def __init__(self, root_dir: str | Path | None = None) -> None:
        current = Path(root_dir) if root_dir else Path(__file__).resolve().parents[3]
        self.root_dir = current
        self.config_dir = self.root_dir / "config"
        self.cost_registry_path = self.config_dir / "cost_component_registry.json"
        self.metric_registry_path = self.config_dir / "profit_metric_registry.json"

    def _read_json(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"registry 文件不存在: {path}")
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def get_cost_component_registry(self) -> Dict[str, Any]:
        data = self._read_json(self.cost_registry_path)
        components = data.get("components") or []
        return {
            "version": data.get("version"),
            "count": len(components),
            "components": components,
        }

    def get_profit_metric_registry(self) -> Dict[str, Any]:
        data = self._read_json(self.metric_registry_path)
        metrics = data.get("metrics") or []
        pricing_fields = data.get("pricingFields") or []
        return {
            "version": data.get("version"),
            "metricCount": len(metrics),
            "pricingFieldCount": len(pricing_fields),
            "metrics": metrics,
            "pricingFields": pricing_fields,
        }

    def get_registry_summary(self) -> Dict[str, Any]:
        cost = self.get_cost_component_registry()
        metric = self.get_profit_metric_registry()

        return {
            "costRegistryVersion": cost.get("version"),
            "metricRegistryVersion": metric.get("version"),
            "costComponentCount": cost.get("count", 0),
            "metricCount": metric.get("metricCount", 0),
            "pricingFieldCount": metric.get("pricingFieldCount", 0),
            "strategyConsumableMetrics": [
                item.get("code")
                for item in (metric.get("metrics") or [])
                if item.get("strategyConsumable")
            ],
            "phaseBuckets": {
                "costComponents": _group_by_phase(cost.get("components") or [], "requiredPhase"),
                "metrics": _group_by_phase(metric.get("metrics") or [], "phase"),
                "pricingFields": _group_by_phase(metric.get("pricingFields") or [], "phase"),
            },
        }


def _group_by_phase(items: List[Dict[str, Any]], key: str) -> Dict[str, int]:
    result: Dict[str, int] = {}
    for item in items:
        phase = str(item.get(key) or "UNKNOWN")
        result[phase] = result.get(phase, 0) + 1
    return result
'''

TYPES_ADDITION = """
export interface CostComponentDefinition {
  code: string
  label: string
  allocLevel: 'order' | 'order_line' | 'sku' | 'shop'
  sourceMode: Array<'api' | 'import' | 'rule' | 'manual'>
  requiredPhase: 'P0' | 'P1' | 'P2' | 'P3' | 'P4'
  mutable: boolean
}

export interface ProfitMetricDefinition {
  code: string
  label: string
  phase: 'P0' | 'P1' | 'P2' | 'P3' | 'P4'
  strategyConsumable?: boolean
  dependsOn?: string[]
}

export interface PricingFieldDefinition {
  code: 'floor_price' | 'target_price' | 'ceiling_price'
  label: string
  phase: 'P0' | 'P1' | 'P2' | 'P3' | 'P4'
}

export interface CostComponentRegistryResponse {
  version: string
  count: number
  components: CostComponentDefinition[]
}

export interface ProfitMetricRegistryResponse {
  version: string
  metricCount: number
  pricingFieldCount: number
  metrics: ProfitMetricDefinition[]
  pricingFields: PricingFieldDefinition[]
}

export interface ProfitRegistrySummary {
  costRegistryVersion?: string
  metricRegistryVersion?: string
  costComponentCount: number
  metricCount: number
  pricingFieldCount: number
  strategyConsumableMetrics: string[]
  phaseBuckets: {
    costComponents: Record<string, number>
    metrics: Record<string, number>
    pricingFields: Record<string, number>
  }
}

// ========== Ads 相关类型 ==========
"""

ROUTE_ADDITION = '''

@profit_bp.route('/registry/cost-components', methods=['GET'])
def get_cost_component_registry():
    data = profit_registry_service.get_cost_component_registry()
    return jsonify({
        'success': True,
        'data': data,
    })


@profit_bp.route('/registry/metrics', methods=['GET'])
def get_profit_metric_registry():
    data = profit_registry_service.get_profit_metric_registry()
    return jsonify({
        'success': True,
        'data': data,
    })


@profit_bp.route('/registry/summary', methods=['GET'])
def get_profit_registry_summary():
    data = profit_registry_service.get_registry_summary()
    return jsonify({
        'success': True,
        'data': data,
    })
'''

def main() -> None:
    service_dir = ROOT / "src" / "ecom_v51" / "services"
    route_dir = ROOT / "src" / "ecom_v51" / "api" / "routes"
    frontend_types = ROOT / "frontend" / "src" / "types" / "index.ts"
    services_init = service_dir / "__init__.py"
    profit_route = route_dir / "profit.py"
    config_dir = ROOT / "config"

    for p in [frontend_types, services_init, profit_route]:
        if not p.exists():
            fail(f"缺少文件: {p}")
    if not (config_dir / "cost_component_registry.json").exists():
        fail("缺少 config/cost_component_registry.json，先确认 P0 补丁已落地")
    if not (config_dir / "profit_metric_registry.json").exists():
        fail("缺少 config/profit_metric_registry.json，先确认 P0 补丁已落地")

    registry_service_file = service_dir / "profit_registry_service.py"
    if not registry_service_file.exists():
        write_text(registry_service_file, SERVICE_FILE_CONTENT)

    text = read_text(services_init)
    backup(services_init)
    if "profit_registry_service import ProfitRegistryService" not in text:
        if "from .profit_service import ProfitService" in text:
            text = text.replace(
                "from .profit_service import ProfitService",
                "from .profit_service import ProfitService\nfrom .profit_registry_service import ProfitRegistryService",
            )
        else:
            text = text.rstrip() + "\nfrom .profit_registry_service import ProfitRegistryService\n"

    if "__all__" in text and "ProfitRegistryService" not in text:
        text = re.sub(
            r"(__all__\s*=\s*\[.*?)(\])",
            lambda m: m.group(1).rstrip() + ", 'ProfitRegistryService'" + m.group(2),
            text,
            flags=re.S,
        )
    write_text(services_init, text)

    route_text = read_text(profit_route)
    backup(profit_route)

    if "ProfitRegistryService" not in route_text:
        m = re.search(r"from ecom_v51\.services import\s*\((.*?)\)", route_text, flags=re.S)
        if m:
            inner = m.group(1).strip()
            replacement = f"from ecom_v51.services import ({inner}, ProfitRegistryService)"
            route_text = route_text[:m.start()] + replacement + route_text[m.end():]
        elif "from ecom_v51.services import" in route_text:
            route_text = route_text.replace(
                "from ecom_v51.services import",
                "from ecom_v51.services import ProfitRegistryService,",
                1,
            )
        else:
            fail("profit.py 中未找到 services import，未修改任何路由")

    if "profit_registry_service = ProfitRegistryService()" not in route_text:
        if "profit_service = ProfitService()" in route_text:
            route_text = route_text.replace(
                "profit_service = ProfitService()",
                "profit_service = ProfitService()\nprofit_registry_service = ProfitRegistryService()",
                1,
            )
        elif "service = ProfitService()" in route_text:
            route_text = route_text.replace(
                "service = ProfitService()",
                "service = ProfitService()\nprofit_registry_service = ProfitRegistryService()",
                1,
            )
        elif "profit_bp = Blueprint(" in route_text:
            route_text = route_text.replace(
                "profit_bp = Blueprint(",
                "profit_bp = Blueprint(",
                1,
            )
            route_text += "\nprofit_registry_service = ProfitRegistryService()\n"
        else:
            route_text = route_text.rstrip() + "\n\nprofit_registry_service = ProfitRegistryService()\n"

    if "/registry/cost-components" not in route_text:
        route_text = route_text.rstrip() + ROUTE_ADDITION
    write_text(profit_route, route_text)

    types_text = read_text(frontend_types)
    backup(frontend_types)
    marker = "// ========== Ads 相关类型 =========="
    if "export interface CostComponentRegistryResponse" not in types_text:
        if marker not in types_text:
            fail("frontend types 未找到 Ads 标记锚点，未修改 types")
        types_text = types_text.replace(marker, TYPES_ADDITION, 1)
        write_text(frontend_types, types_text)

    print("已完成利润引擎 P1 registry bridge 补丁")
    print("新增: src/ecom_v51/services/profit_registry_service.py")
    print("修改: src/ecom_v51/services/__init__.py")
    print("修改: src/ecom_v51/api/routes/profit.py")
    print("修改: frontend/src/types/index.ts")

if __name__ == "__main__":
    main()
