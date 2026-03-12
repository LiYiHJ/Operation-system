from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, inspect

from ecom_v51.db.models import (
    AlertEvent,
    DimDate,
    DimSku,
    FactProfitSnapshot,
    FactReviewsDaily,
    FactSkuDaily,
    ImportBatch,
    StrategyTask,
    ReportSnapshot,
    ExecutionLog,
)
from ecom_v51.db.session import get_session, get_engine


class DashboardService:
    """Dashboard服务 - 经营开工台真数据聚合"""

    def __init__(self, shop_id: int = 1):
        self.shop_id = shop_id
        engine = get_engine()
        if 'execution_log' not in inspect(engine).get_table_names():
            ExecutionLog.metadata.create_all(bind=engine, tables=[ExecutionLog.__table__])

    @staticmethod
    def _sku_map(session, sku_ids: list[int]) -> dict[int, str]:
        if not sku_ids:
            return {}
        rows = session.query(DimSku.id, DimSku.sku).filter(DimSku.id.in_(sku_ids)).all()
        return {int(row.id): str(row.sku) for row in rows}

    def overview(self, days: int = 7) -> dict[str, object]:
        with get_session() as session:
            today = date.today()
            start_day = today - timedelta(days=max(days - 1, 0))

            totals = (
                session.query(
                    func.coalesce(func.sum(FactSkuDaily.revenue_ordered), 0.0).label('total_revenue'),
                    func.coalesce(func.sum(FactSkuDaily.orders_count), 0).label('total_orders'),
                    func.coalesce(func.sum(FactSkuDaily.impressions_total), 0).label('total_impressions'),
                    func.coalesce(func.sum(FactSkuDaily.card_visits), 0).label('total_clicks'),
                    func.count(func.distinct(FactSkuDaily.sku_id)).label('total_products'),
                )
                .join(DimDate, FactSkuDaily.date_id == DimDate.id)
                .filter(DimDate.date_value >= start_day, DimDate.date_value <= today)
                .one()
            )

            profit = (
                session.query(
                    func.coalesce(func.sum(FactProfitSnapshot.net_profit), 0.0).label('net_profit'),
                )
                .join(DimDate, FactProfitSnapshot.date_id == DimDate.id)
                .filter(DimDate.date_value >= start_day, DimDate.date_value <= today)
                .one()
            )

            rating = (
                session.query(
                    func.coalesce(func.avg(FactReviewsDaily.rating_avg), 0.0).label('avg_rating'),
                )
                .join(DimDate, FactReviewsDaily.date_id == DimDate.id)
                .filter(DimDate.date_value >= start_day, DimDate.date_value <= today)
                .one()
            )

            previous_start = start_day - timedelta(days=days)
            previous_end = start_day - timedelta(days=1)
            previous_totals = (
                session.query(
                    func.coalesce(func.sum(FactSkuDaily.revenue_ordered), 0.0).label('total_revenue'),
                    func.coalesce(func.sum(FactSkuDaily.orders_count), 0).label('total_orders'),
                )
                .join(DimDate, FactSkuDaily.date_id == DimDate.id)
                .filter(DimDate.date_value >= previous_start, DimDate.date_value <= previous_end)
                .one()
            )

            trend_rows = (
                session.query(
                    DimDate.date_value,
                    func.coalesce(func.sum(FactSkuDaily.revenue_ordered), 0.0).label('revenue'),
                    func.coalesce(func.sum(FactSkuDaily.orders_count), 0).label('orders'),
                )
                .join(DimDate, FactSkuDaily.date_id == DimDate.id)
                .filter(DimDate.date_value >= start_day, DimDate.date_value <= today)
                .group_by(DimDate.date_value)
                .order_by(DimDate.date_value)
                .all()
            )

            top_skus = (
                session.query(
                    DimSku.sku.label('sku'),
                    func.coalesce(func.sum(FactSkuDaily.revenue_ordered), 0.0).label('revenue'),
                    func.coalesce(func.sum(FactSkuDaily.orders_count), 0).label('orders'),
                    func.coalesce(func.avg(FactProfitSnapshot.net_margin), 0.0).label('margin'),
                )
                .join(FactSkuDaily, FactSkuDaily.sku_id == DimSku.id)
                .outerjoin(
                    FactProfitSnapshot,
                    (FactProfitSnapshot.sku_id == DimSku.id) & (FactProfitSnapshot.date_id == FactSkuDaily.date_id),
                )
                .join(DimDate, FactSkuDaily.date_id == DimDate.id)
                .filter(DimDate.date_value >= start_day, DimDate.date_value <= today)
                .group_by(DimSku.sku)
                .order_by(func.sum(FactSkuDaily.revenue_ordered).desc())
                .limit(5)
                .all()
            )

            alerts = (
                session.query(AlertEvent)
                .order_by(AlertEvent.detected_at.desc())
                .limit(8)
                .all()
            )

            recent_imports = (
                session.query(ImportBatch)
                .order_by(ImportBatch.created_at.desc())
                .limit(5)
                .all()
            )
            recent_strategies = (
                session.query(StrategyTask)
                .order_by(StrategyTask.created_at.desc())
                .limit(5)
                .all()
            )
            recent_exec = (
                session.query(ExecutionLog)
                .join(StrategyTask, StrategyTask.id == ExecutionLog.strategy_task_id)
                .filter(StrategyTask.shop_id == self.shop_id)
                .order_by(ExecutionLog.confirmed_at.desc())
                .limit(5)
                .all()
            )

            sku_map = self._sku_map(session, [int(x.sku_id) for x in alerts if x.sku_id])

            total_revenue = float(totals.total_revenue or 0.0)
            total_orders = int(totals.total_orders or 0)
            avg_order_value = total_revenue / total_orders if total_orders else 0.0
            net_profit = float(profit.net_profit or 0.0)
            profit_margin = net_profit / total_revenue if total_revenue else 0.0
            total_clicks = int(totals.total_clicks or 0)
            total_impressions = int(totals.total_impressions or 0)
            avg_ctr = total_clicks / total_impressions if total_impressions else 0.0

            must_handle_today = [
                {
                    'type': self._severity_to_priority(a.severity),
                    'message': a.message,
                    'sku': sku_map.get(int(a.sku_id), str(a.sku_id or '-')) if a.sku_id else '-',
                    'action': '立即处理',
                }
                for a in alerts[:5]
            ]

            return {
                'totalRevenue': round(total_revenue, 2),
                'totalOrders': total_orders,
                'avgOrderValue': round(avg_order_value, 2),
                'profitMargin': round(profit_margin, 4),
                'totalProducts': int(totals.total_products or 0),
                'totalImpressions': total_impressions,
                'totalClicks': total_clicks,
                'avgCtr': round(avg_ctr, 4),
                'avgRating': round(float(rating.avg_rating or 0.0), 2),
                'period': {'start': start_day.isoformat(), 'end': today.isoformat()},
                'kpiDeltas': {
                    'revenue': self._pct_delta(total_revenue, float(previous_totals.total_revenue or 0.0)),
                    'orders': self._pct_delta(float(total_orders), float(previous_totals.total_orders or 0.0)),
                    'avgOrderValue': self._pct_delta(avg_order_value, (float(previous_totals.total_revenue or 0.0) / float(previous_totals.total_orders or 1)) if float(previous_totals.total_orders or 0) else 0.0),
                },
                'topSkus': [
                    {
                        'sku': row.sku,
                        'revenue': float(row.revenue or 0.0),
                        'orders': int(row.orders or 0),
                        'margin': float(row.margin or 0.0),
                        'abcClass': self._abc_class(i),
                    }
                    for i, row in enumerate(top_skus)
                ],
                'alerts': [
                    {
                        'type': self._severity_to_priority(row.severity),
                        'message': row.message,
                        'sku': sku_map.get(int(row.sku_id), str(row.sku_id or '-')) if row.sku_id else '-',
                        'timestamp': row.detected_at.isoformat() if row.detected_at else None,
                    }
                    for row in alerts
                ],
                'trends': {
                    'dates': [row.date_value.strftime('%m-%d') for row in trend_rows],
                    'revenue': [float(row.revenue or 0.0) for row in trend_rows],
                    'orders': [int(row.orders or 0) for row in trend_rows],
                },
                'openingWorkbench': {
                    'todaySummary': {
                        'todayRevenue': round(total_revenue, 2),
                        'todayOrders': total_orders,
                        'todayProfitMargin': round(profit_margin, 4),
                        'pendingAlerts': len(alerts),
                        'pendingStrategies': len([x for x in recent_strategies if x.status in ['pending', 'in_progress']]),
                    },
                    'mustHandleToday': must_handle_today,
                    'recentChanges': {
                        'recentImports': [
                            {
                                'batchId': x.id,
                                'status': x.status,
                                'successCount': x.success_count,
                                'errorCount': x.error_count,
                                'createdAt': x.created_at.isoformat() if x.created_at else None,
                            }
                            for x in recent_imports
                        ],
                        'recentStrategies': [
                            {
                                'taskId': x.id,
                                'priority': x.priority,
                                'status': x.status,
                                'issue': x.issue_summary,
                                'createdAt': x.created_at.isoformat() if x.created_at else None,
                            }
                            for x in recent_strategies
                        ],
                        'recentExecution': [
                            {
                                'executionId': x.id,
                                'taskId': x.strategy_task_id,
                                'generatedAt': x.confirmed_at.isoformat() if x.confirmed_at else None,
                                'resultSummary': x.result_summary,
                                'reportType': 'strategy_execution',
                            }
                            for x in recent_exec
                        ],
                    },
                },
            }

    @staticmethod
    def _abc_class(index: int) -> str:
        if index < 2:
            return 'A'
        if index < 4:
            return 'B'
        return 'C'

    @staticmethod
    def _severity_to_priority(severity: str | None) -> str:
        mapping = {'critical': 'P0', 'high': 'P1', 'medium': 'P2', 'low': 'P3'}
        return mapping.get((severity or '').lower(), 'P2')


    @staticmethod
    def _pct_delta(current: float, previous: float) -> float | None:
        if previous == 0:
            return None
        return round((current - previous) / previous, 4)
