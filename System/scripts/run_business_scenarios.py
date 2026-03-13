#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import date, datetime

from ecom_v51.db.models import DimDate, DimPlatform, DimShop, DimSku, FactAdsDaily, FactOrdersDaily, FactProfitSnapshot, FactReviewsDaily, FactSkuDaily
from ecom_v51.db.session import get_session
from ecom_v51.services.analysis_service import AnalysisService
from ecom_v51.services.dashboard_service import DashboardService


def ensure_base() -> tuple[int, int]:
    with get_session() as s:
        platform = s.query(DimPlatform).filter(DimPlatform.platform_code == 'ozon').one_or_none()
        if platform is None:
            platform = DimPlatform(platform_code='ozon', platform_name='Ozon', is_active=True)
            s.add(platform)
            s.flush()
        shop = s.query(DimShop).filter(DimShop.id == 1).one_or_none()
        if shop is None:
            shop = DimShop(id=1, platform_id=platform.id, shop_code='shop-1', shop_name='Shop 1', currency_code='RUB', timezone='Europe/Moscow', status='active')
            s.add(shop)
            s.flush()
        d = s.query(DimDate).filter(DimDate.date_value == date.today()).one_or_none()
        if d is None:
            d = DimDate(date_value=date.today(), year=date.today().year, month=date.today().month, day=date.today().day, week_of_year=date.today().isocalendar().week)
            s.add(d)
            s.flush()
        return shop.id, d.id


def upsert_sku(shop_id: int, date_id: int, sku: str, *, impressions: int, visits: int, add: int, orders: int, revenue: float,
              canceled: int = 0, returned: int = 0, rating: float = 4.5, reviews: int = 5, ad_spend: float = 200, ad_orders: int = 2,
              sale_price: float = 100, list_price: float = 120, net_margin: float = 0.2) -> None:
    with get_session() as s:
        dim = s.query(DimSku).filter(DimSku.shop_id == shop_id, DimSku.sku == sku).one_or_none()
        if dim is None:
            dim = DimSku(shop_id=shop_id, sku=sku, sku_name=sku, status='active', is_active=True)
            s.add(dim)
            s.flush()

        f = s.query(FactSkuDaily).filter(FactSkuDaily.shop_id == shop_id, FactSkuDaily.date_id == date_id, FactSkuDaily.sku_id == dim.id).one_or_none()
        if f is None:
            f = FactSkuDaily(shop_id=shop_id, date_id=date_id, sku_id=dim.id, batch_id=1)
            s.add(f)
        f.impressions_total = impressions
        f.card_visits = visits
        f.add_to_cart_total = add
        f.orders_count = orders
        f.cancelled_count = canceled
        f.returned_count = returned
        f.revenue_ordered = revenue
        f.revenue_delivered = revenue

        fo = s.query(FactOrdersDaily).filter(FactOrdersDaily.shop_id == shop_id, FactOrdersDaily.date_id == date_id, FactOrdersDaily.sku_id == dim.id).one_or_none()
        if fo is None:
            fo = FactOrdersDaily(shop_id=shop_id, date_id=date_id, sku_id=dim.id, batch_id=1)
            s.add(fo)
        fo.ordered_qty = orders
        fo.delivered_qty = max(0, orders - canceled - returned)
        fo.cancelled_qty = canceled
        fo.returned_qty = returned
        fo.ordered_amount = revenue
        fo.delivered_amount = revenue

        fr = s.query(FactReviewsDaily).filter(FactReviewsDaily.shop_id == shop_id, FactReviewsDaily.date_id == date_id, FactReviewsDaily.sku_id == dim.id).one_or_none()
        if fr is None:
            fr = FactReviewsDaily(shop_id=shop_id, date_id=date_id, sku_id=dim.id, batch_id=1)
            s.add(fr)
        fr.rating_avg = rating
        fr.new_reviews_count = reviews
        fr.quality_risk_score = max(0.0, 5.0 - rating)

        fa = s.query(FactAdsDaily).filter(FactAdsDaily.shop_id == shop_id, FactAdsDaily.date_id == date_id, FactAdsDaily.sku_id == dim.id).one_or_none()
        if fa is None:
            fa = FactAdsDaily(shop_id=shop_id, date_id=date_id, sku_id=dim.id, campaign_id=None, batch_id=1)
            s.add(fa)
        fa.ad_spend = ad_spend
        fa.ad_orders = ad_orders
        fa.ad_revenue = revenue * 0.3
        fa.ad_clicks = max(1, int(visits * 0.5))
        fa.cpc = fa.ad_spend / fa.ad_clicks
        fa.roas = (fa.ad_revenue / fa.ad_spend) if fa.ad_spend else 0

        fp = s.query(FactProfitSnapshot).filter(FactProfitSnapshot.shop_id == shop_id, FactProfitSnapshot.date_id == date_id, FactProfitSnapshot.sku_id == dim.id).one_or_none()
        if fp is None:
            fp = FactProfitSnapshot(shop_id=shop_id, date_id=date_id, sku_id=dim.id, batch_id=1, sale_price=sale_price, list_price=list_price,
                                    fixed_cost_total=60, variable_rate_total=0.25, base_profit=0, contribution_profit=0, post_fulfillment_profit=0,
                                    net_profit=0, net_margin=0, break_even_price=0, break_even_discount_ratio=0)
            s.add(fp)
        fp.sale_price = sale_price
        fp.list_price = list_price
        fp.net_margin = net_margin
        fp.net_profit = revenue * net_margin


