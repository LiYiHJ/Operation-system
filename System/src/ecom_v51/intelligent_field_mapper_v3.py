"""
增强版智能字段映射器 V3
支持：任意文档类型、多语言、手动映射
"""
import re
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from difflib import SequenceMatcher


@dataclass
class FieldPattern:
    """字段模式定义"""
    name: str  # 标准字段名
    keywords: List[str]  # 关键词列表
    patterns: List[str]  # 正则表达式模式
    priority: int  # 优先级（越高越优先）
    category: str = 'general'  # 字段分类
    description: str = ''  # 字段描述
    validator: Optional[callable] = None  # 数据验证函数
    examples: List[str] = field(default_factory=list)  # 示例值


class IntelligentFieldMapperV3:
    """
    智能字段映射器 V3
    
    特性：
    1. 支持任意文档格式（Excel/CSV/JSON）
    2. 多语言支持（俄语/中文/英语/西班牙语/葡萄牙语）
    3. 模糊匹配 + 正则匹配 + 数据验证
    4. 支持手动映射覆盖
    5. 学习用户反馈，持续优化
    """
    
    def __init__(self):
        self.field_patterns = self._init_field_patterns()
        self.fuzzy_threshold = 0.6  # 降低阈值，提高匹配率
        self.user_feedback = []  # 用户反馈记录
        
    def _init_field_patterns(self) -> Dict[str, FieldPattern]:
        """初始化字段模式（30+ 标准字段）"""
        return {
            # === 基础信息字段 ===
            "sku": FieldPattern(
                name="sku",
                keywords=[
                    "sku", "артикул", "artikel", "art", "code",
                    "商品编码", "产品ID", "货号", "编号", "id",
                    "identifier", "product id", "offer id", "seller sku",
                    "товар", "codigo", "código", "ref", "reference"
                ],
                patterns=[
                    r"(?i)(seller[_\s]?sku|sku)",
                    r"(?i)(offer[_\s]?id|offerid)",
                    r"(?i)(product[_\s]?id|productid)",
                    r"(?i)(арт[икул]+|art[ikul]+)",
                    r"(?i)(id[_\s]?товара)",
                    r"(?i)(商品编码|产品编号)",
                    r"(?i)(货号|款号)",
                ],
                priority=100,
                category="基础",
                description="商品唯一标识",
                examples=["SKU-001", "12345", "ABC123"]
            ),
            
            "product_name": FieldPattern(
                name="product_name",
                keywords=[
                    "name", "название", "названия", "title",
                    "名称", "标题", "品名", "商品名称",
                    "product name", "product title",
                    "nome", "nombre"
                ],
                patterns=[
                    r"(?i)(product[_\s]?name)",
                    r"(?i)(названи[ея])",
                    r"(?i)(商品名称|产品名称)",
                ],
                priority=90,
                category="基础",
                description="商品名称",
                examples=["男士T恤", "Women Dress"]
            ),
            
            # === 销售数据字段 ===
            "orders": FieldPattern(
                name="orders",
                keywords=[
                    "orders", "заказы", "заказ", "order",
                    "订单", "订单数", "销量", "销售量",
                    "order count", "sales quantity",
                    "pedidos", "ventas"
                ],
                patterns=[
                    r"(?i)(order[_\s]?count|orders)",
                    r"(?i)(заказы)",
                    r"(?i)(订单数|销量)",
                ],
                priority=85,
                category="销售",
                description="订单数量",
                validator=lambda x: isinstance(x, (int, float)) and x >= 0,
                examples=[10, 50, 100]
            ),
            
            "revenue": FieldPattern(
                name="revenue",
                keywords=[
                    "revenue", "выручка", "sales",
                    "销售额", "收入", "营业额", "金额",
                    "total sales", "gross sales",
                    "receita", "ingresos"
                ],
                patterns=[
                    r"(?i)(revenue|выручка)",
                    r"(?i)(销售额|收入)",
                    r"(?i)(total[_\s]?sales)",
                ],
                priority=85,
                category="销售",
                description="销售额",
                validator=lambda x: isinstance(x, (int, float)) and x >= 0,
                examples=[10000, 50000.5]
            ),
            
            "units": FieldPattern(
                name="units",
                keywords=[
                    "units", "quantity", "qty",
                    "销量", "数量", "件数",
                    "количество", "штук",
                    "unidades", "cantidad"
                ],
                patterns=[
                    r"(?i)(units|quantity|qty)",
                    r"(?i)(销量|数量)",
                ],
                priority=80,
                category="销售",
                description="销售件数",
                validator=lambda x: isinstance(x, (int, float)) and x >= 0,
                examples=[5, 10, 20]
            ),
            
            # === 流量数据字段 ===
            "impressions": FieldPattern(
                name="impressions",
                keywords=[
                    "impressions", "показы", "показов",
                    "展示", "展现量", "曝光", "浏览量",
                    "views", "pv", "page views",
                    "impresiones", "visualizações"
                ],
                patterns=[
                    r"(?i)(impressions|показы)",
                    r"(?i)(展示量|展现量|曝光)",
                ],
                priority=75,
                category="流量",
                description="展示量",
                validator=lambda x: isinstance(x, (int, float)) and x >= 0,
                examples=[1000, 5000]
            ),
            
            "clicks": FieldPattern(
                name="clicks",
                keywords=[
                    "clicks", "клики", "кликов",
                    "点击", "点击量", "点击数",
                    "click count", "clickthrough",
                    "clics", "clics"
                ],
                patterns=[
                    r"(?i)(clicks|клики)",
                    r"(?i)(点击量|点击数)",
                ],
                priority=75,
                category="流量",
                description="点击量",
                validator=lambda x: isinstance(x, (int, float)) and x >= 0,
                examples=[50, 100]
            ),
            
            "ctr": FieldPattern(
                name="ctr",
                keywords=[
                    "ctr", "click[_\s]?through[_\s]?rate",
                    "点击率", "点击通过率",
                    "коэффициент кликов",
                    "taxa de cliques"
                ],
                patterns=[
                    r"(?i)(ctr|click[_\s]?through[_\s]?rate)",
                    r"(?i)(点击率)",
                ],
                priority=70,
                category="流量",
                description="点击率",
                validator=lambda x: 0 <= x <= 1,
                examples=[0.05, 0.1]
            ),
            
            "card_visits": FieldPattern(
                name="card_visits",
                keywords=[
                    "card[_\s]?visits", "card[_\s]?views",
                    "商品页访问", "详情页浏览",
                    "посещения карточки",
                    "página de producto"
                ],
                patterns=[
                    r"(?i)(card[_\s]?visits)",
                    r"(?i)(商品页访问|详情页)",
                ],
                priority=75,
                category="流量",
                description="商品页访问数",
                validator=lambda x: isinstance(x, (int, float)) and x >= 0,
                examples=[100, 500]
            ),
            
            # === 转化数据字段 ===
            "add_to_cart": FieldPattern(
                name="add_to_cart",
                keywords=[
                    "add[_\s]?to[_\s]?cart", "atc",
                    "加购", "加购数", "加入购物车",
                    "добавить в корзину",
                    "añadir al carrito"
                ],
                patterns=[
                    r"(?i)(add[_\s]?to[_\s]?cart|atc)",
                    r"(?i)(加购数|加入购物车)",
                ],
                priority=70,
                category="转化",
                description="加购数",
                validator=lambda x: isinstance(x, (int, float)) and x >= 0,
                examples=[10, 20]
            ),
            
            "conversion_rate": FieldPattern(
                name="conversion_rate",
                keywords=[
                    "conversion[_\s]?rate", "cvr",
                    "转化率", "成交率",
                    "коэффициент конверсии",
                    "taxa de conversão"
                ],
                patterns=[
                    r"(?i)(conversion[_\s]?rate|cvr)",
                    r"(?i)(转化率|成交率)",
                ],
                priority=70,
                category="转化",
                description="转化率",
                validator=lambda x: 0 <= x <= 1,
                examples=[0.05, 0.1]
            ),
            
            # === 价格数据字段 ===
            "sale_price": FieldPattern(
                name="sale_price",
                keywords=[
                    "price", "цена", "售价", "价格", "单价",
                    "sale[_\s]?price", "selling[_\s]?price",
                    "precio", "preço"
                ],
                patterns=[
                    r"(?i)(sale[_\s]?price|price)",
                    r"(?i)(цена|售价|价格)",
                ],
                priority=85,
                category="价格",
                description="销售价格",
                validator=lambda x: isinstance(x, (int, float)) and x >= 0,
                examples=[99.9, 199]
            ),
            
            "list_price": FieldPattern(
                name="list_price",
                keywords=[
                    "list[_\s]?price", "original[_\s]?price",
                    "原价", "吊牌价", "定价",
                    "исходная цена",
                    "precio original"
                ],
                patterns=[
                    r"(?i)(list[_\s]?price|original[_\s]?price)",
                    r"(?i)(原价|吊牌价)",
                ],
                priority=80,
                category="价格",
                description="原价",
                validator=lambda x: isinstance(x, (int, float)) and x >= 0,
                examples=[199, 299]
            ),
            
            "market_price": FieldPattern(
                name="market_price",
                keywords=[
                    "market[_\s]?price", "avg[_\s]?price",
                    "市场价", "均价", "平均价",
                    "рыночная цена",
                    "precio de mercado"
                ],
                patterns=[
                    r"(?i)(market[_\s]?price|avg[_\s]?price)",
                    r"(?i)(市场价|均价)",
                ],
                priority=75,
                category="价格",
                description="市场均价",
                validator=lambda x: isinstance(x, (int, float)) and x >= 0,
                examples=[150, 250]
            ),
            
            # === 库存数据字段 ===
            "stock_total": FieldPattern(
                name="stock_total",
                keywords=[
                    "stock", "inventory", "quantity",
                    "库存", "库存量", "存货",
                    "остатки", "наличие",
                    "existencias", "estoque"
                ],
                patterns=[
                    r"(?i)(stock|inventory|quantity)",
                    r"(?i)(库存|库存量)",
                    r"(?i)(остатки|наличие)",
                ],
                priority=80,
                category="库存",
                description="总库存",
                validator=lambda x: isinstance(x, (int, float)) and x >= 0,
                examples=[100, 500]
            ),
            
            "stock_fbo": FieldPattern(
                name="stock_fbo",
                keywords=[
                    "fbo[_\s]?stock", "fbo",
                    "FBO库存", "fbo库存",
                    "остатки fbo"
                ],
                patterns=[
                    r"(?i)(fbo[_\s]?stock)",
                    r"(?i)(fbo库存)",
                ],
                priority=75,
                category="库存",
                description="FBO仓库库存",
                validator=lambda x: isinstance(x, (int, float)) and x >= 0,
                examples=[50, 100]
            ),
            
            "days_of_supply": FieldPattern(
                name="days_of_supply",
                keywords=[
                    "days[_\s]?of[_\s]?supply", "dos",
                    "库存天数", "周转天数",
                    "дни поставки"
                ],
                patterns=[
                    r"(?i)(days[_\s]?of[_\s]?supply|dos)",
                    r"(?i)(库存天数|周转天数)",
                ],
                priority=70,
                category="库存",
                description="库存周转天数",
                validator=lambda x: isinstance(x, (int, float)) and x >= 0,
                examples=[30, 60]
            ),
            
            # === 评价数据字段 ===
            "rating": FieldPattern(
                name="rating",
                keywords=[
                    "rating", "рейтинг", "score",
                    "评分", "星级", "评分值",
                    "calificación", "classificação"
                ],
                patterns=[
                    r"(?i)(rating|рейтинг)",
                    r"(?i)(评分|星级)",
                ],
                priority=75,
                category="评价",
                description="商品评分",
                validator=lambda x: 0 <= x <= 5,
                examples=[4.5, 4.8]
            ),
            
            "reviews_count": FieldPattern(
                name="reviews_count",
                keywords=[
                    "reviews", "review[_\s]?count",
                    "评价数", "评论数", "评价数量",
                    "отзывы",
                    "reseñas", "avaliações"
                ],
                patterns=[
                    r"(?i)(reviews?[_\s]?count)",
                    r"(?i)(评价数|评论数)",
                ],
                priority=70,
                category="评价",
                description="评价数量",
                validator=lambda x: isinstance(x, (int, float)) and x >= 0,
                examples=[10, 50]
            ),
            
            "return_rate": FieldPattern(
                name="return_rate",
                keywords=[
                    "return[_\s]?rate", "退货率",
                    "возврат", "коэффициент возврата",
                    "tasa de devolución"
                ],
                patterns=[
                    r"(?i)(return[_\s]?rate)",
                    r"(?i)(退货率)",
                ],
                priority=65,
                category="评价",
                description="退货率",
                validator=lambda x: 0 <= x <= 1,
                examples=[0.05, 0.1]
            ),
            
            # === 广告数据字段 ===
            "ad_spend": FieldPattern(
                name="ad_spend",
                keywords=[
                    "ad[_\s]?spend", "ad[_\s]?cost",
                    "广告花费", "广告费", "推广费",
                    "расходы на рекламу",
                    "gasto publicitario"
                ],
                patterns=[
                    r"(?i)(ad[_\s]?spend|ad[_\s]?cost)",
                    r"(?i)(广告花费|广告费)",
                ],
                priority=70,
                category="广告",
                description="广告花费",
                validator=lambda x: isinstance(x, (int, float)) and x >= 0,
                examples=[1000, 5000]
            ),
            
            "roas": FieldPattern(
                name="roas",
                keywords=[
                    "roas", "return[_\s]?on[_\s]?ad[_\s]?spend",
                    "广告投资回报率", "广告ROI",
                    "romi"
                ],
                patterns=[
                    r"(?i)(roas)",
                    r"(?i)(广告投资回报率)",
                ],
                priority=70,
                category="广告",
                description="广告投资回报率",
                validator=lambda x: isinstance(x, (int, float)) and x >= 0,
                examples=[3.5, 5.0]
            ),
            
            # === 成本数据字段 ===
            "cost_price": FieldPattern(
                name="cost_price",
                keywords=[
                    "cost", "cost[_\s]?price",
                    "成本价", "成本", "进价",
                    "себестоимость",
                    "costo", "custo"
                ],
                patterns=[
                    r"(?i)(cost[_\s]?price|cost)",
                    r"(?i)(成本价|成本)",
                ],
                priority=80,
                category="成本",
                description="成本价",
                validator=lambda x: isinstance(x, (int, float)) and x >= 0,
                examples=[50, 100]
            ),
        }
    
    def detect_field(
        self,
        field_name: str,
        sample_values: Optional[List[any]] = None
    ) -> Tuple[str, float, List[str]]:
        """
        智能识别字段
        
        Args:
            field_name: 原始字段名
            sample_values: 样本值（用于验证）
        
        Returns:
            (standard_field, confidence, reasons)
        """
        field_lower = field_name.lower().strip()
        best_match = "unmapped"
        best_score = 0
        best_reasons = []
        
        for standard_field, pattern in self.field_patterns.items():
            score = 0
            reasons = []
            
            # 1. 关键词匹配（权重 50%）
            for keyword in pattern.keywords:
                keyword_lower = keyword.lower()
                if keyword_lower == field_lower:
                    score += 0.5
                    reasons.append(f"完全匹配关键词: {keyword}")
                elif keyword_lower in field_lower:
                    score += 0.3
                    reasons.append(f"包含关键词: {keyword}")
                else:
                    # 模糊匹配
                    ratio = SequenceMatcher(None, field_lower, keyword_lower).ratio()
                    if ratio > self.fuzzy_threshold:
                        score += ratio * 0.2
                        reasons.append(f"模糊匹配: {keyword} ({ratio:.2f})")
            
            # 2. 正则匹配（权重 30%）
            for regex_pattern in pattern.patterns:
                try:
                    if re.search(regex_pattern, field_name):
                        score += 0.3
                        reasons.append(f"正则匹配: {regex_pattern}")
                except:
                    pass
            
            # 3. 数据验证（权重 20%）
            if sample_values and pattern.validator:
                valid_count = sum(1 for v in sample_values[:5] if pattern.validator(v))
                if valid_count > 0:
                    validation_score = valid_count / min(5, len(sample_values))
                    score += validation_score * 0.2
                    reasons.append(f"数据验证通过: {valid_count}/{min(5, len(sample_values))}")
            
            # 优先级加成
            score += pattern.priority / 1000  # 0.01 - 0.1
            
            if score > best_score:
                best_score = score
                best_match = standard_field
                best_reasons = reasons
        
        # 置信度归一化
        confidence = min(best_score, 1.0)
        
        return best_match, confidence, best_reasons
    
    def map_fields(
        self,
        headers: List[str],
        sample_data: Optional[List[List[any]]] = None
    ) -> List[Dict]:
        """
        批量映射字段
        
        Args:
            headers: 表头列表
            sample_data: 样本数据（每行是一个列表）
        
        Returns:
            映射结果列表
        """
        mappings = []
        
        for idx, header in enumerate(headers):
            # 获取样本值
            sample_values = None
            if sample_data:
                sample_values = [row[idx] for row in sample_data if idx < len(row)]
            
            # 识别字段
            standard_field, confidence, reasons = self.detect_field(header, sample_values)
            
            mappings.append({
                'original_field': header,
                'standard_field': standard_field,
                'confidence': confidence,
                'sample_values': sample_values[:5] if sample_values else [],
                'reasons': reasons,
                'is_manual': False
            })
        
        return mappings
    
    def learn_from_feedback(
        self,
        original_field: str,
        correct_standard_field: str
    ):
        """
        从用户反馈中学习
        
        Args:
            original_field: 原始字段名
            correct_standard_field: 正确的标准字段
        """
        feedback = {
            'original': original_field,
            'correct': correct_standard_field,
            'timestamp': datetime.now().isoformat()
        }
        self.user_feedback.append(feedback)
        
        # 如果该字段不在关键词列表，添加它
        if correct_standard_field in self.field_patterns:
            pattern = self.field_patterns[correct_standard_field]
            if original_field.lower() not in [k.lower() for k in pattern.keywords]:
                pattern.keywords.append(original_field)
        
        # 保存反馈到文件（可选）
        self._save_feedback()
    
    def _save_feedback(self):
        """保存用户反馈到文件"""
        try:
            with open('field_mapping_feedback.json', 'w', encoding='utf-8') as f:
                json.dump(self.user_feedback, f, ensure_ascii=False, indent=2)
        except:
            pass


# 导出
if __name__ == "__main__":
    mapper = IntelligentFieldMapperV3()
    
    # 测试
    test_headers = [
        "Артикул",  # 俄语 SKU
        "商品编码",  # 中文 SKU
        "SKU",      # 英文 SKU
        "Orders Count",  # 英文订单
        "订单数",    # 中文订单
        "Заказы",   # 俄语订单
        "Price",    # 价格
        "Unknown Field"  # 未知字段
    ]
    
    mappings = mapper.map_fields(test_headers)
    
    for m in mappings:
        print(f"{m['original_field']:20} → {m['standard_field']:20} (置信度: {m['confidence']:.2f})")
