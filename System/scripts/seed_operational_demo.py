from __future__ import annotations

import csv
import json
from datetime import date, datetime, timedelta
from pathlib import Path

from ecom_v51.db.base import Base
from ecom_v51.db.models import (
    AlertEvent,
    DimCampaign,
    DimDate,
    DimPlatform,
    DimShop,
    DimSku,
    ExecutionLog,
    FactAdsDaily,
    FactInventoryDaily,
    FactOrdersDaily,
    FactProfitSnapshot,
    FactReviewsDaily,
    FactSkuDaily,
    ImportBatch,
    ImportBatchFile,
    ImportErrorLog,
    ReminderReadState,
    ReportSnapshot,
    StrategyTask,
)
from ecom_v51.db.session import get_engine, get_session
from ecom_v51.services.import_service import ImportService
from ecom_v51.services.strategy_service import StrategyTaskService, build_action_source

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / 'sample_data' / 'p4_demo_import.csv'
SHOP_ID = 1


def ensure_schema() -> None:
    Base.metadata.create_all(bind=get_engine())


def reset_demo_data() -> None:
    with get_session() as session:
        session.query(ExecutionLog).delete(synchronize_session=False)
        session.query(ReportSnapshot).delete(synchronize_session=False)
        session.query(AlertEvent).filter(AlertEvent.shop_id == SHOP_ID).delete(synchronize_session=False)
        session.query(StrategyTask).filter(StrategyTask.shop_id == SHOP_ID).delete(synchronize_session=False)

        session.query(FactAdsDaily).filter(FactAdsDaily.shop_id == SHOP_ID).delete(synchronize_session=False)
        session.query(FactInventoryDaily).filter(FactInventoryDaily.shop_id == SHOP_ID).delete(synchronize_session=False)
        session.query(FactOrdersDaily).filter(FactOrdersDaily.shop_id == SHOP_ID).delete(synchronize_session=False)
        session.query(FactReviewsDaily).filter(FactReviewsDaily.shop_id == SHOP_ID).delete(synchronize_session=False)
        session.query(FactProfitSnapshot).filter(FactProfitSnapshot.shop_id == SHOP_ID).delete(synchronize_session=False)
        session.query(FactSkuDaily).filter(FactSkuDaily.shop_id == SHOP_ID).delete(synchronize_session=False)

        session.query(ImportErrorLog).delete(synchronize_session=False)
        session.query(ImportBatchFile).delete(synchronize_session=False)
        session.query(ImportBatch).delete(synchronize_session=False)
        session.query(ReminderReadState).delete(synchronize_session=False)
        session.query(DimCampaign).filter(DimCampaign.shop_id == SHOP_ID).delete(synchronize_session=False)
        session.query(DimSku).filter(DimSku.shop_id == SHOP_ID).delete(synchronize_session=False)


def ensure_dims() -> None:
    with get_session() as session:
        platform = session.query(DimPlatform).filter(DimPlatform.platform_code == 'ozon').one_or_none()
        if not platform:
            platform = DimPlatform(platform_code='ozon', platform_name='Ozon', is_active=True)
            session.add(platform)
            session.flush()

        shop = session.query(DimShop).filter(DimShop.id == SHOP_ID).one_or_none()
        if not shop:
            shop = DimShop(
                id=SHOP_ID,
                platform_id=platform.id,
                shop_code='demo-shop-1',
                shop_name='Demo 运营店铺',
                currency_code='RUB',
                timezone='Europe/Moscow',
                status='active',
            )
            session.add(shop)


def ensure_date(session, d: date) -> DimDate:
    row = session.query(DimDate).filter(DimDate.date_value == d).one_or_none()
    if row:
        return row
    row = DimDate(date_value=d, year=d.year, month=d.month, day=d.day, week_of_year=d.isocalendar().week)
    session.add(row)
    session.flush()
    return row


