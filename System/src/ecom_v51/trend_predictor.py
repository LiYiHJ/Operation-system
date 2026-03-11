"""
趋势预测模块
使用简单的统计方法 + Prophet 进行销量、库存、价格趋势预测
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging
import json
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 尝试导入 Prophet（如果已安装）
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
    logger.info("✅ Prophet 已安装")
except ImportError:
    PROPHET_AVAILABLE = False
    logger.warning("⚠️ Prophet 未安装，将使用简单预测方法。安装: pip install prophet")


class TrendPredictor:
    """
    趋势预测器
    
    支持三种预测方法：
    1. 简单移动平均（无需依赖）
    2. 线性回归（只需 numpy）
    3. Prophet（需安装 prophet）
    """
    
    def __init__(self, method: str = "auto"):
        """
        初始化预测器
        
        Args:
            method: 预测方法
                - "simple": 简单移动平均
                - "linear": 线性回归
                - "prophet": Facebook Prophet
                - "auto": 自动选择（优先 Prophet）
        """
        self.method = method
        
        # 根据可用性自动选择方法
        if method == "auto":
            if PROPHET_AVAILABLE:
                self.method = "prophet"
            else:
                self.method = "linear"
        
        logger.info(f"📊 预测方法: {self.method}")
    
    # ===== 销量预测 =====
    
    def predict_sales(
        self,
        historical_data: pd.DataFrame,
        days: int = 7,
        sku: str = None
    ) -> Dict:
        """
        预测未来销量
        
        Args:
            historical_data: 历史数据（必须包含 date 和 orders 列）
            days: 预测天数
            sku: SKU 编号（用于日志）
        
        Returns:
            预测结果
        """
        try:
            # 准备数据
            df = historical_data.copy()
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # 根据方法选择预测算法
            if self.method == "prophet":
                predictions = self._predict_with_prophet(df, 'orders', days)
            elif self.method == "linear":
                predictions = self._predict_with_linear(df, 'orders', days)
            else:
                predictions = self._predict_with_simple(df, 'orders', days)
            
            # 计算置信区间
            confidence = self._calculate_confidence(df, 'orders')
            
            # 计算统计信息
            stats = {
                "avg_daily_sales": float(df['orders'].tail(7).mean()),
                "trend": self._detect_trend(df['orders']),
                "volatility": float(df['orders'].std() / df['orders'].mean()) if df['orders'].mean() > 0 else 0
            }
            
            return {
                "sku": sku,
                "predictions": predictions,
                "confidence": confidence,
                "stats": stats,
                "method": self.method
            }
            
        except Exception as e:
            logger.error(f"销量预测失败: {e}")
            return None
    
    # ===== 库存预测 =====
    
    def predict_stockout(
        self,
        current_stock: int,
        daily_sales: List[float],
        days_to_predict: int = 30
    ) -> Dict:
        """
        预测库存耗尽时间
        
        Args:
            current_stock: 当前库存
            daily_sales: 历史日销量列表
            days_to_predict: 预测天数
        
        Returns:
            库存预测结果
        """
        try:
            # 计算平均日销
            avg_sales = np.mean(daily_sales)
            
            # 预测库存消耗
            days_of_stock = current_stock / avg_sales if avg_sales > 0 else 999
            
            # 计算断货日期
            stockout_date = datetime.now() + timedelta(days=days_of_stock)
            
            # 风险等级
            if days_of_stock < 7:
                risk_level = "critical"
                risk_color = "red"
            elif days_of_stock < 14:
                risk_level = "warning"
                risk_color = "orange"
            elif days_of_stock > 60:
                risk_level = "overstock"
                risk_color = "yellow"
            else:
                risk_level = "normal"
                risk_color = "green"
            
            # 生成未来 30 天库存预测
            future_stock = []
            stock = current_stock
            for i in range(days_to_predict):
                stock = max(0, stock - avg_sales)
                future_stock.append({
                    "day": i + 1,
                    "date": (datetime.now() + timedelta(days=i+1)).strftime("%Y-%m-%d"),
                    "stock": int(stock),
                    "status": "normal" if stock > 0 else "stockout"
                })
            
            return {
                "current_stock": current_stock,
                "avg_daily_sales": round(avg_sales, 2),
                "days_of_stock": round(days_of_stock, 1),
                "stockout_date": stockout_date.strftime("%Y-%m-%d"),
                "risk_level": risk_level,
                "risk_color": risk_color,
                "reorder_recommendation": self._calculate_reorder_point(avg_sales, days_of_stock),
                "future_stock": future_stock
            }
            
        except Exception as e:
            logger.error(f"库存预测失败: {e}")
            return None
    
    # ===== 价格趋势预测 =====
    
    def predict_price_trend(
        self,
        price_history: pd.DataFrame,
        competitor_prices: List[float] = None
    ) -> Dict:
        """
        预测价格趋势
        
        Args:
            price_history: 价格历史（必须包含 date 和 price 列）
            competitor_prices: 竞品价格列表
        
        Returns:
            价格趋势预测
        """
        try:
            df = price_history.copy()
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # 计算价格趋势
            trend = self._detect_trend(df['price'])
            
            # 计算价格波动
            volatility = df['price'].std() / df['price'].mean() if df['price'].mean() > 0 else 0
            
            # 预测未来价格
            if self.method == "prophet":
                predictions = self._predict_with_prophet(df, 'price', 7)
            elif self.method == "linear":
                predictions = self._predict_with_linear(df, 'price', 7)
            else:
                predictions = self._predict_with_simple(df, 'price', 7)
            
            # 竞品分析
            competitor_analysis = None
            if competitor_prices:
                avg_competitor = np.mean(competitor_prices)
                current_price = df['price'].iloc[-1]
                price_position = (current_price - avg_competitor) / avg_competitor
                
                competitor_analysis = {
                    "avg_competitor_price": round(avg_competitor, 2),
                    "price_position": "高于竞品" if price_position > 0.05 else "低于竞品" if price_position < -0.05 else "与竞品持平",
                    "price_gap_percentage": round(price_position * 100, 1)
                }
            
            return {
                "trend": trend,
                "volatility": round(volatility, 3),
                "predictions": predictions,
                "competitor_analysis": competitor_analysis,
                "recommendation": self._generate_price_recommendation(trend, volatility, competitor_analysis)
            }
            
        except Exception as e:
            logger.error(f"价格趋势预测失败: {e}")
            return None
    
    # ===== 预测算法 =====
    
    def _predict_with_simple(self, df: pd.DataFrame, column: str, days: int) -> List[Dict]:
        """简单移动平均预测"""
        # 使用最近 7 天的平均值作为未来预测
        avg_value = df[column].tail(7).mean()
        
        predictions = []
        for i in range(days):
            date = datetime.now() + timedelta(days=i+1)
            predictions.append({
                "date": date.strftime("%Y-%m-%d"),
                "predicted_value": round(avg_value, 2),
                "method": "simple_moving_average"
            })
        
        return predictions
    
    def _predict_with_linear(self, df: pd.DataFrame, column: str, days: int) -> List[Dict]:
        """线性回归预测"""
        # 准备数据
        X = np.arange(len(df)).reshape(-1, 1)
        y = df[column].values
        
        # 线性回归（手动实现，避免 sklearn 依赖）
        n = len(X)
        sum_x = np.sum(X)
        sum_y = np.sum(y)
        sum_xy = np.sum(X * y.reshape(-1, 1))
        sum_x2 = np.sum(X ** 2)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        intercept = (sum_y - slope * sum_x) / n
        
        # 预测未来
        predictions = []
        for i in range(days):
            future_x = len(df) + i
            predicted_value = slope * future_x + intercept
            date = datetime.now() + timedelta(days=i+1)
            
            predictions.append({
                "date": date.strftime("%Y-%m-%d"),
                "predicted_value": round(max(0, predicted_value), 2),  # 不能为负
                "method": "linear_regression"
            })
        
        return predictions
    
    def _predict_with_prophet(self, df: pd.DataFrame, column: str, days: int) -> List[Dict]:
        """Prophet 预测（Facebook 时间序列模型）"""
        if not PROPHET_AVAILABLE:
            logger.warning("Prophet 不可用，降级为线性回归")
            return self._predict_with_linear(df, column, days)
        
        try:
            # 准备 Prophet 格式数据
            prophet_df = pd.DataFrame({
                'ds': df['date'],
                'y': df[column]
            })
            
            # 创建并训练模型
            model = Prophet(
                daily_seasonality=False,
                weekly_seasonality=True,
                yearly_seasonality=False
            )
            model.fit(prophet_df)
            
            # 生成未来日期
            future = model.make_future_dataframe(periods=days)
            
            # 预测
            forecast = model.predict(future)
            
            # 提取预测结果
            predictions = []
            for i in range(days):
                idx = len(df) + i
                row = forecast.iloc[idx]
                
                predictions.append({
                    "date": row['ds'].strftime("%Y-%m-%d"),
                    "predicted_value": round(max(0, row['yhat']), 2),
                    "lower_bound": round(max(0, row['yhat_lower']), 2),
                    "upper_bound": round(max(0, row['yhat_upper']), 2),
                    "method": "prophet"
                })
            
            return predictions
            
        except Exception as e:
            logger.warning(f"Prophet 预测失败: {e}，降级为线性回归")
            return self._predict_with_linear(df, column, days)
    
    # ===== 辅助方法 =====
    
    def _detect_trend(self, series: pd.Series) -> str:
        """检测趋势方向"""
        if len(series) < 3:
            return "stable"
        
        # 简单趋势检测：比较前半部分和后半部分的平均值
        mid = len(series) // 2
        first_half_avg = series[:mid].mean()
        second_half_avg = series[mid:].mean()
        
        change = (second_half_avg - first_half_avg) / first_half_avg if first_half_avg > 0 else 0
        
        if change > 0.1:
            return "increasing"
        elif change < -0.1:
            return "decreasing"
        else:
            return "stable"
    
    def _calculate_confidence(self, df: pd.DataFrame, column: str) -> float:
        """计算预测置信度（0-1）"""
        if len(df) < 7:
            return 0.5
        
        # 基于数据量和波动性计算置信度
        volatility = df[column].std() / df[column].mean() if df[column].mean() > 0 else 1
        data_points = len(df)
        
        # 数据越多，波动越小，置信度越高
        confidence = min(1.0, (data_points / 30) * (1 - volatility))
        
        return round(confidence, 2)
    
    def _calculate_reorder_point(self, avg_sales: float, days_of_stock: float) -> Dict:
        """计算补货点"""
        # 安全库存 = 7 天销量
        safety_stock = avg_sales * 7
        
        # 补货点 = 安全库存 + 补货周期内的销量
        lead_time = 14  # 假设补货周期 14 天
        reorder_point = safety_stock + avg_sales * lead_time
        
        # 补货建议
        if days_of_stock < 7:
            urgency = "urgent"
            message = "立即补货"
        elif days_of_stock < 14:
            urgency = "high"
            message = "尽快补货"
        elif days_of_stock < 30:
            urgency = "medium"
            message = "计划补货"
        else:
            urgency = "low"
            message = "库存充足"
        
        return {
            "safety_stock": int(safety_stock),
            "reorder_point": int(reorder_point),
            "urgency": urgency,
            "message": message
        }
    
    def _generate_price_recommendation(self, trend: str, volatility: float, competitor_analysis: Dict) -> str:
        """生成价格建议"""
        if trend == "decreasing" and volatility < 0.1:
            return "价格稳定下降，建议观察市场趋势"
        elif trend == "increasing" and volatility < 0.1:
            return "价格稳定上涨，可考虑适当提价"
        elif volatility > 0.2:
            return "价格波动较大，建议谨慎调整"
        
        if competitor_analysis:
            if competitor_analysis["price_position"] == "高于竞品":
                return "价格高于竞品，考虑适当降价提升竞争力"
            elif competitor_analysis["price_position"] == "低于竞品":
                return "价格低于竞品，可考虑适当提价提升利润"
        
        return "价格正常，保持当前策略"


# ===== 批量预测 =====

class BatchTrendPredictor:
    """批量趋势预测器"""
    
    def __init__(self, method: str = "auto"):
        self.predictor = TrendPredictor(method)
    
    def predict_all_skus(
        self,
        sku_data: Dict[str, pd.DataFrame],
        prediction_types: List[str] = ["sales", "stock"]
    ) -> Dict:
        """
        批量预测所有 SKU
        
        Args:
            sku_data: SKU 数据字典 {sku_id: dataframe}
            prediction_types: 预测类型列表
        
        Returns:
            批量预测结果
        """
        results = {}
        
        for sku, df in sku_data.items():
            result = {"sku": sku}
            
            if "sales" in prediction_types:
                result["sales_prediction"] = self.predictor.predict_sales(df, days=7, sku=sku)
            
            if "stock" in prediction_types and 'stock' in df.columns:
                current_stock = df['stock'].iloc[-1]
                daily_sales = df['orders'].tolist()
                result["stock_prediction"] = self.predictor.predict_stockout(current_stock, daily_sales)
            
            results[sku] = result
        
        return results
    
    def identify_trending_products(self, results: Dict, top_n: int = 10) -> Dict:
        """
        识别趋势产品
        
        Args:
            results: 批量预测结果
            top_n: 返回前 N 个
        
        Returns:
            趋势产品列表
        """
        # 上升趋势（销量增长）
        increasing = []
        decreasing = []
        
        for sku, data in results.items():
            if data.get("sales_prediction"):
                trend = data["sales_prediction"]["stats"]["trend"]
                if trend == "increasing":
                    increasing.append({
                        "sku": sku,
                        "avg_sales": data["sales_prediction"]["stats"]["avg_daily_sales"],
                        "confidence": data["sales_prediction"]["confidence"]
                    })
                elif trend == "decreasing":
                    decreasing.append({
                        "sku": sku,
                        "avg_sales": data["sales_prediction"]["stats"]["avg_daily_sales"],
                        "confidence": data["sales_prediction"]["confidence"]
                    })
        
        # 排序
        increasing.sort(key=lambda x: x['avg_sales'], reverse=True)
        decreasing.sort(key=lambda x: x['avg_sales'], reverse=True)
        
        return {
            "hot_products": increasing[:top_n],  # 热销产品
            "declining_products": decreasing[:top_n],  # 滞销产品
            "summary": {
                "total_increasing": len(increasing),
                "total_decreasing": len(decreasing)
            }
        }


# ===== 示例用法 =====

if __name__ == "__main__":
    # 创建示例数据
    dates = pd.date_range(start='2026-02-01', end='2026-03-08', freq='D')
    orders = np.random.poisson(lam=50, size=len(dates))  # 平均 50 单/天
    
    # 添加趋势（逐渐增长）
    trend = np.linspace(0, 20, len(dates))
    orders = orders + trend
    
    df = pd.DataFrame({
        'date': dates,
        'orders': orders.astype(int),
        'stock': [500 - i*15 for i in range(len(dates))]  # 库存逐渐减少
    })
    
    # 创建预测器
    predictor = TrendPredictor(method="auto")
    
    # 预测销量
    print("📊 销量预测:")
    sales_pred = predictor.predict_sales(df, days=7, sku="TEST-001")
    if sales_pred:
        print(f"  趋势: {sales_pred['stats']['trend']}")
        print(f"  置信度: {sales_pred['confidence']}")
        print(f"  未来 7 天预测:")
        for pred in sales_pred['predictions'][:3]:
            print(f"    {pred['date']}: {pred['predicted_value']} 单")
    
    # 预测库存
    print("\n📦 库存预测:")
    stock_pred = predictor.predict_stockout(
        current_stock=500,
        daily_sales=df['orders'].tolist()
    )
    if stock_pred:
        print(f"  预计断货: {stock_pred['stockout_date']}")
        print(f"  可销天数: {stock_pred['days_of_stock']} 天")
        print(f"  风险等级: {stock_pred['risk_level']}")
        print(f"  补货建议: {stock_pred['reorder_recommendation']['message']}")
