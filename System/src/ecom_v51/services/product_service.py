from __future__ import annotations
from datetime import date, timedelta
from typing import List, Dict, Any

from dataclasses import asdict
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session

from ecom_v51.models import SkuSnapshot
from ecom_v51.war_room import WarRoomService
from ecom_v51.db.session import get_session
from ecom_v51.db.models import (
    DimSku,
    DimShop,
    DimProduct,
    DimCategory,
    FactSkuDaily,
    FactAdsDaily,
    FactProfitSnapshot,
    FactInventoryDaily,
    DimDate
)


class ProductService:
    """产品服务 - 连接真实数据库"""
    
    def list_products(self, query: str = "") -> list[dict[str, object]]:
        """
        从数据库查询产品列表
        
        Args:
            query: 搜索关键词（SKU、产品名称、类目等）
        
        Returns:
            产品列表
        """
        with get_session() as session:
            # 获取最近7天的日期
            today = date.today()
            seven_days_ago = today - timedelta(days=7)
            
            # 查询SKU及其最近7天的汇总数据
            query_obj = (
                session.query(
                    DimSku.sku,
                    DimShop.shop_name,
                    DimCategory.category_name,
                    func.sum(FactSkuDaily.revenue_ordered).label('sales'),
                    func.sum(FactSkuDaily.orders_count).label('orders'),
                    func.sum(FactSkuDaily.card_visits).label('total_card_visits'),
                    func.sum(FactSkuDaily.impressions_total).label('total_impressions'),
                    func.sum(FactSkuDaily.add_to_cart_total).label('total_add_to_cart'),
                )
                .join(DimShop, DimSku.shop_id == DimShop.id)
                .outerjoin(DimProduct, DimSku.product_id == DimProduct.id)
                .outerjoin(DimCategory, DimProduct.category_id == DimCategory.id)
                .join(FactSkuDaily, DimSku.id == FactSkuDaily.sku_id)
                .join(DimDate, FactSkuDaily.date_id == DimDate.id)
                .filter(DimDate.date_value >= seven_days_ago)
                .group_by(
                    DimSku.id,
                    DimSku.sku,
                    DimShop.shop_name,
                    DimCategory.category_name
                )
            )
            
            # 如果有搜索关键词，添加过滤条件
            if query:
                query_lower = f"%{query.lower()}%"
                query_obj = query_obj.filter(
                    or_(
                        DimSku.sku.ilike(query_lower),
                        DimProduct.product_name.ilike(query_lower),
                        DimCategory.category_name.ilike(query_lower),
                        DimShop.shop_name.ilike(query_lower)
                    )
                )
            
            results = query_obj.limit(100).all()
            
            # 构建返回数据
            products = []
            for row in results:
                # 计算CTR和加购率
                ctr = (
                    float(row.total_card_visits) / float(row.total_impressions)
                    if row.total_impressions and row.total_impressions > 0
                    else 0
                )
                add_to_cart_rate = (
                    float(row.total_add_to_cart) / float(row.total_card_visits)
                    if row.total_card_visits and row.total_card_visits > 0
                    else 0
                )
                
                # 查询该SKU的广告ROI（最近7天）
                ad_data = (
                    session.query(
                        func.sum(FactAdsDaily.ad_spend).label('total_ad_spend'),
                        func.sum(FactAdsDaily.ad_revenue).label('total_ad_revenue')
                    )
                    .join(DimDate, FactAdsDaily.date_id == DimDate.id)
                    .filter(
                        and_(
                            FactAdsDaily.sku_id == DimSku.id,
                            DimDate.date_value >= seven_days_ago
                        )
                    )
                    .first()
                )
                
                ad_roi = (
                    float(ad_data.total_ad_revenue) / float(ad_data.total_ad_spend)
                    if ad_data and ad_data.total_ad_spend and ad_data.total_ad_spend > 0
                    else 0
                )
                
                # 查询库存天数
                inventory_data = (
                    session.query(FactInventoryDaily.days_of_supply)
                    .join(DimDate, FactInventoryDaily.date_id == DimDate.id)
                    .filter(FactInventoryDaily.sku_id == DimSku.id)
                    .order_by(DimDate.date_value.desc())
                    .first()
                )
                
                days_of_supply = inventory_data.days_of_supply if inventory_data else 0
                
                # 查询利润数据
                profit_data = (
                    session.query(
                        FactProfitSnapshot.net_profit,
                        FactProfitSnapshot.net_margin
                    )
                    .filter(FactProfitSnapshot.sku_id == DimSku.id)
                    .order_by(FactProfitSnapshot.snapshot_date.desc())
                    .first()
                )
                
                net_profit = float(profit_data.net_profit) if profit_data else 0
                net_margin = float(profit_data.net_margin) if profit_data else 0
                
                products.append({
                    "sku": row.sku,
                    "shop": row.shop_name or "Unknown",
                    "category": row.category_name or "Uncategorized",
                    "sales": float(row.sales or 0),
                    "orders": int(row.orders or 0),
                    "ctr": round(ctr, 4),
                    "add_to_cart_rate": round(add_to_cart_rate, 4),
                    "price_index": 1.0,  # TODO: 需要价格指数表
                    "ad_roi": round(ad_roi, 2),
                    "days_of_supply": int(days_of_supply),
                    "net_profit": round(net_profit, 2),
                    "net_margin": round(net_margin, 4),
                    "health_score": 50,  # TODO: 需要健康度评分逻辑
                })
            
            return products

    def get_snapshot(self, sku: str) -> SkuSnapshot:
        if sku == "SKU-002":
            return SkuSnapshot(
                sku="SKU-002",
                impressions=8500,
                card_visits=92,
                add_to_cart=4,
                orders=1,
                ad_spend=280,
                ad_revenue=170,
                stock_total=20,
                days_of_supply=5,
                rating=3.6,
                return_rate=0.18,
                cancel_rate=0.08,
                sale_price=86,
                list_price=99,
                variable_rate_total=0.34,
                fixed_cost_total=65,
            )

        return SkuSnapshot(
            sku="SKU-001",
            impressions=12000,
            card_visits=230,
            add_to_cart=19,
            orders=8,
            ad_spend=420,
            ad_revenue=960,
            stock_total=85,
            days_of_supply=12,
            rating=4.4,
            return_rate=0.06,
            cancel_rate=0.03,
            sale_price=119,
            list_price=129,
            variable_rate_total=0.31,
            fixed_cost_total=72,
        )

    def get_war_room(self, sku: str) -> dict[str, object]:
        report = WarRoomService().build_report(self.get_snapshot(sku))
        return asdict(report)
