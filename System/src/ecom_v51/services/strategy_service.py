from __future__ import annotations

from typing import List, Dict, Any
from sqlalchemy.orm import Session

from ecom_v51.db.session import get_session
from ecom_v51.db.models import StrategyTask, FactSkuDaily, DimSku
from ecom_v51.strategy import StrategyEngine
from ecom_v51.models import SkuSnapshot
from ecom_v51.war_room import WarRoomService


class StrategyTaskService:
    """策略任务服务 - 使用真实引擎和数据库"""
    
    def __init__(self):
        self.engine = StrategyEngine()
        self.war_room = WarRoomService()
    
    def list_tasks(self, priority: str = "", status: str = "") -> list[dict[str, object]]:
        """
        从数据库查询策略任务
        
        Args:
            priority: 优先级过滤 (P0/P1/P2/P3)
            status: 状态过滤 (pending/in_progress/completed)
        
        Returns:
            策略任务列表
        """
        with get_session() as session:
            query = session.query(StrategyTask)
            
            if priority:
                query = query.filter(StrategyTask.priority == priority)
            
            if status:
                query = query.filter(StrategyTask.status == status)
            
            tasks = query.order_by(StrategyTask.priority, StrategyTask.created_at.desc()).limit(100).all()
            
            return [
                {
                    "id": task.id,
                    "priority": task.priority,
                    "status": task.status,
                    "strategy_type": task.strategy_type,
                    "sku": task.sku.sku if task.sku else None,
                    "trigger_rule": task.trigger_rule,
                    "issue_summary": task.issue_summary,
                    "recommended_action": task.recommended_action,
                    "observation_metrics": task.observation_metrics_json,
                    "owner": task.owner,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                }
                for task in tasks
            ]
    
    def generate_for_sku(self, sku_snapshot: SkuSnapshot) -> List[Dict[str, Any]]:
        """
        为SKU生成策略任务
        
        Args:
            sku_snapshot: SKU快照数据
        
        Returns:
            生成的策略任务列表
        """
        # 使用真实的策略引擎生成任务
        tasks = self.engine.generate_for_sku(
            ctr=sku_snapshot.card_visits / sku_snapshot.impressions if sku_snapshot.impressions else 0,
            add_to_cart_rate=sku_snapshot.add_to_cart / sku_snapshot.card_visits if sku_snapshot.card_visits else 0,
            order_rate=sku_snapshot.orders / sku_snapshot.add_to_cart if sku_snapshot.add_to_cart else 0,
            net_margin=0,  # TODO: 从利润快照获取
            roas=sku_snapshot.ad_revenue / sku_snapshot.ad_spend if sku_snapshot.ad_spend else 0,
            days_of_supply=sku_snapshot.days_of_supply,
            return_rate=sku_snapshot.return_rate,
            rating=sku_snapshot.rating,
        )
        
        return [
            {
                "strategy_type": task.strategy_type,
                "priority": task.priority,
                "issue_summary": task.issue_summary,
                "recommended_action": task.recommended_action,
                "observation_metrics": task.observation_metrics,
            }
            for task in tasks
        ]