def run() -> None:
    shop_id, date_id = ensure_base()

    scenarios = [
        ('S1_HIGH_EXPOSURE_LOW_CLICK', dict(impressions=20000, visits=120, add=30, orders=8, revenue=1200, ad_spend=80, ad_orders=2, net_margin=0.25)),
        ('S2_HIGH_CLICK_LOW_CART', dict(impressions=6000, visits=1800, add=45, orders=18, revenue=2500, ad_spend=240, ad_orders=4, net_margin=0.22)),
        ('S3_HIGH_CART_LOW_ORDER', dict(impressions=7000, visits=1700, add=480, orders=35, revenue=3600, ad_spend=260, ad_orders=5, net_margin=0.18)),
        ('S4_ORDER_OK_HIGH_RETURN_CANCEL', dict(impressions=5000, visits=900, add=300, orders=120, revenue=8400, canceled=25, returned=30, rating=3.8, reviews=22, ad_spend=280, ad_orders=10, net_margin=0.08)),
        ('S5_GOOD_SALES_BAD_AD_EFF', dict(impressions=9000, visits=2000, add=600, orders=220, revenue=21000, ad_spend=5200, ad_orders=25, net_margin=0.16)),
        ('S6_HIGH_REVENUE_LOW_MARGIN', dict(impressions=12000, visits=2200, add=650, orders=260, revenue=26000, canceled=12, returned=18, rating=4.0, reviews=30, ad_spend=6000, ad_orders=22, sale_price=88, list_price=160, net_margin=0.03)),
    ]

    for code, payload in scenarios:
        upsert_sku(shop_id, date_id, code, **payload)

    analysis = AnalysisService(shop_id=shop_id, days=7)
    abc = analysis.abc_analysis()
    funnel = analysis.funnel_analysis()
    price = analysis.price_cockpit('daily')
    ads = analysis.ads_analysis()
    dash = DashboardService(shop_id=shop_id).overview(7)

    checks = {
        'scenario_1_detect_low_ctr': any(r['sku'] == 'S1_HIGH_EXPOSURE_LOW_CLICK' and r['bottleneck'] == 'CTR' for r in funnel['rows']),
        'scenario_2_detect_low_add_rate': any(r['sku'] == 'S2_HIGH_CLICK_LOW_CART' and r['bottleneck'] == '加购率' for r in funnel['rows']),
        'scenario_3_detect_low_order_rate': any(r['sku'] == 'S3_HIGH_CART_LOW_ORDER' and r['bottleneck'] == '下单率' for r in funnel['rows']),
        'scenario_4_in_abc_issue': any(r['sku'] == 'S4_ORDER_OK_HIGH_RETURN_CANCEL' and r['issue'] != '结构健康' for r in abc['rows']),
        'scenario_5_ads_spend_detected': ads['summary']['totalSpend'] > 0,
        'scenario_6_low_margin_detected': any(r['sku'] == 'S6_HIGH_REVENUE_LOW_MARGIN' and r['margin'] < 0.08 for r in price['batchRecommendations']),
        'dashboard_non_zero': dash['totalRevenue'] > 0 and dash['totalOrders'] > 0,
    }

    print(json.dumps({
        'generatedAt': datetime.utcnow().isoformat(),
        'scenarioCount': len(scenarios),
        'checks': checks,
        'passCount': len([v for v in checks.values() if v]),
        'failCount': len([v for v in checks.values() if not v]),
        'samples': {
            'dashboard': {'totalRevenue': dash['totalRevenue'], 'totalOrders': dash['totalOrders'], 'profitMargin': dash['profitMargin']},
            'funnelRows': funnel['rows'][:3],
            'priceRows': price['batchRecommendations'][:3],
            'adsSummary': ads['summary'],
        }
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    run()
