"""
War Room API - 基于前端 utils/api.ts 定义
实现：
  GET /api/sku/:id/war-room
"""

from flask import Blueprint, jsonify
from datetime import datetime

from ...war_room import WarRoomService
from ...models import SkuSnapshot

war_room_bp = Blueprint('war_room', __name__)


@war_room_bp.route('/<sku>/war-room', methods=['GET'])
def get_sku_war_room(sku):
    """
    SKU 作战室报告
    前端调用: warRoomAPI.getSkuReport(skuId)
    
    参数:
        sku: SKU编码
    
    返回:
        {
            "sku": "SKU-001",
            "funnel": {
                "ctr": 0.01,
                "add_to_cart_rate": 0.05,
                "order_rate": 0.2
            },
            "net_profit": -15.0,
            "net_margin": -0.15,
            "break_even_price": 107.69,
            "discount_simulations": [...],
            "strategy_tasks": [...]
        }
    """
    try:
        # TODO: 从数据库读取SKU数据
        # 当前使用示例数据
        snapshot = SkuSnapshot(
            sku=sku,
            impressions=10000,
            card_visits=100,
            add_to_cart=5,
            orders=1,
            ad_spend=300,
            ad_revenue=200,
            stock_total=20,
            days_of_supply=5,
            rating=3.7,
            return_rate=0.2,
            cancel_rate=0.05,
            sale_price=100,
            list_price=120,
            variable_rate_total=0.35,
            fixed_cost_total=80
        )
        
        # 使用 WarRoomService 生成报告
        service = WarRoomService()
        report = service.build_report(snapshot)
        
        # 转换为字典
        result = {
            "sku": report.sku,
            "funnel": report.funnel,
            "net_profit": report.net_profit,
            "net_margin": report.net_margin,
            "break_even_price": report.break_even_price,
            "discount_simulations": [
                {
                    "discount_ratio": sim.discount_ratio,
                    "deal_price": sim.deal_price,
                    "net_profit": sim.net_profit,
                    "net_margin": sim.net_margin,
                    "is_loss": sim.is_loss
                }
                for sim in report.discount_simulations
            ],
            "strategy_tasks": [
                {
                    "strategy_type": task.strategy_type,
                    "level": task.level,
                    "priority": task.priority,
                    "issue_summary": task.issue_summary,
                    "recommended_action": task.recommended_action,
                    "observation_metrics": task.observation_metrics
                }
                for task in report.strategy_tasks
            ]
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
