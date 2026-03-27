from __future__ import annotations

from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional

from ecom_v51.models import ProfitInput
from ecom_v51.profit_solver import ProfitSolver
from ecom_v51.services.economics_config_service import EconomicsConfigService
from ecom_v51.services.object_assembly_service import ObjectAssemblyService


class EconomicsIntakeService:
    CONTRACT_VERSION = 'p3.economics_intake.v1'
    CONSUMER_PRESET = 'economics_v1'

    def __init__(self, root_dir: Path, *, object_service: ObjectAssemblyService | None = None, config_service: EconomicsConfigService | None = None) -> None:
        self.root_dir = Path(root_dir)
        self.object_service = object_service or ObjectAssemblyService(self.root_dir)
        self._config_rebind_enabled = config_service is not None
        self.config_service = config_service or EconomicsConfigService(self.root_dir)
        self.profit_solver = ProfitSolver()

    @staticmethod
    def _clean_str(value: Any, default: str = '') -> str:
        text = str(value or '').strip()
        return text or default

    def _load_state(self, batch_ref: str) -> Optional[Dict[str, Any]]:
        return self.object_service._load_batch_object_state(batch_ref)

    def _normalize_view(self, view: str | None) -> str:
        return self.object_service._normalize_fact_view(view)

    def _paginate_rows(self, rows: list[Dict[str, Any]], *, offset: int, limit: int) -> tuple[list[Dict[str, Any]], dict[str, Any]]:
        return self.object_service._paginate_rows(rows, offset=offset, limit=limit)

    def _build_contract(self, batch_id: int) -> Dict[str, Any]:
        source_contract = self.object_service._build_fact_contract(batch_id)
        return {
            'contractName': 'economics_intake_skeleton',
            'contractVersion': self.CONTRACT_VERSION,
            'sourceContractName': source_contract['contractName'],
            'sourcePreset': self.CONSUMER_PRESET,
            'defaultView': 'ready',
            'availableViews': ['all', 'ready', 'issues'],
            'primaryKeyFields': ['factDate', 'shopId', 'canonicalSku', 'currencyCode', 'providerCode', 'unresolvedReason'],
            'dimensionFields': ['factDate', 'shopId', 'skuId', 'canonicalSku', 'currencyCode', 'providerCode'],
            'measureFields': [
                'orderedQty',
                'deliveredQty',
                'returnedQty',
                'cancelledQtyEstimated',
                'orderedAmount',
                'deliveredAmountEstimated',
                'discountAmount',
                'refundAmount',
                'platformFeeAmount',
                'fulfillmentFeeAmount',
                'netSalesAmount',
            ],
            'qualityFields': ['factReady', 'unresolvedReason', 'identityConfidenceBucket', 'identityConfidence'],
            'economicsFields': ['costCoverageState', 'economicsReady', 'economicsBlockers'],
            'readinessRules': {
                'factReadyField': 'factReady',
                'economicsReadyField': 'economicsReady',
                'economicsReadyRequires': ['factReady', 'cost_card_attached'],
            },
            'exportFileStem': f'batch_{batch_id}_economics_intake',
        }

    def _build_intake_rows(self, state: Dict[str, Any]) -> Dict[str, Any]:
        fact_model = self.object_service._build_fact_read_model(state)
        out_rows: list[Dict[str, Any]] = []
        for row in fact_model['rows']:
            item = dict(row)
            blockers: list[str] = []
            if item.get('unresolvedReason'):
                blockers.append(str(item['unresolvedReason']))
            blockers.append('missing_cost_card')
            item['costCoverageState'] = 'missing_cost_card'
            item['economicsReady'] = False
            item['economicsBlockers'] = blockers
            out_rows.append(item)
        return {'rows': out_rows, 'factReadiness': fact_model['readiness']}

    def _build_issue_buckets(self, rows: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        counter = Counter()
        for row in rows:
            blockers = list(row.get('economicsBlockers') or [])
            if not blockers:
                counter['resolved'] += 1
                continue
            for blocker in blockers:
                counter[self._clean_str(blocker, 'unknown')] += 1
        return [
            {'reason': reason, 'rowCount': count}
            for reason, count in sorted(counter.items(), key=lambda item: item[0])
        ]

    def _build_dimension_summary(self, rows: list[Dict[str, Any]]) -> Dict[str, Any]:
        fact_dates = [row.get('factDate') for row in rows if row.get('factDate')]
        return {
            'shopIdCount': len({row.get('shopId') for row in rows if row.get('shopId') is not None}),
            'providerCodeCount': len({row.get('providerCode') for row in rows if row.get('providerCode')}),
            'currencyCodeCount': len({row.get('currencyCode') for row in rows if row.get('currencyCode')}),
            'factDateRange': {
                'min': min(fact_dates) if fact_dates else None,
                'max': max(fact_dates) if fact_dates else None,
            },
        }

    def _build_intake_summary(self, rows: list[Dict[str, Any]], *, fact_readiness: Dict[str, Any]) -> Dict[str, Any]:
        total_rows = len(rows)
        economics_ready_count = sum(1 for row in rows if row.get('economicsReady') is True)
        missing_cost_count = sum(1 for row in rows if row.get('costCoverageState') == 'missing_cost_card')
        return {
            'sourceFactRowCount': total_rows,
            'factReadyRowCount': sum(1 for row in rows if row.get('factReady') is True),
            'economicsReadyRowCount': economics_ready_count,
            'blockedRowCount': total_rows - economics_ready_count,
            'factReadyRate': round((sum(1 for row in rows if row.get('factReady') is True) / total_rows) if total_rows else 0.0, 4),
            'economicsReadyRate': round((economics_ready_count / total_rows) if total_rows else 0.0, 4),
            'missingCostCardRowCount': missing_cost_count,
            'netSalesAmountTotal': round(sum(float(row.get('netSalesAmount') or 0.0) for row in rows), 4),
            'deliveredAmountEstimatedTotal': round(sum(float(row.get('deliveredAmountEstimated') or 0.0) for row in rows), 4),
            'platformFeeAmountTotal': round(sum(float(row.get('platformFeeAmount') or 0.0) for row in rows), 4),
            'fulfillmentFeeAmountTotal': round(sum(float(row.get('fulfillmentFeeAmount') or 0.0) for row in rows), 4),
            'refundAmountTotal': round(sum(float(row.get('refundAmount') or 0.0) for row in rows), 4),
            'discountAmountTotal': round(sum(float(row.get('discountAmount') or 0.0) for row in rows), 4),
            'factReadiness': dict(fact_readiness),
        }

    def _project_rows(self, rows: list[Dict[str, Any]]) -> tuple[list[Dict[str, Any]], list[str]]:
        projected, column_order = self.object_service._project_fact_rows(rows, preset=self.CONSUMER_PRESET)
        column_order = list(column_order or [])
        column_order.extend(['costCoverageState', 'economicsReady', 'economicsBlockers'])
        result = []
        for source, original in zip(projected, rows):
            item = dict(source)
            item['costCoverageState'] = original.get('costCoverageState')
            item['economicsReady'] = original.get('economicsReady')
            item['economicsBlockers'] = list(original.get('economicsBlockers') or [])
            result.append(item)
        return result, column_order

    def _build_core_contract(self, batch_id: int) -> Dict[str, Any]:
        intake_contract = self._build_contract(batch_id)
        contract_version = 'p4.economics_core_rebind.v1' if self._config_rebind_enabled else 'p3.economics_core.v1'
        return {
            'contractName': 'economics_core_minimal_margin',
            'contractVersion': contract_version,
            'sourceContractName': intake_contract['sourceContractName'] if 'sourceContractName' in intake_contract else intake_contract['contractName'],
            'sourcePreset': self.CONSUMER_PRESET,
            'defaultView': 'all',
            'availableViews': ['all', 'ready', 'issues'],
            'dimensionFields': ['factDate', 'shopId', 'skuId', 'canonicalSku', 'currencyCode', 'providerCode'],
            'inputMeasureFields': ['netSalesAmount', 'platformFeeAmount', 'fulfillmentFeeAmount'],
            'configBindingFields': ['resolvedProfileCode', 'coreBindingMode', 'resolvedVariableCostAmount', 'fallbackVariableCostAmount', 'resolvedComponentTotals'],
            'derivedMeasureFields': ['variableCostAmount', 'grossProfitAmount', 'grossMarginRate'],
            'qualityFields': ['factReady', 'costCoverageState', 'economicsBlockers', 'coreReady', 'coreCalculationState'],
            'readinessRules': {
                'coreReadyField': 'coreReady',
                'coreReadyRequires': ['factReady'],
                'bindingPolicy': 'prefer_config_resolve_then_fallback_to_import_partial_costs' if self._config_rebind_enabled else 'import_partial_costs_only',
            },
            'exportFileStem': f'batch_{batch_id}_economics_core',
        }

    @staticmethod
    def _build_core_key(row: Dict[str, Any]) -> tuple[Any, ...]:
        return (
            row.get('factDate'),
            row.get('shopId'),
            row.get('skuId'),
            row.get('canonicalSku'),
            row.get('currencyCode'),
            row.get('providerCode'),
        )

    @staticmethod
    def _sum_resolved_components(resolve_row: Dict[str, Any]) -> tuple[float, Dict[str, float]]:
        totals: Dict[str, float] = {}
        total = 0.0
        for component in list(resolve_row.get('resolvedComponents') or []):
            if component.get('coverageState') != 'covered':
                continue
            code = str(component.get('componentCode') or '').strip()
            value = round(float(component.get('value') or 0.0), 4)
            totals[code] = value
            total += value
        return round(total, 4), totals

    def _build_core_rows(self, state: Dict[str, Any], *, batch_ref: str) -> Dict[str, Any]:
        intake_model = self._build_intake_rows(state)
        resolve_state = self.config_service.get_batch_config_resolve(batch_ref, limit=1000, offset=0, view='all')
        resolve_map = {
            self._build_core_key(item): dict(item)
            for item in list((resolve_state or {}).get('items') or [])
        }
        rows: list[Dict[str, Any]] = []
        for row in intake_model['rows']:
            item = dict(row)
            fallback_variable_cost = round(float(item.get('platformFeeAmount') or 0.0) + float(item.get('fulfillmentFeeAmount') or 0.0), 4)
            resolve_row = resolve_map.get(self._build_core_key(item))
            resolved_variable_cost = None
            resolved_component_totals: Dict[str, float] = {}
            resolved_profile_code = None
            if resolve_row:
                resolved_variable_cost, resolved_component_totals = self._sum_resolved_components(resolve_row)
                resolved_profile_code = resolve_row.get('profileCode')
            use_config = bool(resolve_row and resolve_row.get('configReady') is True)
            variable_cost_amount = resolved_variable_cost if use_config and resolved_variable_cost is not None else fallback_variable_cost
            gross_profit_amount = round(float(item.get('netSalesAmount') or 0.0) - float(variable_cost_amount or 0.0), 4)
            net_sales_amount = float(item.get('netSalesAmount') or 0.0)
            gross_margin_rate = round((gross_profit_amount / net_sales_amount), 4) if net_sales_amount else None
            core_ready = bool(item.get('factReady') is True)
            item['resolvedProfileCode'] = resolved_profile_code
            item['resolvedVariableCostAmount'] = resolved_variable_cost
            item['fallbackVariableCostAmount'] = fallback_variable_cost
            item['resolvedComponentTotals'] = deepcopy(resolved_component_totals)
            item['coreBindingMode'] = 'config_resolve' if use_config else 'import_partial_fallback'
            item['variableCostAmount'] = round(float(variable_cost_amount or 0.0), 4)
            item['grossProfitAmount'] = gross_profit_amount
            item['grossMarginRate'] = gross_margin_rate
            item['coreReady'] = core_ready
            if use_config:
                item['coreCalculationState'] = 'calculated_config_bound_partial_costs'
            elif self._config_rebind_enabled:
                item['coreCalculationState'] = 'calculated_import_fallback_partial_costs'
            else:
                item['coreCalculationState'] = 'calculated_partial_costs' if core_ready else 'blocked_fact_quality'
            rows.append(item)
        readiness = {
            'coreRowCount': len(rows),
            'coreReadyRowCount': sum(1 for row in rows if row.get('coreReady') is True),
            'blockedCoreRowCount': sum(1 for row in rows if row.get('coreReady') is not True),
            'configBoundRowCount': sum(1 for row in rows if row.get('coreBindingMode') == 'config_resolve'),
            'fallbackRowCount': sum(1 for row in rows if row.get('coreBindingMode') == 'import_partial_fallback'),
        }
        readiness['coreReadyRate'] = round((readiness['coreReadyRowCount'] / readiness['coreRowCount']) if readiness['coreRowCount'] else 0.0, 4)
        readiness['configBoundRate'] = round((readiness['configBoundRowCount'] / readiness['coreRowCount']) if readiness['coreRowCount'] else 0.0, 4)
        return {'rows': rows, 'factReadiness': intake_model['factReadiness'], 'coreReadiness': readiness}

    def _project_core_rows(self, rows: list[Dict[str, Any]]) -> tuple[list[Dict[str, Any]], list[str]]:
        column_order = [
            'factDate', 'shopId', 'skuId', 'canonicalSku', 'currencyCode', 'providerCode',
            'netSalesAmount', 'platformFeeAmount', 'fulfillmentFeeAmount',
            'resolvedProfileCode', 'coreBindingMode', 'resolvedVariableCostAmount', 'fallbackVariableCostAmount', 'resolvedComponentTotals',
            'variableCostAmount', 'grossProfitAmount', 'grossMarginRate',
            'factReady', 'costCoverageState', 'economicsBlockers', 'coreReady', 'coreCalculationState',
        ]
        projected = []
        for row in rows:
            projected.append({field: row.get(field) for field in column_order})
        return projected, column_order

    def _build_core_summary(self, rows: list[Dict[str, Any]], *, core_readiness: Dict[str, Any]) -> Dict[str, Any]:
        total_rows = len(rows)
        revenue_amount_total = round(sum(float(row.get('netSalesAmount') or 0.0) for row in rows), 4)
        variable_cost_total = round(sum(float(row.get('variableCostAmount') or 0.0) for row in rows), 4)
        gross_profit_total = round(sum(float(row.get('grossProfitAmount') or 0.0) for row in rows), 4)
        return {
            'rowCount': total_rows,
            'coreReadyRowCount': core_readiness['coreReadyRowCount'],
            'blockedRowCount': total_rows - core_readiness['coreReadyRowCount'],
            'configBoundRowCount': core_readiness.get('configBoundRowCount', 0),
            'fallbackRowCount': core_readiness.get('fallbackRowCount', 0),
            'revenueAmountTotal': revenue_amount_total,
            'variableCostAmountTotal': variable_cost_total,
            'grossProfitAmountTotal': gross_profit_total,
            'grossMarginRate': round((gross_profit_total / revenue_amount_total) if revenue_amount_total else 0.0, 4),
        }

    def _build_cost_coverage_summary(self, rows: list[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            'missingCostCardRowCount': sum(1 for row in rows if row.get('costCoverageState') == 'missing_cost_card'),
            'configBoundRowCount': sum(1 for row in rows if row.get('coreBindingMode') == 'config_resolve'),
            'fallbackImportRowCount': sum(1 for row in rows if row.get('coreBindingMode') == 'import_partial_fallback'),
            'blockedByFactIssuesRowCount': sum(1 for row in rows if row.get('factReady') is not True),
        }


    def _build_profit_solve_contract(self, batch_id: int) -> Dict[str, Any]:
        return {
            'contractName': 'economics_profit_solve',
            'contractVersion': 'p4.profit_solve.v1',
            'defaultView': 'all',
            'availableViews': ['all', 'ready', 'issues'],
            'sourcePreset': self.CONSUMER_PRESET,
            'dimensionFields': ['factDate', 'shopId', 'skuId', 'canonicalSku', 'currencyCode', 'providerCode'],
            'inputFields': ['netSalesAmount', 'platformFeeAmount', 'fulfillmentFeeAmount', 'resolvedComponentTotals', 'resolvedProfileCode'],
            'layerFields': ['baseContributionProfit', 'profitAfterAds', 'riskAdjustedProfit'],
            'qualityFields': ['solveReady', 'solveState', 'profitConfidence', 'dominantCostComponent', 'dominantRiskDriver'],
            'notes': [
                '当前 GET /api/v1/economics/batches/{batch_ref}/solve 只冻结为 batch historical solve 读面，不是正式场景求解 API。',
                '本轮只做 profit solve skeleton，不做 full P&L。',
                '仍不做 pricing recommendation / break-even / snapshot save。',
                '优先消费 resolve + core 结果；config 不齐时允许 import fallback。',
                '正式场景求解留给后续 POST /api/v1/economics/profit/solve。',
            ],
            'exportFileStem': f'batch_{batch_id}_profit_solve',
        }

    @staticmethod
    def _pick_dominant_cost_component(component_amounts: Dict[str, float]) -> tuple[str | None, float]:
        if not component_amounts:
            return None, 0.0
        code, amount = max(component_amounts.items(), key=lambda item: (float(item[1] or 0.0), item[0]))
        return code, round(float(amount or 0.0), 4)

    @staticmethod
    def _estimate_profit_confidence(row: Dict[str, Any]) -> float:
        if row.get('coreReady') is not True:
            return 0.0
        identity_confidence = float(row.get('identityConfidence') or 0.0)
        if row.get('coreBindingMode') == 'config_resolve':
            return round(min(0.95, max(0.75, identity_confidence or 0.75)), 4)
        return round(min(0.8, max(0.55, identity_confidence or 0.55)), 4)

    def _build_profit_solve_rows(self, state: Dict[str, Any], *, batch_ref: str) -> Dict[str, Any]:
        core_model = self._build_core_rows(state, batch_ref=batch_ref)
        rows: list[Dict[str, Any]] = []
        for row in core_model['rows']:
            item = dict(row)
            resolved_totals = dict(item.get('resolvedComponentTotals') or {})
            platform_fee = round(float(resolved_totals.get('platform_fee', item.get('platformFeeAmount') or 0.0) or 0.0), 4)
            fulfillment_fee = round(float(resolved_totals.get('fulfillment_fee', item.get('fulfillmentFeeAmount') or 0.0) or 0.0), 4)
            ads_cost = round(float(resolved_totals.get('ads_cost', 0.0) or 0.0), 4)
            other_variable_cost = round(float(resolved_totals.get('other_variable_cost', 0.0) or 0.0), 4)
            net_sales_amount = round(float(item.get('netSalesAmount') or 0.0), 4)

            base_contribution_profit = round(net_sales_amount - platform_fee - fulfillment_fee - other_variable_cost, 4)
            profit_after_ads = round(base_contribution_profit - ads_cost, 4)
            risk_adjusted_profit = profit_after_ads
            net_margin_rate = round((risk_adjusted_profit / net_sales_amount), 4) if net_sales_amount else None

            component_amounts = {
                'platform_fee': platform_fee,
                'fulfillment_fee': fulfillment_fee,
                'ads_cost': ads_cost,
                'other_variable_cost': other_variable_cost,
            }
            dominant_component, dominant_component_amount = self._pick_dominant_cost_component(component_amounts)

            allow_fallback_solve = (
                item.get('coreBindingMode') == 'import_partial_fallback'
                and item.get('coreCalculationState') == 'calculated_import_fallback_partial_costs'
            )
            allow_config_solve = (
                item.get('coreBindingMode') == 'config_resolve'
                and item.get('coreCalculationState') == 'calculated_config_bound_partial_costs'
            )
            solve_ready = bool(item.get('coreReady') is True or allow_fallback_solve or allow_config_solve)
            if not solve_ready:
                solve_state = 'blocked_core_quality'
            elif item.get('coreBindingMode') == 'config_resolve':
                solve_state = 'calculated_config_bound_profit_skeleton'
            else:
                solve_state = 'calculated_import_fallback_profit_skeleton'

            item['platformFeeResolved'] = platform_fee
            item['fulfillmentFeeResolved'] = fulfillment_fee
            item['adsCostResolved'] = ads_cost
            item['otherVariableCostResolved'] = other_variable_cost
            item['baseContributionProfit'] = base_contribution_profit
            item['profitAfterAds'] = profit_after_ads
            item['riskAdjustedProfit'] = risk_adjusted_profit
            item['netMarginRate'] = net_margin_rate
            item['profitConfidence'] = self._estimate_profit_confidence(item)
            item['dominantCostComponent'] = dominant_component
            item['dominantCostComponentAmount'] = dominant_component_amount
            item['dominantRiskDriver'] = 'cost_config_pending' if item.get('coreBindingMode') != 'config_resolve' else (dominant_component or 'none')
            item['solveReady'] = solve_ready
            item['solveState'] = solve_state
            item['solveSourceMode'] = 'config_resolve' if item.get('coreBindingMode') == 'config_resolve' else 'import_partial_fallback'
            rows.append(item)

        readiness = {
            'solveRowCount': len(rows),
            'solveReadyRowCount': sum(1 for row in rows if row.get('solveReady') is True),
            'blockedSolveRowCount': sum(1 for row in rows if row.get('solveReady') is not True),
            'configBoundRowCount': sum(1 for row in rows if row.get('solveSourceMode') == 'config_resolve'),
            'fallbackRowCount': sum(1 for row in rows if row.get('solveSourceMode') == 'import_partial_fallback'),
        }
        readiness['solveReadyRate'] = round((readiness['solveReadyRowCount'] / readiness['solveRowCount']) if readiness['solveRowCount'] else 0.0, 4)
        return {'rows': rows, 'factReadiness': core_model['factReadiness'], 'coreReadiness': core_model['coreReadiness'], 'solveReadiness': readiness}

    def _project_profit_solve_rows(self, rows: list[Dict[str, Any]]) -> tuple[list[Dict[str, Any]], list[str]]:
        column_order = [
            'factDate', 'shopId', 'skuId', 'canonicalSku', 'currencyCode', 'providerCode',
            'resolvedProfileCode', 'coreBindingMode', 'solveSourceMode',
            'netSalesAmount', 'platformFeeResolved', 'fulfillmentFeeResolved', 'adsCostResolved', 'otherVariableCostResolved',
            'baseContributionProfit', 'profitAfterAds', 'riskAdjustedProfit', 'netMarginRate',
            'profitConfidence', 'dominantCostComponent', 'dominantCostComponentAmount', 'dominantRiskDriver',
            'solveReady', 'solveState',
        ]
        projected = []
        for row in rows:
            projected.append({field: row.get(field) for field in column_order})
        return projected, column_order

    def _build_profit_solve_summary(self, rows: list[Dict[str, Any]], *, solve_readiness: Dict[str, Any]) -> Dict[str, Any]:
        total_rows = len(rows)
        revenue_amount_total = round(sum(float(row.get('netSalesAmount') or 0.0) for row in rows), 4)
        base_profit_total = round(sum(float(row.get('baseContributionProfit') or 0.0) for row in rows), 4)
        profit_after_ads_total = round(sum(float(row.get('profitAfterAds') or 0.0) for row in rows), 4)
        risk_adjusted_total = round(sum(float(row.get('riskAdjustedProfit') or 0.0) for row in rows), 4)
        confidence_values = [float(row.get('profitConfidence') or 0.0) for row in rows if row.get('solveReady') is True]
        return {
            'rowCount': total_rows,
            'solveReadyRowCount': solve_readiness['solveReadyRowCount'],
            'blockedRowCount': total_rows - solve_readiness['solveReadyRowCount'],
            'configBoundRowCount': solve_readiness.get('configBoundRowCount', 0),
            'fallbackRowCount': solve_readiness.get('fallbackRowCount', 0),
            'revenueAmountTotal': revenue_amount_total,
            'baseContributionProfitTotal': base_profit_total,
            'profitAfterAdsTotal': profit_after_ads_total,
            'riskAdjustedProfitTotal': risk_adjusted_total,
            'netMarginRate': round((risk_adjusted_total / revenue_amount_total) if revenue_amount_total else 0.0, 4),
            'profitConfidenceAvg': round((sum(confidence_values) / len(confidence_values)) if confidence_values else 0.0, 4),
        }

    def _build_profit_solve_issue_buckets(self, rows: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        counter = Counter()
        for row in rows:
            if row.get('solveReady') is not True:
                counter[str(row.get('solveState') or 'blocked_core_quality')] += 1
                continue
            if row.get('solveSourceMode') == 'import_partial_fallback':
                counter['fallback_profit_skeleton'] += 1
            if row.get('dominantRiskDriver') == 'cost_config_pending':
                counter['cost_config_pending'] += 1
        return [
            {'reason': reason, 'rowCount': count}
            for reason, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
        ]

    def _build_pricing_recommend_contract(self, batch_id: int) -> Dict[str, Any]:
        return {
            'contractName': 'economics_pricing_recommend',
            'contractVersion': 'p4.pricing_recommend.v1',
            'strategyModes': ['balanced_profit'],
            'defaultStrategyMode': 'balanced_profit',
            'defaultView': 'all',
            'availableViews': ['all', 'ready', 'issues'],
            'inputFields': ['batchRef', 'strategyMode', 'constraints.minMargin'],
            'dimensionFields': ['factDate', 'shopId', 'skuId', 'canonicalSku', 'currencyCode', 'providerCode'],
            'priceLineFields': ['currentUnitPrice', 'breakEvenPrice', 'floorPrice', 'targetPrice', 'ceilingPrice', 'recommendedPrice'],
            'qualityFields': ['recommendationReady', 'recommendationState', 'solveSourceMode', 'profitConfidence'],
            'notes': [
                '当前 POST /api/v1/economics/pricing/recommend 只冻结为基于 batch historical solve 的 pricing skeleton。',
                '本轮先输出价格三线与最小 explanation/risk，不做 full P&L / snapshot / action control。',
                '正式场景化 pricing recommend 仍以后续 Economics Engine V1 扩展为准。',
            ],
            'exportFileStem': f'batch_{batch_id}_pricing_recommend',
        }

    @staticmethod
    def _safe_unit_price(amount: Any, qty: Any) -> float:
        amount_value = float(amount or 0.0)
        qty_value = float(qty or 0.0)
        if qty_value > 0:
            return round(amount_value / qty_value, 4)
        return round(amount_value, 4)

    def _build_pricing_recommend_rows(
        self,
        state: Dict[str, Any],
        *,
        batch_ref: str,
        strategy_mode: str,
        constraints: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        solve_model = self._build_profit_solve_rows(state, batch_ref=batch_ref)
        min_margin = round(float((constraints or {}).get('minMargin') or 0.08), 4)
        rows: list[Dict[str, Any]] = []
        for row in solve_model['rows']:
            item = dict(row)
            qty_base = float(item.get('deliveredQty') or item.get('orderedQty') or 0.0)
            amount_base = item.get('netSalesAmount')
            if float(amount_base or 0.0) <= 0:
                amount_base = item.get('deliveredAmountEstimated')
            if float(amount_base or 0.0) <= 0:
                amount_base = item.get('orderedAmount')
            current_unit_price = self._safe_unit_price(amount_base, qty_base)
            platform_fee = float(item.get('platformFeeResolved') or 0.0)
            fulfillment_fee = float(item.get('fulfillmentFeeResolved') or 0.0)
            ads_cost = float(item.get('adsCostResolved') or 0.0)
            other_cost = float(item.get('otherVariableCostResolved') or 0.0)
            variable_rate_total = 0.0
            if float(item.get('netSalesAmount') or 0.0) > 0:
                variable_rate_total = round((platform_fee + fulfillment_fee) / float(item.get('netSalesAmount') or 0.0), 4)
            fixed_cost_total = round(ads_cost + other_cost, 4)
            pricing_ready = bool(item.get('solveReady') is True)
            if not pricing_ready or current_unit_price <= 0:
                recommendation_state = 'blocked_profit_solve'
                break_even_price = 0.0
                floor_price = 0.0
                target_price = 0.0
                ceiling_price = 0.0
                recommended_price = 0.0
                explanation = {
                    'summary': '利润求解未就绪，无法给出定价建议。',
                    'whyNotLower': '当前 solve 未就绪。',
                    'whyNotHigher': '当前 solve 未就绪。',
                }
                risks = ['profit_solve_blocked']
            else:
                payload = ProfitInput(
                    sale_price=current_unit_price,
                    list_price=current_unit_price,
                    variable_rate_total=variable_rate_total,
                    fixed_cost_total=fixed_cost_total,
                )
                current_result = self.profit_solver.solve_current(payload)
                break_even_price = round(float(current_result.break_even_price or 0.0), 4)
                current_margin = round(float(current_result.net_margin or 0.0), 4)
                if strategy_mode == 'balanced_profit' and current_margin < min_margin and variable_rate_total < 1:
                    try:
                        target_price = round(float(self.profit_solver.target_margin_price(min_margin, variable_rate_total, fixed_cost_total)), 4)
                        recommendation_state = 'recommended_margin_recovery'
                    except Exception:
                        target_price = current_unit_price
                        recommendation_state = 'recommended_hold_current_price'
                else:
                    target_price = current_unit_price
                    recommendation_state = 'recommended_hold_current_price' if item.get('solveSourceMode') == 'config_resolve' else 'recommended_import_fallback_guardrail'
                floor_price = max(0.0, break_even_price)
                ceiling_price = max(current_unit_price, target_price)
                recommended_price = target_price
                risks = []
                if item.get('solveSourceMode') == 'import_partial_fallback':
                    risks.append('cost_config_pending')
                if float(item.get('profitConfidence') or 0.0) < 0.7:
                    risks.append('low_profit_confidence')
                if current_margin < min_margin:
                    risks.append('below_target_margin')
                explanation = {
                    'summary': f'基于历史批次利润骨架给出 {strategy_mode} 定价建议。',
                    'whyNotLower': f'低于 {round(floor_price, 4)} 将接近或跌破保本线。',
                    'whyNotHigher': '本轮 pricing skeleton 仅冻结最小建议，不做弹性/评分/库存联动上探。',
                }
            item['strategyMode'] = strategy_mode
            item['minMarginConstraint'] = min_margin
            item['currentUnitPrice'] = current_unit_price
            item['breakEvenPrice'] = break_even_price
            item['floorPrice'] = floor_price
            item['targetPrice'] = target_price
            item['ceilingPrice'] = ceiling_price
            item['recommendedPrice'] = recommended_price
            item['recommendationReady'] = pricing_ready and current_unit_price > 0
            item['recommendationState'] = recommendation_state
            item['explanation'] = explanation
            item['risks'] = risks
            rows.append(item)
        readiness = {
            'pricingRowCount': len(rows),
            'recommendationReadyRowCount': sum(1 for row in rows if row.get('recommendationReady') is True),
            'blockedRowCount': sum(1 for row in rows if row.get('recommendationReady') is not True),
            'configBoundRowCount': sum(1 for row in rows if row.get('solveSourceMode') == 'config_resolve'),
            'fallbackRowCount': sum(1 for row in rows if row.get('solveSourceMode') == 'import_partial_fallback'),
        }
        return {
            'rows': rows,
            'factReadiness': solve_model['factReadiness'],
            'coreReadiness': solve_model['coreReadiness'],
            'solveReadiness': solve_model['solveReadiness'],
            'pricingReadiness': readiness,
        }

    def _project_pricing_recommend_rows(self, rows: list[Dict[str, Any]]) -> tuple[list[Dict[str, Any]], list[str]]:
        column_order = [
            'factDate', 'shopId', 'skuId', 'canonicalSku', 'currencyCode', 'providerCode',
            'resolvedProfileCode', 'solveSourceMode', 'strategyMode',
            'currentUnitPrice', 'breakEvenPrice', 'floorPrice', 'targetPrice', 'ceilingPrice', 'recommendedPrice',
            'recommendationReady', 'recommendationState', 'profitConfidence', 'dominantRiskDriver', 'explanation', 'risks',
        ]
        projected = []
        for row in rows:
            projected.append({field: row.get(field) for field in column_order})
        return projected, column_order

    def _build_pricing_recommend_summary(self, rows: list[Dict[str, Any]], *, pricing_readiness: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'rowCount': len(rows),
            'recommendationReadyRowCount': pricing_readiness['recommendationReadyRowCount'],
            'blockedRowCount': pricing_readiness['blockedRowCount'],
            'configBoundRowCount': pricing_readiness['configBoundRowCount'],
            'fallbackRowCount': pricing_readiness['fallbackRowCount'],
            'recommendedPriceAvg': round((sum(float(row.get('recommendedPrice') or 0.0) for row in rows) / len(rows)) if rows else 0.0, 4),
            'floorPriceAvg': round((sum(float(row.get('floorPrice') or 0.0) for row in rows) / len(rows)) if rows else 0.0, 4),
        }

    def _build_config_state_payload(self, batch_ref: str) -> dict[str, Any] | None:
        summary = self.config_service.get_batch_config_resolve_summary(batch_ref)
        if not summary:
            return None
        return {
            'isConfigAware': True,
            'defaultProfileCode': summary.get('defaultProfileCode'),
            'configReadyRowCount': summary.get('configReadyRowCount'),
            'blockedRowCount': summary.get('blockedRowCount'),
            'missingCostCardRowCount': summary.get('missingCostCardRowCount'),
            'configReadyRate': summary.get('configReadyRate'),
        }

    def get_batch_economics_core(
        self,
        batch_ref: str,
        *,
        limit: int = 50,
        offset: int = 0,
        view: str = 'all',
    ) -> Optional[Dict[str, Any]]:
        state = self._load_state(batch_ref)
        if not state:
            return None
        detail = dict(state['detail'])
        events = list(state.get('events') or [])
        aggregate_metrics = self.object_service._build_aggregate_metrics(state)
        identity_diagnostics = self.object_service._build_identity_diagnostics(state)
        core_model = self._build_core_rows(state, batch_ref=batch_ref)
        normalized_view = self._normalize_view(view)
        filtered_rows = self.object_service._filter_fact_rows(core_model['rows'], view=normalized_view)
        safe_offset = max(int(offset or 0), 0)
        safe_limit = min(max(int(limit or 50), 1), 200)
        page, page_info = self._paginate_rows(filtered_rows, offset=safe_offset, limit=safe_limit)
        projected_page, column_order = self._project_core_rows(page)
        contract = self._build_core_contract(state['batchId'])
        return {
            'batchId': state['batchId'],
            'datasetKind': detail.get('datasetKind'),
            'contractVersion': contract['contractVersion'],
            'status': 'completed' if events else 'pending',
            'view': normalized_view,
            'sourcePreset': self.CONSUMER_PRESET,
            'columnOrder': column_order,
            'pagination': page_info,
            'aggregateMetrics': aggregate_metrics,
            'identityDiagnostics': identity_diagnostics,
            'factReadiness': core_model['factReadiness'],
            'coreReadiness': core_model['coreReadiness'],
            'coreSummary': self._build_core_summary(filtered_rows, core_readiness=core_model['coreReadiness']),
            'costCoverageSummary': self._build_cost_coverage_summary(filtered_rows),
            'issueBuckets': self._build_issue_buckets(filtered_rows),
            'configResolveSummary': self._build_config_state_payload(batch_ref),
            'sourceFactContract': self.object_service._build_fact_contract(state['batchId']),
            'sourceIntakeContract': self._build_contract(state['batchId']),
            'sourceConfigContract': self.config_service.get_batch_config_resolve_contract(batch_ref),
            'exportSpec': {
                'fileStem': contract['exportFileStem'],
                'suggestedFileName': f"{contract['exportFileStem']}_{normalized_view}.json",
                'selectedColumns': column_order,
            },
            'items': projected_page,
        }

    def get_batch_economics_core_contract(self, batch_ref: str) -> Optional[Dict[str, Any]]:
        state = self._load_state(batch_ref)
        if not state:
            return None
        detail = dict(state['detail'])
        events = list(state.get('events') or [])
        core_model = self._build_core_rows(state, batch_ref=batch_ref)
        return {
            'batchId': state['batchId'],
            'datasetKind': detail.get('datasetKind'),
            'contractVersion': self._build_core_contract(state['batchId'])['contractVersion'],
            'status': 'completed' if events else 'pending',
            'factReadiness': core_model['factReadiness'],
            'coreReadiness': core_model['coreReadiness'],
            'sourceFactContract': self.object_service._build_fact_contract(state['batchId']),
            'sourceIntakeContract': self._build_contract(state['batchId']),
            'sourceConfigContract': self.config_service.get_batch_config_resolve_contract(batch_ref),
            'consumerContract': self._build_core_contract(state['batchId']),
        }

    def get_batch_profit_solve(
        self,
        batch_ref: str,
        *,
        limit: int = 50,
        offset: int = 0,
        view: str = 'all',
    ) -> Optional[Dict[str, Any]]:
        state = self._load_state(batch_ref)
        if not state:
            return None
        detail = dict(state['detail'])
        events = list(state.get('events') or [])
        aggregate_metrics = self.object_service._build_aggregate_metrics(state)
        identity_diagnostics = self.object_service._build_identity_diagnostics(state)
        solve_model = self._build_profit_solve_rows(state, batch_ref=batch_ref)
        normalized_view = self._normalize_view(view)
        filtered_rows = self.object_service._filter_fact_rows(solve_model['rows'], view=normalized_view)
        safe_offset = max(int(offset or 0), 0)
        safe_limit = min(max(int(limit or 50), 1), 200)
        page, page_info = self._paginate_rows(filtered_rows, offset=safe_offset, limit=safe_limit)
        projected_page, column_order = self._project_profit_solve_rows(page)
        contract = self._build_profit_solve_contract(state['batchId'])
        return {
            'batchId': state['batchId'],
            'datasetKind': detail.get('datasetKind'),
            'contractVersion': contract['contractVersion'],
            'status': 'completed' if events else 'pending',
            'view': normalized_view,
            'sourcePreset': self.CONSUMER_PRESET,
            'columnOrder': column_order,
            'pagination': page_info,
            'aggregateMetrics': aggregate_metrics,
            'identityDiagnostics': identity_diagnostics,
            'factReadiness': solve_model['factReadiness'],
            'coreReadiness': solve_model['coreReadiness'],
            'solveReadiness': solve_model['solveReadiness'],
            'solveSummary': self._build_profit_solve_summary(filtered_rows, solve_readiness=solve_model['solveReadiness']),
            'issueBuckets': self._build_profit_solve_issue_buckets(filtered_rows),
            'configResolveSummary': self._build_config_state_payload(batch_ref),
            'sourceFactContract': self.object_service._build_fact_contract(state['batchId']),
            'sourceIntakeContract': self._build_contract(state['batchId']),
            'sourceCoreContract': self._build_core_contract(state['batchId']),
            'sourceConfigContract': self.config_service.get_batch_config_resolve_contract(batch_ref),
            'exportSpec': {
                'fileStem': contract['exportFileStem'],
                'suggestedFileName': f"{contract['exportFileStem']}_{normalized_view}.json",
                'selectedColumns': column_order,
            },
            'items': projected_page,
        }

    def get_batch_profit_solve_contract(self, batch_ref: str) -> Optional[Dict[str, Any]]:
        state = self._load_state(batch_ref)
        if not state:
            return None
        detail = dict(state['detail'])
        events = list(state.get('events') or [])
        solve_model = self._build_profit_solve_rows(state, batch_ref=batch_ref)
        return {
            'batchId': state['batchId'],
            'datasetKind': detail.get('datasetKind'),
            'contractVersion': self._build_profit_solve_contract(state['batchId'])['contractVersion'],
            'status': 'completed' if events else 'pending',
            'factReadiness': solve_model['factReadiness'],
            'coreReadiness': solve_model['coreReadiness'],
            'solveReadiness': solve_model['solveReadiness'],
            'sourceFactContract': self.object_service._build_fact_contract(state['batchId']),
            'sourceIntakeContract': self._build_contract(state['batchId']),
            'sourceCoreContract': self._build_core_contract(state['batchId']),
            'sourceConfigContract': self.config_service.get_batch_config_resolve_contract(batch_ref),
            'consumerContract': self._build_profit_solve_contract(state['batchId']),
        }

    def get_batch_pricing_recommend(
        self,
        batch_ref: str,
        *,
        strategy_mode: str = 'balanced_profit',
        constraints: Dict[str, Any] | None = None,
        limit: int = 50,
        offset: int = 0,
        view: str = 'all',
    ) -> Optional[Dict[str, Any]]:
        state = self._load_state(batch_ref)
        if not state:
            return None
        detail = dict(state['detail'])
        events = list(state.get('events') or [])
        aggregate_metrics = self.object_service._build_aggregate_metrics(state)
        identity_diagnostics = self.object_service._build_identity_diagnostics(state)
        pricing_model = self._build_pricing_recommend_rows(state, batch_ref=batch_ref, strategy_mode=self._clean_str(strategy_mode, 'balanced_profit'), constraints=constraints)
        normalized_view = self._normalize_view(view)
        filtered_rows = self.object_service._filter_fact_rows(pricing_model['rows'], view=normalized_view)
        safe_offset = max(int(offset or 0), 0)
        safe_limit = min(max(int(limit or 50), 1), 200)
        page, page_info = self._paginate_rows(filtered_rows, offset=safe_offset, limit=safe_limit)
        projected_page, column_order = self._project_pricing_recommend_rows(page)
        contract = self._build_pricing_recommend_contract(state['batchId'])
        return {
            'batchId': state['batchId'],
            'datasetKind': detail.get('datasetKind'),
            'contractVersion': contract['contractVersion'],
            'status': 'completed' if events else 'pending',
            'view': normalized_view,
            'strategyMode': self._clean_str(strategy_mode, 'balanced_profit'),
            'constraints': {'minMargin': round(float((constraints or {}).get('minMargin') or 0.08), 4)},
            'pagination': page_info,
            'columnOrder': column_order,
            'aggregateMetrics': aggregate_metrics,
            'identityDiagnostics': identity_diagnostics,
            'factReadiness': pricing_model['factReadiness'],
            'coreReadiness': pricing_model['coreReadiness'],
            'solveReadiness': pricing_model['solveReadiness'],
            'pricingReadiness': pricing_model['pricingReadiness'],
            'recommendSummary': self._build_pricing_recommend_summary(filtered_rows, pricing_readiness=pricing_model['pricingReadiness']),
            'sourceSolveContract': self._build_profit_solve_contract(state['batchId']),
            'sourceConfigContract': self.config_service.get_batch_config_resolve_contract(batch_ref),
            'exportSpec': {
                'fileStem': contract['exportFileStem'],
                'suggestedFileName': f"{contract['exportFileStem']}_{normalized_view}.json",
                'selectedColumns': column_order,
            },
            'items': projected_page,
        }

    def get_batch_pricing_recommend_contract(self, batch_ref: str, *, strategy_mode: str = 'balanced_profit') -> Optional[Dict[str, Any]]:
        state = self._load_state(batch_ref)
        if not state:
            return None
        detail = dict(state['detail'])
        events = list(state.get('events') or [])
        pricing_model = self._build_pricing_recommend_rows(state, batch_ref=batch_ref, strategy_mode=self._clean_str(strategy_mode, 'balanced_profit'), constraints={'minMargin': 0.08})
        return {
            'batchId': state['batchId'],
            'datasetKind': detail.get('datasetKind'),
            'contractVersion': self._build_pricing_recommend_contract(state['batchId'])['contractVersion'],
            'status': 'completed' if events else 'pending',
            'strategyMode': self._clean_str(strategy_mode, 'balanced_profit'),
            'solveReadiness': pricing_model['solveReadiness'],
            'pricingReadiness': pricing_model['pricingReadiness'],
            'sourceSolveContract': self._build_profit_solve_contract(state['batchId']),
            'sourceConfigContract': self.config_service.get_batch_config_resolve_contract(batch_ref),
            'consumerContract': self._build_pricing_recommend_contract(state['batchId']),
        }

    def get_batch_economics_intake(
        self,
        batch_ref: str,
        *,
        limit: int = 50,
        offset: int = 0,
        view: str = 'ready',
    ) -> Optional[Dict[str, Any]]:
        state = self._load_state(batch_ref)
        if not state:
            return None
        detail = dict(state['detail'])
        events = list(state.get('events') or [])
        aggregate_metrics = self.object_service._build_aggregate_metrics(state)
        identity_diagnostics = self.object_service._build_identity_diagnostics(state)
        intake_model = self._build_intake_rows(state)
        normalized_view = self._normalize_view(view)
        filtered_rows = self.object_service._filter_fact_rows(intake_model['rows'], view=normalized_view)
        safe_offset = max(int(offset or 0), 0)
        safe_limit = min(max(int(limit or 50), 1), 200)
        page, page_info = self._paginate_rows(filtered_rows, offset=safe_offset, limit=safe_limit)
        projected_page, column_order = self._project_rows(page)
        contract = self._build_contract(state['batchId'])
        issue_buckets = self._build_issue_buckets(filtered_rows)
        return {
            'batchId': state['batchId'],
            'datasetKind': detail.get('datasetKind'),
            'contractVersion': self.CONTRACT_VERSION,
            'status': 'completed' if events else 'pending',
            'view': normalized_view,
            'sourcePreset': self.CONSUMER_PRESET,
            'columnOrder': column_order,
            'pagination': page_info,
            'aggregateMetrics': aggregate_metrics,
            'identityDiagnostics': identity_diagnostics,
            'factReadiness': intake_model['factReadiness'],
            'intakeSummary': self._build_intake_summary(filtered_rows, fact_readiness=intake_model['factReadiness']),
            'dimensionSummary': self._build_dimension_summary(filtered_rows),
            'issueBuckets': issue_buckets,
            'configResolveSummary': self._build_config_state_payload(batch_ref),
            'sourceFactContract': self.object_service._build_fact_contract(state['batchId']),
            'sourceConfigContract': self.config_service.get_batch_config_resolve_contract(batch_ref),
            'exportSpec': {
                'fileStem': contract['exportFileStem'],
                'suggestedFileName': f"{contract['exportFileStem']}_{normalized_view}.json",
                'selectedColumns': column_order,
            },
            'items': projected_page,
        }

    def get_batch_economics_intake_contract(self, batch_ref: str) -> Optional[Dict[str, Any]]:
        state = self._load_state(batch_ref)
        if not state:
            return None
        detail = dict(state['detail'])
        events = list(state.get('events') or [])
        intake_model = self._build_intake_rows(state)
        return {
            'batchId': state['batchId'],
            'datasetKind': detail.get('datasetKind'),
            'contractVersion': self.CONTRACT_VERSION,
            'status': 'completed' if events else 'pending',
            'factReadiness': intake_model['factReadiness'],
            'sourceFactContract': self.object_service._build_fact_contract(state['batchId']),
            'consumerContract': self._build_contract(state['batchId']),
        }
