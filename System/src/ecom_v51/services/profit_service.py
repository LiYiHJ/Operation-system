from __future__ import annotations

from dataclasses import asdict
from copy import deepcopy
from datetime import date, datetime

from ecom_v51.db.models import ReportSnapshot
from ecom_v51.db.session import get_session
from ecom_v51.models import ProfitInput
from ecom_v51.profit_solver import ProfitSolver


class ProfitService:
    def __init__(self) -> None:
        self.solver = ProfitSolver()

    def get_profiles(self) -> list[dict[str, object]]:
        return [
            {'id': 'ozon_daily_profit', 'name': 'Ozon 日常利润模型', 'mode': 'daily'},
            {'id': 'ozon_campaign_profit', 'name': 'Ozon 平台活动利润模型', 'mode': 'campaign'},
            {'id': 'ozon_custom_promo_profit', 'name': 'Ozon 自建促销利润模型', 'mode': 'custom_promo'},
            {'id': 'target_margin_pricing', 'name': '目标利润率定价', 'mode': 'target_margin'},
            {'id': 'target_roi_pricing', 'name': '目标 ROI 定价', 'mode': 'target_roi'},
            {'id': 'custom_template', 'name': '自定义模板扩展位', 'mode': 'custom'},
        ]

    def get_default_params(self) -> dict[str, dict[str, float]]:
        return {
            'platform_auto': {
                'variable_rate_total': 0.31,
                'fixed_cost_total': 72.0,
            },
            'shop_default': {
                'variable_rate_total': 0.29,
                'fixed_cost_total': 69.0,
            },
            'sku_override': {},
            'simulation_override': {},
        }

    def _merge_layered_params(self, layers: dict | None) -> dict[str, float]:
        merged = {'sale_price': 119.0, 'list_price': 129.0, 'variable_rate_total': 0.31, 'fixed_cost_total': 72.0}
        base_layers = self.get_default_params()
        input_layers = layers or {}
        for key in ['platform_auto', 'shop_default', 'sku_override', 'simulation_override']:
            values = deepcopy(base_layers.get(key, {}))
            values.update(input_layers.get(key, {}) or {})
            merged.update(values)
        return merged

    def dashboard(self) -> dict[str, object]:
        payload = ProfitInput(**self._merge_layered_params(None))
        current = self.solver.solve_current(payload)
        discounts = self.solver.simulate_discounts(payload, [0.95, 0.9, 0.85])
        return {
            'input': asdict(payload),
            'current': asdict(current),
            'discounts': [asdict(x) for x in discounts],
            'profiles': self.get_profiles(),
        }

    @staticmethod
    def _build_risk_scan(result: dict[str, object], payload: ProfitInput) -> list[dict[str, str]]:
        net_margin = float(result.get('net_margin') or 0)
        is_loss = bool(result.get('is_loss'))
        variable_rate = float(payload.variable_rate_total)
        return [
            {
                'risk': '亏损风险',
                'level': '高' if is_loss else '低',
                'detail': '当前参数下净利润为负' if is_loss else '当前净利润为正',
            },
            {
                'risk': '高费率风险',
                'level': '中' if variable_rate > 0.4 else '低',
                'detail': f'变量费率 {round(variable_rate * 100, 2)}%',
            },
            {
                'risk': '低毛利风险',
                'level': '中' if net_margin < 0.1 else '低',
                'detail': f'净利率 {round(net_margin * 100, 2)}%',
            },
        ]

    def simulate_matrix(
        self,
        *,
        sale_price: float,
        list_price: float,
        variable_rate_total: float,
        fixed_cost_total: float,
        algorithm_profile: str = 'ozon_daily_profit',
        layered_params: dict | None = None,
        discount_ratios: list[float] | None = None,
        scenarios: list[dict] | None = None,
    ) -> dict[str, object]:
        merged = self._merge_layered_params(layered_params)
        payload = ProfitInput(
            sale_price=sale_price or merged['sale_price'],
            list_price=list_price or merged['list_price'],
            variable_rate_total=variable_rate_total or merged['variable_rate_total'],
            fixed_cost_total=fixed_cost_total or merged['fixed_cost_total'],
        )
        current = self.solver.solve_current(payload)
        ratios = [float(x) for x in (discount_ratios or [1.0, 0.95, 0.9, 0.85, 0.8])]
        ratio_set = []
        for ratio in ratios:
            if ratio <= 0:
                continue
            ratio_set.append(ratio)
        if 1.0 not in ratio_set:
            ratio_set.insert(0, 1.0)
        discount_rows = [asdict(x) for x in self.solver.simulate_discounts(payload, ratio_set)]

        scenario_rows = []
        for item in scenarios or []:
            name = str(item.get('name') or '场景')
            layer = item.get('layered_params') or {}
            params = self._merge_layered_params(layer)
            scenario_payload = ProfitInput(
                sale_price=float(params.get('sale_price', payload.sale_price)),
                list_price=float(params.get('list_price', payload.list_price)),
                variable_rate_total=float(params.get('variable_rate_total', payload.variable_rate_total)),
                fixed_cost_total=float(params.get('fixed_cost_total', payload.fixed_cost_total)),
            )
            scenario_rows.append({'name': name, 'input': asdict(scenario_payload), 'result': asdict(self.solver.solve_current(scenario_payload))})

        break_even_price = float(current.break_even_price)
        safety_floor_price = round(break_even_price * 1.05, 4)
        target_margin_floor_price = round(self.solver.target_margin_price(0.1, payload.variable_rate_total, payload.fixed_cost_total), 4)
        return {
            'algorithm_profile': algorithm_profile,
            'input': asdict(payload),
            'current': asdict(current),
            'discountScenarios': discount_rows,
            'customScenarios': scenario_rows,
            'pricingGuardrails': {
                'breakEvenPrice': round(break_even_price, 4),
                'safetyFloorPrice': safety_floor_price,
                'targetMargin10Price': target_margin_floor_price,
            },
            'riskScan': self._build_risk_scan(asdict(current), payload),
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
        algorithm_profile: str = 'ozon_daily_profit',
        layered_params: dict | None = None,
        scenarios: list[dict] | None = None,
    ) -> dict[str, object]:
        merged = self._merge_layered_params(layered_params)
        payload = ProfitInput(
            sale_price=sale_price or merged['sale_price'],
            list_price=list_price or merged['list_price'],
            variable_rate_total=variable_rate_total or merged['variable_rate_total'],
            fixed_cost_total=fixed_cost_total or merged['fixed_cost_total'],
        )
        current = self.solver.solve_current(payload)

        if mode == 'target_profit':
            suggested_price = self.solver.target_profit_price(target_value, payload.variable_rate_total, payload.fixed_cost_total)
        elif mode == 'target_margin':
            suggested_price = self.solver.target_margin_price(target_value, payload.variable_rate_total, payload.fixed_cost_total)
        elif mode == 'target_roi':
            suggested_price = self.solver.target_roi_price(target_value, payload.variable_rate_total, payload.fixed_cost_total)
        else:
            suggested_price = payload.sale_price

        suggested_result = self.solver.solve_current(
            ProfitInput(
                sale_price=suggested_price,
                list_price=payload.list_price,
                variable_rate_total=payload.variable_rate_total,
                fixed_cost_total=payload.fixed_cost_total,
            )
        )

        scenario_results = []
        for item in scenarios or []:
            name = item.get('name', '场景')
            layer = item.get('layered_params', {})
            params = self._merge_layered_params(layer)
            scenario_payload = ProfitInput(
                sale_price=float(params.get('sale_price', payload.sale_price)),
                list_price=float(params.get('list_price', payload.list_price)),
                variable_rate_total=float(params.get('variable_rate_total', payload.variable_rate_total)),
                fixed_cost_total=float(params.get('fixed_cost_total', payload.fixed_cost_total)),
            )
            scenario_results.append({'name': name, 'result': asdict(self.solver.solve_current(scenario_payload))})

        current_dict = asdict(current)
        return {
            'algorithm_profile': algorithm_profile,
            'layered_params': layered_params or self.get_default_params(),
            'input': asdict(payload),
            'current': current_dict,
            'mode': mode,
            'target_value': target_value,
            'suggested_price': round(suggested_price, 4),
            'suggested_result': asdict(suggested_result),
            'discounts': [asdict(x) for x in self.solver.simulate_discounts(payload, [0.95, 0.9, 0.85, 0.8])],
            'scenario_results': scenario_results,
            'riskScan': self._build_risk_scan(current_dict, payload),
        }

    def save_snapshot(
        self,
        *,
        shop_id: int,
        snapshot_name: str,
        algorithm_profile: str,
        payload: dict,
        result: dict,
        operator: str,
    ) -> dict[str, object]:
        now = datetime.utcnow()
        with get_session() as session:
            snapshot = ReportSnapshot(
                shop_id=shop_id,
                report_type='profit_snapshot',
                report_date=date.today(),
                content_md=snapshot_name,
                content_json={
                    'snapshot_name': snapshot_name,
                    'algorithm_profile': algorithm_profile,
                    'payload': payload,
                    'result': result,
                    'operator': operator,
                },
                generated_at=now,
            )
            session.add(snapshot)
            session.flush()
            return {
                'snapshotId': snapshot.id,
                'snapshotName': snapshot_name,
                'savedAt': snapshot.generated_at.isoformat() if snapshot.generated_at else None,
            }

    def list_snapshots(self, *, shop_id: int, limit: int = 20) -> list[dict[str, object]]:
        with get_session() as session:
            rows = (
                session.query(ReportSnapshot)
                .filter(ReportSnapshot.shop_id == shop_id, ReportSnapshot.report_type == 'profit_snapshot')
                .order_by(ReportSnapshot.generated_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    'snapshotId': r.id,
                    'snapshotName': (r.content_json or {}).get('snapshot_name') or r.content_md or f'快照#{r.id}',
                    'algorithmProfile': (r.content_json or {}).get('algorithm_profile'),
                    'savedAt': r.generated_at.isoformat() if r.generated_at else None,
                }
                for r in rows
            ]

    def save_template(
        self,
        *,
        shop_id: int,
        template_name: str,
        algorithm_profile: str,
        layered_params: dict,
        scenarios: list[dict],
        operator: str,
    ) -> dict[str, object]:
        now = datetime.utcnow()
        with get_session() as session:
            template = ReportSnapshot(
                shop_id=shop_id,
                report_type='profit_template',
                report_date=date.today(),
                content_md=template_name,
                content_json={
                    'template_name': template_name,
                    'algorithm_profile': algorithm_profile,
                    'layered_params': layered_params,
                    'scenarios': scenarios,
                    'operator': operator,
                },
                generated_at=now,
            )
            session.add(template)
            session.flush()
            return {
                'templateId': template.id,
                'templateName': template_name,
                'savedAt': template.generated_at.isoformat() if template.generated_at else None,
            }

    def list_templates(self, *, shop_id: int, limit: int = 20) -> list[dict[str, object]]:
        with get_session() as session:
            rows = (
                session.query(ReportSnapshot)
                .filter(ReportSnapshot.shop_id == shop_id, ReportSnapshot.report_type == 'profit_template')
                .order_by(ReportSnapshot.generated_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    'templateId': r.id,
                    'templateName': (r.content_json or {}).get('template_name') or r.content_md or f'模板#{r.id}',
                    'algorithmProfile': (r.content_json or {}).get('algorithm_profile'),
                    'layeredParams': (r.content_json or {}).get('layered_params') or {},
                    'scenarios': (r.content_json or {}).get('scenarios') or [],
                    'savedAt': r.generated_at.isoformat() if r.generated_at else None,
                }
                for r in rows
            ]