def read_demo_rows() -> list[dict]:
    with CSV_PATH.open('r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def run_import_chain() -> tuple[int, int]:
    svc = ImportService()
    parsed = svc.parse_import_file(str(CSV_PATH), shop_id=SHOP_ID, operator='seed_script')
    confirm = svc.confirm_import(
        session_id=int(parsed['sessionId']),
        shop_id=SHOP_ID,
        manual_overrides=[],
        operator='seed_script',
    )
    return int(parsed['sessionId']), int(confirm['batchId'])


def seed_timeseries(batch_id: int) -> None:
    rows = read_demo_rows()
    with get_session() as session:
        campaigns: dict[str, int] = {}
        for idx, r in enumerate(rows):
            c = DimCampaign(
                shop_id=SHOP_ID,
                campaign_code=f"CMP-{idx+1:02d}",
                campaign_name=f"活动计划-{r['SKU']}",
                status='active' if idx % 3 != 0 else 'paused',
            )
            session.add(c)
            session.flush()
            campaigns[r['SKU']] = c.id

        sku_map = {x.sku: x.id for x in session.query(DimSku).filter(DimSku.shop_id == SHOP_ID).all()}

        today = date.today()
        for offset in range(7):
            d = today - timedelta(days=offset)
            date_dim = ensure_date(session, d)
            trend_factor = 1 + ((6 - offset) * 0.04)

            for idx, r in enumerate(rows):
                sku_id = sku_map[r['SKU']]
                impressions = int(float(r['Impressions']) * trend_factor)
                visits = int(float(r['Card visits']) * trend_factor)
                add_to_cart = int(float(r['Add to Cart']) * trend_factor)
                orders = int(float(r['Orders']) * trend_factor)
                revenue = float(r['Revenue']) * trend_factor
                returns = max(0, int(float(r['Returns']) + (1 if idx % 3 == 0 and offset < 2 else 0)))

                sku_daily = session.query(FactSkuDaily).filter(
                    FactSkuDaily.date_id == date_dim.id,
                    FactSkuDaily.shop_id == SHOP_ID,
                    FactSkuDaily.sku_id == sku_id,
                ).one_or_none() or FactSkuDaily(date_id=date_dim.id, shop_id=SHOP_ID, sku_id=sku_id, batch_id=batch_id)
                session.add(sku_daily)
                sku_daily.impressions_total = impressions
                sku_daily.card_visits = visits
                sku_daily.add_to_cart_total = add_to_cart
                sku_daily.orders_count = orders
                sku_daily.delivered_count = max(0, orders - 1)
                sku_daily.cancelled_count = 1 if idx % 4 == 0 else 0
                sku_daily.returned_count = returns
                sku_daily.revenue_ordered = revenue
                sku_daily.revenue_delivered = revenue * 0.97
                sku_daily.batch_id = batch_id

                sale_price = float(r['sale_price'])
                list_price = float(r['list_price'])
                fixed_cost = float(r['cost_price'])
                var_rate = float(r['commission_rate'])
                net_profit = revenue - (revenue * var_rate) - (orders * fixed_cost)
                net_margin = (net_profit / revenue) if revenue else 0

                profit = session.query(FactProfitSnapshot).filter(
                    FactProfitSnapshot.date_id == date_dim.id,
                    FactProfitSnapshot.shop_id == SHOP_ID,
                    FactProfitSnapshot.sku_id == sku_id,
                ).one_or_none() or FactProfitSnapshot(
                    date_id=date_dim.id,
                    shop_id=SHOP_ID,
                    sku_id=sku_id,
                    batch_id=batch_id,
                    sale_price=sale_price,
                    list_price=list_price,
                    fixed_cost_total=fixed_cost,
                    variable_rate_total=var_rate,
                    base_profit=0,
                    contribution_profit=0,
                    post_fulfillment_profit=0,
                    net_profit=0,
                    net_margin=0,
                    break_even_price=fixed_cost,
                    break_even_discount_ratio=0,
                )
                session.add(profit)
                profit.sale_price = sale_price
                profit.list_price = list_price
                profit.fixed_cost_total = fixed_cost
                profit.variable_rate_total = var_rate
                profit.base_profit = net_profit
                profit.contribution_profit = net_profit
                profit.post_fulfillment_profit = net_profit
                profit.net_profit = net_profit
                profit.net_margin = net_margin
                profit.break_even_price = fixed_cost / max(1 - var_rate, 0.01)
                profit.break_even_discount_ratio = max(0.0, 1 - (profit.break_even_price / list_price))
                profit.batch_id = batch_id

                inv = session.query(FactInventoryDaily).filter(
                    FactInventoryDaily.date_id == date_dim.id,
                    FactInventoryDaily.shop_id == SHOP_ID,
                    FactInventoryDaily.sku_id == sku_id,
                ).one_or_none() or FactInventoryDaily(date_id=date_dim.id, shop_id=SHOP_ID, sku_id=sku_id, batch_id=batch_id)
                session.add(inv)
                stock = max(8, int(float(r['Stock']) - offset * (orders / 4)))
                inv.stock_total = stock
                inv.stock_fbo = int(stock * 0.8)
                inv.stock_fbs = stock - inv.stock_fbo
                inv.days_of_supply = round(stock / max(orders, 1), 2)
                inv.batch_id = batch_id

                ads = session.query(FactAdsDaily).filter(
                    FactAdsDaily.date_id == date_dim.id,
                    FactAdsDaily.shop_id == SHOP_ID,
                    FactAdsDaily.sku_id == sku_id,
                ).one_or_none() or FactAdsDaily(date_id=date_dim.id, shop_id=SHOP_ID, sku_id=sku_id, batch_id=batch_id)
                session.add(ads)
                spend = float(r['Ad spend']) * (0.85 + 0.05 * (6 - offset))
                ad_orders = max(1, int(float(r['Ad orders']) * trend_factor))
                ad_revenue = ad_orders * sale_price
                ads.campaign_id = campaigns[r['SKU']]
                ads.ad_spend = round(spend, 2)
                ads.ad_clicks = max(5, int(spend / 5.2))
                ads.ad_orders = ad_orders
                ads.ad_revenue = round(ad_revenue, 2)
                ads.cpc = round(ads.ad_spend / max(ads.ad_clicks, 1), 2)
                ads.roas = round(ads.ad_revenue / max(ads.ad_spend, 1), 2)
                ads.batch_id = batch_id

                od = session.query(FactOrdersDaily).filter(
                    FactOrdersDaily.date_id == date_dim.id,
                    FactOrdersDaily.shop_id == SHOP_ID,
                    FactOrdersDaily.sku_id == sku_id,
                ).one_or_none() or FactOrdersDaily(date_id=date_dim.id, shop_id=SHOP_ID, sku_id=sku_id, batch_id=batch_id)
                session.add(od)
                od.ordered_qty = orders
                od.delivered_qty = max(0, orders - 1)
                od.cancelled_qty = 1 if idx % 4 == 0 else 0
                od.returned_qty = returns
                od.ordered_amount = revenue
                od.delivered_amount = revenue * 0.97
                od.batch_id = batch_id

                rv = session.query(FactReviewsDaily).filter(
                    FactReviewsDaily.date_id == date_dim.id,
                    FactReviewsDaily.shop_id == SHOP_ID,
                    FactReviewsDaily.sku_id == sku_id,
                ).one_or_none() or FactReviewsDaily(date_id=date_dim.id, shop_id=SHOP_ID, sku_id=sku_id, batch_id=batch_id)
                session.add(rv)
                rating = max(3.5, float(r['Rating']) - (0.1 if idx % 5 == 0 and offset < 2 else 0))
                rv.rating_avg = round(rating, 2)
                rv.new_reviews_count = int(float(r['Reviews']) * (0.8 + 0.03 * offset))
                rv.negative_reviews_count = 1 if rating < 4.2 else 0
                rv.quality_risk_score = round(max(0, 5 - rating) / 5, 2)
                rv.batch_id = batch_id


def seed_alerts_and_strategy(batch_id: int) -> None:
    with get_session() as session:
        sku_map = {x.sku: x.id for x in session.query(DimSku).filter(DimSku.shop_id == SHOP_ID).all()}

        alerts = [
            ('SKU-MAT-02', 'inventory_risk', 'critical', '库存周转过低，预计3天内断货'),
            ('SKU-BAG-01', 'margin_drop', 'high', '活动期利润率下降，建议调价'),
            ('SKU-THERMO-02', 'ads_low_roas', 'medium', '广告ROAS低于目标值，请优化投放'),
        ]
        for sku, typ, sev, msg in alerts:
            session.add(AlertEvent(
                shop_id=SHOP_ID,
                sku_id=sku_map.get(sku),
                alert_type=typ,
                severity=sev,
                message=msg,
                detected_at=datetime.utcnow() - timedelta(hours=1),
                status='open',
            ))

        # 制造导入异常与提醒来源
        file_row = session.query(ImportBatchFile).order_by(ImportBatchFile.id.desc()).first()
        if file_row:
            session.add(ImportErrorLog(
                batch_file_id=file_row.id,
                row_no=3,
                column_name='commission_rate',
                error_type='normalize_warning',
                raw_value='1.8',
                error_message='佣金率疑似异常，已按百分比规范化处理',
            ))

        tasks = [
            ('price', 'pricing', 'P0', '价格竞争力页识别同品低价冲击', '提高SKU-MAT-02售价并重算活动折扣'),
            ('inventory', 'inventory', 'P1', '库存预警页识别补货风险', 'SKU-MAT-02 立即补货并降低广告预算'),
            ('ads', 'ads', 'P1', '广告页识别低ROAS投放', '暂停低效关键词，保留高转化词'),
            ('funnel', 'conversion', 'P2', '漏斗页识别加购到下单流失', '优化详情页利益点并补充信任背书'),
            ('abc', 'abc', 'P2', 'ABC页识别高营收低毛利', '对A类SKU优化费用与定价结构'),
        ]
        created_ids = []
        for source_page, strategy_type, priority, reason, action in tasks:
            sku_id = next(iter(sku_map.values()), None)
            task = StrategyTask(
                shop_id=SHOP_ID,
                sku_id=sku_id,
                strategy_type=strategy_type,
                priority=priority,
                trigger_rule=f'{source_page}:seed',
                issue_summary=reason,
                recommended_action=action,
                risk_note=json.dumps(build_action_source(source_page=source_page, source_reason=reason, source_module='seed'), ensure_ascii=False),
                observation_metrics_json=[source_page],
                status='pending',
                owner='operator',
                due_date=date.today() + timedelta(days=1),
            )
            session.add(task)
            session.flush()
            created_ids.append(task.id)

    # 生成执行留痕（部分已执行，部分待执行）
    StrategyTaskService().decision_confirm(selected_task_ids=created_ids[:2], operator='operator')


def summarize() -> None:
    with get_session() as session:
        print('--- Seed Summary ---')
        print('SKU:', session.query(DimSku).filter(DimSku.shop_id == SHOP_ID).count())
        print('FactSkuDaily:', session.query(FactSkuDaily).filter(FactSkuDaily.shop_id == SHOP_ID).count())
        print('FactProfitSnapshot:', session.query(FactProfitSnapshot).filter(FactProfitSnapshot.shop_id == SHOP_ID).count())
        print('FactInventoryDaily:', session.query(FactInventoryDaily).filter(FactInventoryDaily.shop_id == SHOP_ID).count())
        print('FactAdsDaily:', session.query(FactAdsDaily).filter(FactAdsDaily.shop_id == SHOP_ID).count())
        print('FactOrdersDaily:', session.query(FactOrdersDaily).filter(FactOrdersDaily.shop_id == SHOP_ID).count())
        print('FactReviewsDaily:', session.query(FactReviewsDaily).filter(FactReviewsDaily.shop_id == SHOP_ID).count())
        print('StrategyTask:', session.query(StrategyTask).filter(StrategyTask.shop_id == SHOP_ID).count())
        print('ExecutionLog:', session.query(ExecutionLog).count())
        print('Alerts:', session.query(AlertEvent).filter(AlertEvent.shop_id == SHOP_ID).count())


def main() -> None:
    print('[P4] 初始化可运营样本链路...')
    ensure_schema()
    reset_demo_data()
    ensure_dims()
    session_id, batch_id = run_import_chain()
    seed_timeseries(batch_id=batch_id)
    seed_alerts_and_strategy(batch_id=batch_id)
    summarize()
    print(f'[P4] 完成: import_session={session_id}, batch_id={batch_id}, csv={CSV_PATH}')


if __name__ == '__main__':
    main()
