from __future__ import annotations

from datetime import date, timedelta, datetime
import json
from collections import defaultdict

from sqlalchemy import func

from ecom_v51.db.models import (
    DimDate,
    DimSku,
    FactAdsDaily,
    FactInventoryDaily,
    FactProfitSnapshot,
    FactReviewsDaily,
    FactSkuDaily,
    StrategyTask,
)
from ecom_v51.db.session import get_session
from ecom_v51.services.strategy_service import build_action_source


class AnalysisService:
    def __init__(self, shop_id: int = 1, days: int = 7) -> None:
        self.shop_id = shop_id
        self.days = max(days, 1)

    def _date_window(self) -> tuple[date, date]:
        end = date.today()
        start = end - timedelta(days=self.days - 1)
        return start, end

    def abc_analysis(self) -> dict[str, object]:
        start, end = self._date_window()
        with get_session() as session:
            rows = (
                session.query(
                    DimSku.sku.label('sku'),
                    func.coalesce(func.sum(FactSkuDaily.revenue_ordered), 0.0).label('revenue'),
                    func.coalesce(func.sum(FactSkuDaily.orders_count), 0).label('orders'),
                    func.coalesce(func.avg(FactProfitSnapshot.net_margin), 0.0).label('margin'),
                    func.coalesce(func.avg(FactSkuDaily.card_visits / func.nullif(FactSkuDaily.impressions_total, 0)), 0.0).label('ctr'),
                    func.coalesce(func.avg(FactAdsDaily.roas), 0.0).label('roas'),
                    func.coalesce(func.avg(FactInventoryDaily.days_of_supply), 0.0).label('days_supply'),
                    func.coalesce(func.avg(FactReviewsDaily.rating_avg), 0.0).label('rating'),
                    func.coalesce(func.avg(FactSkuDaily.returned_count / func.nullif(FactSkuDaily.delivered_count, 0)), 0.0).label('return_rate'),
                )
                .join(FactSkuDaily, FactSkuDaily.sku_id == DimSku.id)
                .join(DimDate, FactSkuDaily.date_id == DimDate.id)
                .outerjoin(FactProfitSnapshot, (FactProfitSnapshot.sku_id == DimSku.id) & (FactProfitSnapshot.date_id == FactSkuDaily.date_id))
                .outerjoin(FactAdsDaily, (FactAdsDaily.sku_id == DimSku.id) & (FactAdsDaily.date_id == FactSkuDaily.date_id))
                .outerjoin(FactInventoryDaily, (FactInventoryDaily.sku_id == DimSku.id) & (FactInventoryDaily.date_id == FactSkuDaily.date_id))
                .outerjoin(FactReviewsDaily, (FactReviewsDaily.sku_id == DimSku.id) & (FactReviewsDaily.date_id == FactSkuDaily.date_id))
                .filter(FactSkuDaily.shop_id == self.shop_id, DimDate.date_value >= start, DimDate.date_value <= end)
                .group_by(DimSku.sku)
                .order_by(func.sum(FactSkuDaily.revenue_ordered).desc())
                .limit(100)
                .all()
            )

        total_revenue = sum(float(r.revenue or 0) for r in rows) or 1.0
        cum = 0.0
        items = []
        for r in rows:
            rev = float(r.revenue or 0.0)
            cum += rev / total_revenue
            abc = 'A' if cum <= 0.7 else ('B' if cum <= 0.9 else 'C')
            issues = []
            if float(r.margin or 0) < 0.1:
                issues.append('低毛利')
            if float(r.days_supply or 0) < 7:
                issues.append('库存风险')
            items.append({
                'sku': r.sku,
                'revenue': rev,
                'orders': int(r.orders or 0),
                'margin': float(r.margin or 0.0),
                'abcClass': abc,
                'ctr': float(r.ctr or 0.0),
                'roas': float(r.roas or 0.0),
                'daysOfSupply': float(r.days_supply or 0.0),
                'rating': float(r.rating or 0.0),
                'returnRate': float(r.return_rate or 0.0),
                'issue': '、'.join(issues) if issues else '结构健康',
                'recommendation': self._abc_recommendation(abc, issues),
                'priority': 'P0' if '库存风险' in issues else ('P1' if '低毛利' in issues else 'P2'),
            })

        summary = {
            'A': len([x for x in items if x['abcClass'] == 'A']),
            'B': len([x for x in items if x['abcClass'] == 'B']),
            'C': len([x for x in items if x['abcClass'] == 'C']),
            'totalRevenue': round(sum(x['revenue'] for x in items), 2),
            'avgMargin': round((sum(x['margin'] for x in items) / len(items)), 4) if items else 0,
        }
        issues = [x for x in items if x['issue'] != '结构健康']
        return {'summary': summary, 'rows': items, 'issues': issues[:20], 'recommendedActions': issues[:10]}

    @staticmethod
    def _abc_recommendation(abc: str, issues: list[str]) -> str:
        if abc == 'A':
            return 'A类重点保供与利润优化，保持投放强度'
        if '库存风险' in issues:
            return '优先补货并设置动态安全库存'
        if '低毛利' in issues:
            return '优化费率结构并调整售价策略'
        return 'C类结合清仓与低预算保活策略'

    def price_cockpit(self, view: str = 'daily') -> dict[str, object]:
        start, end = self._date_window()
        with get_session() as session:
            rows = (
                session.query(
                    DimSku.id.label('sku_id'),
                    DimSku.sku.label('sku'),
                    func.coalesce(func.avg(FactProfitSnapshot.sale_price), 0.0).label('our_price'),
                    func.coalesce(func.avg(FactProfitSnapshot.list_price), 0.0).label('market_price'),
                    func.coalesce(func.avg(FactProfitSnapshot.net_margin), 0.0).label('margin'),
                    func.coalesce(func.sum(FactSkuDaily.orders_count), 0).label('orders'),
                    func.coalesce(func.avg(FactAdsDaily.roas), 0.0).label('roas'),
                )
                .join(FactProfitSnapshot, FactProfitSnapshot.sku_id == DimSku.id)
                .join(DimDate, FactProfitSnapshot.date_id == DimDate.id)
                .outerjoin(FactSkuDaily, (FactSkuDaily.sku_id == DimSku.id) & (FactSkuDaily.date_id == FactProfitSnapshot.date_id))
                .outerjoin(FactAdsDaily, (FactAdsDaily.sku_id == DimSku.id) & (FactAdsDaily.date_id == FactProfitSnapshot.date_id))
                .filter(FactProfitSnapshot.shop_id == self.shop_id, DimDate.date_value >= start, DimDate.date_value <= end)
                .group_by(DimSku.id, DimSku.sku)
                .order_by(func.avg(FactProfitSnapshot.net_margin).asc())
                .limit(200)
                .all()
            )

        strategy_groups = {
            'traffic': {'label': '引流组', 'rule': lambda x: x['priceGap'] <= -20 and x['margin'] < 0.15},
            'standard_margin': {'label': '标准利润组', 'rule': lambda x: -20 < x['priceGap'] < 20 and x['margin'] >= 0.1},
            'high_margin': {'label': '高利润组', 'rule': lambda x: x['margin'] >= 0.25},
            'clearance': {'label': '清仓组', 'rule': lambda x: x['orders'] < 5 and x['margin'] <= 0.1},
            'campaign': {'label': '活动参与组', 'rule': lambda x: x['roas'] > 2.5 and x['orders'] > 10},
        }

        items = []
        for r in rows:
            our = float(r.our_price or 0)
            market = float(r.market_price or 0)
            price_gap = round(our - market, 2)
            comp = 'green' if price_gap <= 0 else ('yellow' if price_gap <= 20 else 'red')
            base = {
                'skuId': int(r.sku_id),
                'sku': r.sku,
                'ourPrice': round(our, 2),
                'marketPrice': round(market, 2),
                'priceGap': price_gap,
                'margin': float(r.margin or 0),
                'orders': int(r.orders or 0),
                'roas': float(r.roas or 0),
                'competitiveness': comp,
                'view': view,
            }
            group = next((k for k, g in strategy_groups.items() if g['rule'](base)), 'standard_margin')
            base['group'] = group
            base['recommendation'] = self._price_recommendation(base, view)
            items.append(base)

        group_counts = defaultdict(int)
        for x in items:
            group_counts[x['group']] += 1

        issues = [x for x in items if x['competitiveness'] == 'red' or x['margin'] < 0.08]
        return {
            'summary': {
                'totalSku': len(items),
                'redZone': len([x for x in items if x['competitiveness'] == 'red']),
                'avgPriceGap': round(sum(x['priceGap'] for x in items) / len(items), 2) if items else 0,
                'avgMargin': round(sum(x['margin'] for x in items) / len(items), 4) if items else 0,
            },
            'groupedStrategies': [{ 'key': k, 'label': v['label'], 'count': group_counts[k]} for k, v in strategy_groups.items()],
            'batchRecommendations': items,
            'issues': issues[:30],
            'explanations': [
                {'title': '分组说明', 'content': '按价格差、利润率、订单和ROAS自动分组。'},
                {'title': '推荐逻辑', 'content': '高价低转化优先降价，低价低毛利优先提价。'},
                {'title': '动作流转', 'content': '可一键推送至策略清单并进入决策队列。'},
            ],
        }

    @staticmethod
    def _price_recommendation(item: dict[str, object], view: str) -> str:
        price_gap = float(item['priceGap'])
        margin = float(item['margin'])
        if view == 'campaign':
            return '活动价建议：以保转化为先，控制最低毛利底线'
        if view == 'promo':
            return '自促建议：按库存与ROI设置阶梯折扣'
        if price_gap > 20:
            return '高于市场价，建议降价5%-12%并复测转化'
        if price_gap < -20 and margin < 0.15:
            return '低价低毛利，建议提价3%-8%并优化费率'
        return '价格处于可接受区间，维持并观察'

    def funnel_analysis(self) -> dict[str, object]:
        start, end = self._date_window()
        with get_session() as session:
            rows = (
                session.query(
                    DimSku.id.label('sku_id'),
                    DimSku.sku.label('sku'),
                    func.coalesce(func.sum(FactSkuDaily.impressions_total), 0).label('impressions'),
                    func.coalesce(func.sum(FactSkuDaily.card_visits), 0).label('card_visits'),
                    func.coalesce(func.sum(FactSkuDaily.add_to_cart_total), 0).label('add_to_cart'),
                    func.coalesce(func.sum(FactSkuDaily.orders_count), 0).label('orders'),
                )
                .join(FactSkuDaily, FactSkuDaily.sku_id == DimSku.id)
                .join(DimDate, FactSkuDaily.date_id == DimDate.id)
                .filter(FactSkuDaily.shop_id == self.shop_id, DimDate.date_value >= start, DimDate.date_value <= end)
                .group_by(DimSku.id, DimSku.sku)
                .order_by(func.sum(FactSkuDaily.impressions_total).desc())
                .limit(200)
                .all()
            )

        items = []
        for r in rows:
            imp = int(r.impressions or 0)
            visits = int(r.card_visits or 0)
            add = int(r.add_to_cart or 0)
            orders = int(r.orders or 0)
            ctr = visits / imp if imp else 0
            add_rate = add / visits if visits else 0
            order_rate = orders / add if add else 0
            bottleneck = 'CTR' if ctr < 0.02 else ('加购率' if add_rate < 0.2 else ('下单率' if order_rate < 0.2 else '无'))
            items.append({
                'skuId': int(r.sku_id),
                'sku': r.sku,
                'impressions': imp,
                'cardVisits': visits,
                'addToCart': add,
                'orders': orders,
                'ctr': round(ctr, 4),
                'addRate': round(add_rate, 4),
                'orderRate': round(order_rate, 4),
                'bottleneck': bottleneck,
                'priority': 'P0' if bottleneck != '无' and orders < 5 else ('P1' if bottleneck != '无' else 'P3'),
                'recommendation': f'围绕{bottleneck}优化主图/价格/履约' if bottleneck != '无' else '漏斗健康，持续A/B测试',
            })
        issues = [x for x in items if x['bottleneck'] != '无']
        summary = {
            'avgCtr': round(sum(x['ctr'] for x in items) / len(items), 4) if items else 0,
            'avgAddRate': round(sum(x['addRate'] for x in items) / len(items), 4) if items else 0,
            'avgOrderRate': round(sum(x['orderRate'] for x in items) / len(items), 4) if items else 0,
            'totalOrders': sum(x['orders'] for x in items),
        }
        return {'summary': summary, 'rows': items, 'issues': issues[:30], 'recommendedActions': issues[:10]}

    def inventory_analysis(self) -> dict[str, object]:
        start, end = self._date_window()
        with get_session() as session:
            rows = (
                session.query(
                    DimSku.id.label('sku_id'),
                    DimSku.sku.label('sku'),
                    func.coalesce(func.avg(FactInventoryDaily.stock_total), 0).label('stock_total'),
                    func.coalesce(func.avg(FactInventoryDaily.days_of_supply), 0).label('days_supply'),
                    func.coalesce(func.sum(FactSkuDaily.orders_count), 0).label('orders'),
                )
                .join(FactInventoryDaily, FactInventoryDaily.sku_id == DimSku.id)
                .join(DimDate, FactInventoryDaily.date_id == DimDate.id)
                .outerjoin(FactSkuDaily, (FactSkuDaily.sku_id == DimSku.id) & (FactSkuDaily.date_id == FactInventoryDaily.date_id))
                .filter(FactInventoryDaily.shop_id == self.shop_id, DimDate.date_value >= start, DimDate.date_value <= end)
                .group_by(DimSku.id, DimSku.sku)
                .order_by(func.avg(FactInventoryDaily.days_of_supply).asc())
                .limit(200)
                .all()
            )

        items = []
        for r in rows:
            days = float(r.days_supply or 0)
            stock = float(r.stock_total or 0)
            sales_velocity = (float(r.orders or 0) / self.days) if self.days else 0
            reorder = max(1, int(sales_velocity * 7))
            safety = max(1, int(sales_velocity * 5))
            level = 'critical' if days < 7 else ('warning' if days < 14 else 'normal')
            items.append({
                'skuId': int(r.sku_id),
                'sku': r.sku,
                'stockTotal': int(stock),
                'daysOfSupply': round(days, 1),
                'salesVelocity': round(sales_velocity, 2),
                'safetyStock': safety,
                'reorderPoint': reorder,
                'alertLevel': level,
                'estimatedStockout': (date.today() + timedelta(days=max(1, int(days or 1)))).isoformat(),
                'recommendation': '优先补货并锁定在途' if level == 'critical' else ('制定补货计划' if level == 'warning' else '库存健康持续监控'),
            })
        summary = {
            'critical': len([x for x in items if x['alertLevel'] == 'critical']),
            'warning': len([x for x in items if x['alertLevel'] == 'warning']),
            'normal': len([x for x in items if x['alertLevel'] == 'normal']),
            'totalStock': sum(x['stockTotal'] for x in items),
            'avgDaysOfSupply': round(sum(x['daysOfSupply'] for x in items) / len(items), 2) if items else 0,
        }
        issues = [x for x in items if x['alertLevel'] != 'normal']
        return {'summary': summary, 'rows': items, 'issues': issues[:30], 'recommendedActions': issues[:10]}

    def ads_analysis(self) -> dict[str, object]:
        start, end = self._date_window()
        with get_session() as session:
            rows = (
                session.query(
                    DimSku.id.label('sku_id'),
                    DimSku.sku.label('sku'),
                    func.coalesce(func.sum(FactAdsDaily.ad_spend), 0.0).label('spend'),
                    func.coalesce(func.sum(FactAdsDaily.ad_revenue), 0.0).label('revenue'),
                    func.coalesce(func.sum(FactAdsDaily.ad_clicks), 0).label('clicks'),
                    func.coalesce(func.sum(FactAdsDaily.ad_orders), 0).label('orders'),
                    func.coalesce(func.avg(FactAdsDaily.cpc), 0.0).label('cpc'),
                    func.coalesce(func.avg(FactAdsDaily.roas), 0.0).label('roas'),
                    func.coalesce(func.sum(FactSkuDaily.impressions_total), 0).label('impressions'),
                )
                .join(FactAdsDaily, FactAdsDaily.sku_id == DimSku.id)
                .join(DimDate, FactAdsDaily.date_id == DimDate.id)
                .outerjoin(FactSkuDaily, (FactSkuDaily.sku_id == DimSku.id) & (FactSkuDaily.date_id == FactAdsDaily.date_id))
                .filter(FactAdsDaily.shop_id == self.shop_id, DimDate.date_value >= start, DimDate.date_value <= end)
                .group_by(DimSku.id, DimSku.sku)
                .order_by(func.sum(FactAdsDaily.ad_spend).desc())
                .limit(200)
                .all()
            )

        items = []
        for i, r in enumerate(rows):
            spend = float(r.spend or 0)
            revenue = float(r.revenue or 0)
            roas = float(r.roas or (revenue / spend if spend else 0))
            ctr = (int(r.clicks or 0) / int(r.impressions or 1)) if int(r.impressions or 0) else 0
            acos = (spend / revenue) if revenue else 0
            perf = 'excellent' if roas > 3 else ('good' if roas > 2 else ('poor' if roas > 1 else 'critical'))
            items.append({
                'skuId': int(r.sku_id),
                'sku': r.sku,
                'campaignName': f'Campaign-{r.sku}',
                'campaignStatus': 'active' if i % 4 != 0 else 'paused',
                'impressions': int(r.impressions or 0),
                'clicks': int(r.clicks or 0),
                'ctr': round(ctr, 4),
                'adSpend': round(spend, 2),
                'adRevenue': round(revenue, 2),
                'roas': round(roas, 2),
                'cpc': round(float(r.cpc or 0), 2),
                'acos': round(acos, 4),
                'orders': int(r.orders or 0),
                'avgOrderValue': round((revenue / int(r.orders or 1)) if int(r.orders or 0) else 0, 2),
                'performance': perf,
                'recommendation': '加预算扩量' if perf == 'excellent' else ('优化关键词与出价' if perf in ['good', 'poor'] else '建议暂停并重建计划'),
            })

        summary = {
            'totalSpend': round(sum(x['adSpend'] for x in items), 2),
            'totalRevenue': round(sum(x['adRevenue'] for x in items), 2),
            'avgRoas': round(sum(x['roas'] for x in items) / len(items), 3) if items else 0,
            'activeCampaigns': len([x for x in items if x['campaignStatus'] == 'active']),
        }
        issues = [x for x in items if x['performance'] in ['poor', 'critical']]
        return {'summary': summary, 'rows': items, 'issues': issues[:20], 'recommendedActions': issues[:10]}

    def push_action_to_strategy(
        self,
        *,
        source_page: str,
        sku: str,
        issue_summary: str,
        recommended_action: str,
        strategy_type: str,
        priority: str,
        operator: str,
    ) -> dict[str, object]:
        with get_session() as session:
            sku_row = session.query(DimSku).filter(DimSku.shop_id == self.shop_id, DimSku.sku == sku).first()
            source_payload = build_action_source(
                source_page=source_page,
                source_reason=issue_summary,
                source_module='analysis',
                extra={'operator': operator},
            )
            task = StrategyTask(
                shop_id=self.shop_id,
                sku_id=sku_row.id if sku_row else None,
                strategy_type=strategy_type,
                priority=priority,
                trigger_rule=f'{source_page}:manual_push',
                issue_summary=issue_summary,
                recommended_action=recommended_action,
                risk_note=json.dumps(source_payload, ensure_ascii=False),
                observation_metrics_json=[source_page],
                status='pending',
                owner=operator,
            )
            session.add(task)
            session.flush()
            return {
                'taskId': task.id,
                'status': 'success',
                'message': '已推送到策略清单，可在决策页继续确认执行',
                'tracking': {
                    'strategyStatus': 'pending',
                    'decisionStatus': 'not_entered',
                    'executionStatus': 'not_executed',
                    'sourcePage': source_page,
                },
            }
