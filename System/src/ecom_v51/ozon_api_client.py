"""
Ozon API 客户端
用于自动调价、补货、获取数据等操作
"""
import requests
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OzonAPIClient:
    """
    Ozon API 客户端
    
    文档: https://docs.ozon.ru/api/
    """
    
    def __init__(self, client_id: str, api_key: str):
        """
        初始化客户端
        
        Args:
            client_id: Ozon Client-Id
            api_key: Ozon Api-Key
        """
        self.client_id = client_id
        self.api_key = api_key
        self.base_url = "https://api-seller.ozon.ru"
        
        self.headers = {
            "Client-Id": client_id,
            "Api-Key": api_key,
            "Content-Type": "application/json"
        }
    
    def test_connection(self) -> bool:
        """测试 API 连接"""
        try:
            response = self._post("/v2/product/list", {"filter": {}, "page": 1, "page_size": 1})
            return response.status_code == 200
        except Exception as e:
            logger.error(f"连接测试失败: {e}")
            return False
    
    # ===== 产品相关 =====
    
    def get_products(self, page: int = 1, page_size: int = 100) -> Dict:
        """
        获取产品列表
        
        Args:
            page: 页码
            page_size: 每页数量
        
        Returns:
            产品列表数据
        """
        payload = {
            "filter": {
                "visibility": "ALL"
            },
            "page": page,
            "page_size": page_size
        }
        
        response = self._post("/v2/product/list", payload)
        return response.json()
    
    def get_product_info(self, product_ids: List[int]) -> Dict:
        """
        获取产品详细信息
        
        Args:
            product_ids: 产品 ID 列表
        
        Returns:
            产品详细信息
        """
        payload = {
            "product_id": product_ids
        }
        
        response = self._post("/v2/product/info/list", payload)
        return response.json()
    
    def get_product_stocks(self, product_ids: List[int]) -> Dict:
        """
        获取产品库存信息
        
        Args:
            product_ids: 产品 ID 列表
        
        Returns:
            库存信息
        """
        payload = {
            "product_id": product_ids
        }
        
        response = self._post("/v3/product/info/stocks", payload)
        return response.json()
    
    # ===== 价格相关 =====
    
    def get_product_prices(self, product_ids: List[int]) -> Dict:
        """
        获取产品价格信息
        
        Args:
            product_ids: 产品 ID 列表
        
        Returns:
            价格信息
        """
        payload = {
            "filter": {
                "product_id": product_ids
            },
            "page": 1,
            "page_size": len(product_ids)
        }
        
        response = self._post("/v4/product/info/prices", payload)
        return response.json()
    
    def update_product_prices(self, price_updates: List[Dict]) -> Dict:
        """
        批量更新产品价格（自动调价核心功能）
        
        Args:
            price_updates: 价格更新列表
                [
                    {
                        "product_id": 123456,
                        "price": "1299",
                        "old_price": "1599"  # 可选
                    },
                    ...
                ]
        
        Returns:
            更新结果
        """
        payload = {
            "prices": price_updates
        }
        
        response = self._post("/v1/product/import/prices", payload)
        result = response.json()
        
        if response.status_code == 200:
            logger.info(f"✅ 成功更新 {len(price_updates)} 个产品价格")
        else:
            logger.error(f"❌ 价格更新失败: {result}")
        
        return result
    
    def auto_adjust_price(self, product_id: int, current_price: float, 
                          strategy: str = "profit_optimize") -> Dict:
        """
        自动调价策略
        
        Args:
            product_id: 产品 ID
            current_price: 当前价格
            strategy: 调价策略
                - profit_optimize: 利润优化（保持净利率 > 10%）
                - sell_through: 加速清仓（降价 15%）
                - competitive: 竞争定价（略低于竞品）
        
        Returns:
            调价建议
        """
        adjustment_rules = {
            "profit_optimize": {
                "action": "increase",
                "percentage": 0.10,
                "reason": "提升净利率至 10% 以上"
            },
            "sell_through": {
                "action": "decrease",
                "percentage": 0.15,
                "reason": "加速清仓，提升销量"
            },
            "competitive": {
                "action": "decrease",
                "percentage": 0.05,
                "reason": "保持竞争力，略低于竞品"
            }
        }
        
        rule = adjustment_rules.get(strategy, adjustment_rules["profit_optimize"])
        
        if rule["action"] == "increase":
            new_price = current_price * (1 + rule["percentage"])
        else:
            new_price = current_price * (1 - rule["percentage"])
        
        # 确保价格合理（不低于成本）
        min_price = current_price * 0.7  # 最低 70%
        new_price = max(new_price, min_price)
        
        # 四舍五入到整数
        new_price = round(new_price)
        
        logger.info(f"💡 调价建议 [{strategy}]: {current_price} → {new_price} ({rule['reason']})")
        
        return {
            "product_id": product_id,
            "old_price": current_price,
            "new_price": new_price,
            "change_percentage": rule["percentage"],
            "action": rule["action"],
            "reason": rule["reason"],
            "strategy": strategy
        }
    
    # ===== 库存相关 =====
    
    def update_product_stocks(self, stock_updates: List[Dict]) -> Dict:
        """
        批量更新产品库存（补货核心功能）
        
        Args:
            stock_updates: 库存更新列表
                [
                    {
                        "product_id": 123456,
                        "offer_id": "SKU-001",
                        "stocks": [
                            {
                                "warehouse_id": 12345,
                                "present": 100,
                                "reserved": 0
                            }
                        ]
                    },
                    ...
                ]
        
        Returns:
            更新结果
        """
        payload = {
            "stocks": stock_updates
        }
        
        response = self._post("/v2/products/stocks", payload)
        result = response.json()
        
        if response.status_code == 200:
            logger.info(f"✅ 成功更新 {len(stock_updates)} 个产品库存")
        else:
            logger.error(f"❌ 库存更新失败: {result}")
        
        return result
    
    def get_warehouses(self) -> Dict:
        """
        获取仓库列表
        
        Returns:
            仓库列表
        """
        response = self._post("/v1/warehouse/list", {})
        return response.json()
    
    # ===== 订单相关 =====
    
    def get_orders(self, days: int = 7, status: str = None) -> Dict:
        """
        获取订单列表
        
        Args:
            days: 最近几天
            status: 订单状态（可选）
        
        Returns:
            订单列表
        """
        from datetime import datetime, timedelta
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        payload = {
            "dir": "ASC",
            "filter": {
                "since": start_date.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "to": end_date.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "status": status
            },
            "limit": 1000,
            "offset": 0,
            "with": {
                "analytics_data": True,
                "financial_data": True
            }
        }
        
        response = self._post("/v3/order/list", payload)
        return response.json()
    
    # ===== 分析数据 =====
    
    def get_analytics(self, dimensions: List[str], days: int = 7) -> Dict:
        """
        获取分析数据
        
        Args:
            dimensions: 维度（如 ["day", "sku"]）
            days: 最近几天
        
        Returns:
            分析数据
        """
        from datetime import datetime, timedelta
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        payload = {
            "dimensions": dimensions,
            "metrics": [
                "revenue",
                "ordered_units",
                "delivered_units",
                "returns",
                "cancellations",
                "views",
                "clicks"
            ],
            "date_from": start_date.strftime("%Y-%m-%d"),
            "date_to": end_date.strftime("%Y-%m-%d"),
            "limit": 1000,
            "offset": 0
        }
        
        response = self._post("/v1/analytics/data", payload)
        return response.json()
    
    # ===== 辅助方法 =====
    
    def _post(self, endpoint: str, payload: Dict) -> requests.Response:
        """
        发送 POST 请求
        
        Args:
            endpoint: API 端点
            payload: 请求数据
        
        Returns:
            响应对象
        """
        url = self.base_url + endpoint
        
        try:
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            # 记录请求日志
            logger.debug(f"POST {endpoint} - Status: {response.status_code}")
            
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API 请求失败 [{endpoint}]: {e}")
            raise


