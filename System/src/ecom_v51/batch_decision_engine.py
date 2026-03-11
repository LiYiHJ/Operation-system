"""
批量决策引擎
自动分析所有 SKU，生成优先级策略清单
"""
import pandas as pd
from typing import List, Dict, Any
from dataclasses import dataclass
from .profit_solver import ProfitSolver
from .strategy import StrategyEngine


@dataclass
class DecisionReport:
    """决策报告"""
    shop_name: str
    total_skus: int
    summary: Dict[str, int]  # {P0: 3, P1: 5, ...}
    tasks: List[Dict[str, Any]]
    insights: List[str]  # 关键洞察
    urgent_actions: List[str]  # 紧急行动


class BatchDecisionEngine:
    """
    批量决策引擎
    
    功能：
    1. 批量分析所有 SKU
    2. 自动识别问题（库存、价格、转化、广告）
    3. 生成优先级策略清单（P0-P3）
    4. 提供关键洞察和紧急行动建议
    """
    
    def __init__(self):
        self.profit_solver = ProfitSolver()
        self.strategy_engine = StrategyEngine()
        
        # 阈值配置
        self.thresholds = {
            # 库存
            'stock_critical': 7,      # < 7天 = 紧急
            'stock_warning': 14,      # < 14天 = 警告
            'stock_overstock': 60,    # > 60天 = 滞销
            
            # 价格
            'margin_loss': 0,          # < 0% = 亏损
            'margin_low': 0.1,         # < 10% = 低利润
            
            # 转化
            'ctr_critical': 0.01,      # < 1% = 严重
            'ctr_poor': 0.015,         # < 1.5% = 较差
            'cvr_critical': 0.001,     # < 0.1% = 严重
            
            # 广告
            'roas_critical': 1.0,      # < 1.0 = 严重亏损
            'roas_poor': 2.0,          # < 2.0 = 效率低
            
            # 评价
            'rating_critical': 4.0,    # < 4.0 = 严重
            'rating_warning': 4.5,     # < 4.5 = 警告
            'return_rate_high': 0.15,  # > 15% = 退货率高
        }
    
    def analyze_skus(
        self,
        df: pd.DataFrame,
        shop_name: str = "默认店铺"
    ) -> DecisionReport:
        """
        批量分析 SKU
        
        Args:
            df: SKU 数据 DataFrame
            shop_name: 店铺名称
        
        Returns:
            DecisionReport: 决策报告
        """
        tasks = []
        insights = []
        urgent_actions = []
        
        # 统计
        summary = {'P0': 0, 'P1': 0, 'P2': 0, 'P3': 0}
        
        # 遍历每个 SKU
        for idx, row in df.iterrows():
            sku = row.get('sku', f'SKU-{idx}')
            
            # 提取指标
            orders = row.get('orders', 0)
            revenue = row.get('revenue', 0)
            stock = row.get('stock_total', 0)
            days_of_supply = row.get('days_of_supply', 0)
            rating = row.get('rating', 0)
            return_rate = row.get('return_rate', 0)
            
            # 流量指标
            impressions = row.get('impressions', 0)
            card_visits = row.get('card_visits', 0)
            clicks = row.get('clicks', card_visits)
            add_to_cart = row.get('add_to_cart', 0)
            
            # 计算比率
            ctr = clicks / impressions if impressions > 0 else 0
            add_to_cart_rate = add_to_cart / card_visits if card_visits > 0 else 0
            order_rate = orders / add_to_cart if add_to_cart > 0 else 0
            conversion_rate = orders / impressions if impressions > 0 else 0
            
            # 利润指标
            sale_price = row.get('sale_price', 0)
            cost_price = row.get('cost_price', sale_price * 0.5)  # 默认成本50%
            commission_rate = row.get('commission_rate', 0.15)     # 默认佣金15%
            ad_spend = row.get('ad_spend', 0)
            ad_revenue = row.get('ad_revenue', 0)
            
            # 计算净利润
            variable_rate = commission_rate + 0.05  # 佣金 + 其他可变成本
            fixed_cost = cost_price
            net_profit = sale_price * (1 - variable_rate) - fixed_cost
            net_margin = net_profit / sale_price if sale_price > 0 else 0
            
            # ROAS
            roas = ad_revenue / ad_spend if ad_spend > 0 else 0
            
            # === 生成策略任务 ===
            sku_tasks = self.strategy_engine.generate_for_sku(
                ctr=ctr,
                add_to_cart_rate=add_to_cart_rate,
                order_rate=order_rate,
                net_margin=net_margin,
                roas=roas,
                days_of_supply=days_of_supply,
                return_rate=return_rate,
                rating=rating
            )
            
            # 转换为字典并添加到列表
            for task in sku_tasks:
                task_dict = {
                    'sku': sku,
                    'strategy_type': task.strategy_type,
                    'priority': task.priority,
                    'issue_summary': task.issue_summary,
                    'recommended_action': task.recommended_action,
                    'observation_metrics': task.observation_metrics,
                    'status': 'pending',
                    'details': {
                        'ctr': ctr,
                        'conversion_rate': conversion_rate,
                        'net_margin': net_margin,
                        'roas': roas,
                        'days_of_supply': days_of_supply,
                        'rating': rating,
                        'return_rate': return_rate
                    }
                }
                tasks.append(task_dict)
                summary[task.priority] += 1
            
            # === 额外的规则检查 ===
            
            # 1. 库存紧急（P0）
            if days_of_supply > 0 and days_of_supply < self.thresholds['stock_critical']:
                urgent_actions.append(
                    f"[P0] {sku}: 库存仅剩 {days_of_supply:.0f} 天，立即补货！"
                )
            
            # 2. 滞销库存（P2）
            elif days_of_supply > self.thresholds['stock_overstock']:
                tasks.append({
                    'sku': sku,
                    'strategy_type': 'inventory',
                    'priority': 'P2',
                    'issue_summary': f'库存积压 {days_of_supply:.0f} 天',
                    'recommended_action': '考虑清仓促销或停止补货',
                    'observation_metrics': ['stock_total', 'days_of_supply'],
                    'status': 'pending'
                })
                summary['P2'] += 1
            
            # 3. 评分严重（P1）
            if 0 < rating < self.thresholds['rating_critical']:
                insights.append(
                    f"[P1] {sku}: 评分 {rating:.1f} < 4.0，影响转化"
                )
            
            # 4. 退货率高（P1）
            if return_rate > self.thresholds['return_rate_high']:
                insights.append(
                    f"[P1] {sku}: 退货率 {return_rate:.1%} > 15%，需排查原因"
                )
        
        # === 生成关键洞察 ===
        
        # 整体健康度
        total_skus = len(df)
        p0_ratio = summary['P0'] / total_skus if total_skus > 0 else 0
        p1_ratio = summary['P1'] / total_skus if total_skus > 0 else 0
        
        if p0_ratio > 0.1:
            insights.append(f"⚠️ 警告：{p0_ratio:.1%} 的 SKU 有紧急问题（P0）")
        
        if p1_ratio > 0.3:
            insights.append(f"⚠️ 警告：{p1_ratio:.1%} 的 SKU 有严重问题（P1）")
        
        # 转化率分析
        if total_skus > 0:
            avg_ctr = df['impressions'].sum() / df['card_visits'].sum() if df['card_visits'].sum() > 0 else 0
            if avg_ctr < self.thresholds['ctr_poor']:
                insights.append(
                    f"💡 整体 CTR {avg_ctr:.2%} 偏低，建议优化主图和标题"
                )
        
        # === 排序任务（按优先级） ===
        priority_order = {'P0': 0, 'P1': 1, 'P2': 2, 'P3': 3}
        tasks = sorted(tasks, key=lambda x: priority_order.get(x['priority'], 99))
        
        # 生成决策报告
        report = DecisionReport(
            shop_name=shop_name,
            total_skus=total_skus,
            summary=summary,
            tasks=tasks[:50],  # 最多返回 50 个任务
            insights=insights[:10],  # 最多 10 条洞察
            urgent_actions=urgent_actions[:10]  # 最多 10 条紧急行动
        )
        
        return report
    
    def get_quick_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        快速摘要（用于 Dashboard）
        
        Returns:
            {
                'health_score': 75,
                'alerts': [...],
                'recommendations': [...]
            }
        """
        report = self.analyze_skus(df)
        
        # 计算健康度评分（0-100）
        total_skus = report.total_skus
        if total_skus == 0:
            health_score = 100
        else:
            # P0 每个 -10分，P1 每个 -5分，P2 每个 -2分，P3 每个 -1分
            penalty = (
                report.summary['P0'] * 10 +
                report.summary['P1'] * 5 +
                report.summary['P2'] * 2 +
                report.summary['P3'] * 1
            )
            health_score = max(0, 100 - penalty)
        
        return {
            'health_score': health_score,
            'alerts': report.urgent_actions[:5],
            'recommendations': report.insights[:5],
            'summary': report.summary
        }
