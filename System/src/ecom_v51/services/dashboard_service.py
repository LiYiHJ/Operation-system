from __future__ import annotations
from datetime import date, timedelta
from typing import List, Dict, Any

from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from ecom_v51.db.session import get_session
from ecom_v51.db.models import (
    FactSkuDaily,
    FactProfitSnapshot,
    StrategyTask,
    DimDate,
    DimShop
)


class DashboardService:
    """Dashboard服务 - 连接真实数据库"""
    
    def overview(self) -> dict[str, object]:
        """
        从数据库获取Dashboard概览数据
        
        Returns:
            包含销售额、订单数、净利润、待处理策略等的字典
        """
        with get_session() as session:
            # 获取最近7天的日期
            today = date.today()
            seven_days_ago = today - timedelta(days=7)
            
            # 查询最近7天的销售数据
            recent_sales = (
                session.query(
                    func.sum(FactSkuDaily.revenue_ordered).label('total_sales'),
                    func.sum(FactSkuDaily.orders_count).label('total_orders')
                )
                .join(DimDate, FactSkuDaily.date_id == DimDate.id)
                .filter(DimDate.date_value >= seven_days_ago)
                .first()
            )
            
            # 查询最近的利润快照
            recent_profit = (
                session.query(func.sum(FactProfitSnapshot.net_profit))
                .first()
            )
            
            # 查询待处理策略任务
            pending_strategies_count = (
                session.query(func.count(StrategyTask.id))
                .filter(StrategyTask.status == 'pending')
                .scalar()
            )
            
            # 查询最近7天的销售趋势
            trend_data = (
                session.query(
                    DimDate.date_value,
                    func.sum(FactSkuDaily.revenue_ordered).label('daily_sales')
                )
                .join(DimDate, FactSkuDaily.date_id == DimDate.id)
                .filter(DimDate.date_value >= seven_days_ago)
                .group_by(DimDate.date_value)
                .order_by(DimDate.date_value)
                .all()
            )
            
            # 构建趋势数据
            trend_labels = [
                row.date_value.strftime('%a') 
                for row in trend_data
            ] if trend_data else ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            
            trend_sales = [
                float(row.daily_sales or 0) 
                for row in trend_data
            ] if trend_data else [0, 0, 0, 0, 0, 0, 0]
            
            return {
                "sales": float(recent_sales.total_sales or 0),
                "orders": int(recent_sales.total_orders or 0),
                "net_profit": float(recent_profit[0] or 0),
                "pending_strategies": pending_strategies_count or 0,
                "trend_labels": trend_labels,
                "trend_sales": trend_sales,
            }