# ===== 店铺配置 =====

SHOP_CONFIGS = {
    "YunElite": {
        "client_id": "3055895",
        "api_key": ""  # 需要填入真实的 API Key
    },
    "ALORA": {
        "client_id": "3328779",
        "api_key": ""  # 需要填入真实的 API Key
    },
    "YunYi": {
        "client_id": "4022219",
        "api_key": ""  # 需要填入真实的 API Key
    }
}


def get_ozon_client(shop_name: str = "YunElite") -> Optional[OzonAPIClient]:
    """
    获取 Ozon API 客户端
    
    Args:
        shop_name: 店铺名称
    
    Returns:
        OzonAPIClient 实例
    """
    config = SHOP_CONFIGS.get(shop_name)
    
    if not config:
        logger.error(f"未找到店铺配置: {shop_name}")
        return None
    
    if not config["api_key"]:
        logger.warning(f"店铺 {shop_name} 的 API Key 未配置")
        return None
    
    return OzonAPIClient(
        client_id=config["client_id"],
        api_key=config["api_key"]
    )


# ===== 示例用法 =====

if __name__ == "__main__":
    # 测试连接
    client = get_ozon_client("YunElite")
    
    if client:
        print("✅ API 连接成功" if client.test_connection() else "❌ API 连接失败")
        
        # 获取产品列表
        products = client.get_products(page_size=10)
        print(f"📦 产品数量: {len(products.get('result', {}).get('items', []))}")
