#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能字段映射系统
参考后端利润算法的优秀设计思路
"""

from __future__ import annotations
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import pandas as pd


@dataclass
class FieldPattern:
    """字段模式定义"""
    name: str  # 标准字段名
    keywords: List[str]  # 关键词列表
    patterns: List[str]  # 正则表达式模式
    priority: int  # 优先级（越高越优先）
    validator: Optional[callable] = None  # 数据验证函数


class IntelligentFieldMapper:
    """智能字段映射器 - 参考利润算法的优秀设计"""

    def __init__(self):
        self.field_patterns = self._init_field_patterns()
        self.fuzzy_threshold = 0.7  # 模糊匹配阈值

    def _init_field_patterns(self) -> Dict[str, FieldPattern]:
        """初始化字段模式（参考利润算法的规则引擎）"""
        return {
            # === SKU 字段（最高优先级）===
            "sku": FieldPattern(
                name="sku",
                keywords=[
                    "sku", "артикул", "id", "product", "offer", "seller",
                    "код", "арт", "identifier", "code"
                ],
                patterns=[
                    r"(?i)(seller[_\s]?sku|sku)",
                    r"(?i)(offer[_\s]?id|offerid)",
                    r"(?i)(product[_\s]?id|productid)",
                    r"(?i)(арт[икул]+|art[ikul]+)",
                    r"(?i)(id[_\s]?товара)",
                    r"(?i)(товар[_\s]?id)",
                ],
                priority=100,
                validator=lambda x: bool(re.match(r'^[A-Za-z0-9\-_]+$', str(x)))  # ✅ 修复 f-string 错误
            ),

            # === 产品名称 ===
            "name": FieldPattern(
                name="name",
                keywords=[
                    "name", "название", "title", "наименование",
                    "product", "товар", "назв", "title"
                ],
                patterns=[
                    r"(?i)(product[_\s]?name|productname)",
                    r"(?i)(назв[ание]+)",
                    r"(?i)(наименование)",
                    r"(?i)(title)",
                ],
                priority=90,
            ),

            # === 展示量 ===
            "impressions": FieldPattern(
                name="impressions",
                keywords=[
                    "impressions", "views", "показы", "просмотры",
                    "показ", "просм", "views", "display"
                ],
                patterns=[
                    r"(?i)(impressions?|imp)",
                    r"(?i)(views?|view)",
                    r"(?i)(показ[ы]+)",
                    r"(?i)(просмотр[ы]+)",
                    r"(?i)(display)",
                ],
                priority=80,
                validator=lambda x: isinstance(x, (int, float)) and x >= 0
            ),

            # === 订单数 ===    
            "orders": FieldPattern(
                name="orders",
                keywords=[
                    "orders", "заказы", "order", "заказ",
                    "кол[во]*", "count", "количество"
                ],
                patterns=[
                    r"(?i)(orders?|ord)",
                    r"(?i)(заказ[ы]+)",
                    r"(?i)(кол[во]*[_\s]?заказ)",
                    r"(?i)(order[_\s]?count)",
                ],
                priority=80,
                validator=lambda x: isinstance(x, (int, float)) and x >= 0
            ),

            # === 收入 ===
            "revenue": FieldPattern(
                name="revenue",
                keywords=[
                    "revenue", "sales", "выручка", "сумма",
                    "доход", "sum", "total", "amount"
                ],
                patterns=[
                    r"(?i)(revenue|rev)",
                    r"(?i)(sales|sale)",
                    r"(?i)(выручка)",
                    r"(?i)(сумма[_\s]?заказ)",
                    r"(?i)(total[_\s]?sales)",
                    r"(?i)(amount)",
                ],
                priority=80,
                validator=lambda x: isinstance(x, (int, float)) and x >= 0
            ),

            # === 评分 ===
            "rating": FieldPattern(
                name="rating",
                keywords=[
                    "rating", "рейтинг", "rate", "оценка",
                    "звезд", "star", "score"
                ],
                patterns=[
                    r"(?i)(rating|rate)",
                    r"(?i)(рейтинг)",
                    r"(?i)(оценка)",
                    r"(?i)(star[_\s]?rating)",
                ],
                priority=70,
                validator=lambda x: 0 <= float(x) <= 5 if pd.notna(x) else False
            ),

            # === 库存 ===
            "stock": FieldPattern(
                name="stock",
                keywords=[
                    "stock", "inventory", "остатки", "доступно",
                    "available", "количество", "qty", "balance"
                ],
                patterns=[
                    r"(?i)(stock|stk)",
                    r"(?i)(inventory|inv)",
                    r"(?i)(остатк[и]+)",
                    r"(?i)(доступно)",
                    r"(?i)(available)",
                    r"(?i)(quantity|qty)",
                ],
                priority=70,
                validator=lambda x: isinstance(x, (int, float)) and x >= 0
            ),

            # === 加购数 ===
            "add_to_cart": FieldPattern(
                name="add_to_cart",
                keywords=[
                    "cart", "basket", "корзин", "добав",
                    "add", "to", "basket"
                ],
                patterns=[
                    r"(?i)(add[_\s]?to[_\s]?cart)",
                    r"(?i)(добав[лен]+[_\s]?в[_\s]?корзин)",
                    r"(?i)(cart[_\s]?adds?)",
                    r"(?i)(basket)",
                ],
                priority=60,
            ),

            # === 广告花费 ===
            "ad_spend": FieldPattern(
                name="ad_spend",
                keywords=[
                    "ad", "ads", "реклам", "spend", "cost",
                    "расход", "advertising", "marketing"
                ],
                patterns=[
                    r"(?i)(ad[_\s]?spend)",
                    r"(?i)(advertising[_\s]?cost)",
                    r"(?i)(расход[_\s]?на[_\s]?реклам)",
                    r"(?i)(ads?[_\s]?cost)",
                ],
                priority=60,
            ),

            # === 转化率 ===    
            "conversion_rate": FieldPattern(
                name="conversion_rate",
                keywords=[
                    "conversion", "конверс", "rate", "cvr",
                    "convert"
                ],
                patterns=[
                    r"(?i)(conversion[_\s]?rate)",
                    r"(?i)(конверс[ия]+)",
                    r"(?i)(cvr)",
                ],
                priority=60,
            ),
        }

    def detect_field(self, column_name: str, sample_data: Optional[pd.Series] = None) -> Tuple[Optional[str], float, List[str]]:
        """
        智能检测字段类型（参考利润算法的智能识别）

        参数:
            column_name: 列名
            sample_data: 样本数据（可选，用于验证）

        返回:
            (标准字段名, 置信度, 匹配原因列表)
        """
        matches = []

        # 1. 标准化列名（去除空格、转小写）
        normalized_name = column_name.strip().lower().replace('_', ' ').replace('-', ' ')

        # 2. 遍历所有字段模式
        for field_name, pattern in self.field_patterns.items():
            score = 0.0
            reasons = []

            # 2.1 关键词匹配
            keyword_score = self._match_keywords(normalized_name, pattern.keywords)
            if keyword_score > 0:
                score += keyword_score * 0.5  # 提高到 50% 权重 ✅ 已修复
                reasons.append(f"关键词匹配({keyword_score:.2f})")

            # 2.2 正则表达式匹配
            regex_score = self._match_patterns(column_name, pattern.patterns)
            if regex_score > 0:
                score += regex_score * 0.5  # 提高到 50% 权重 ✅ 已修复
                reasons.append(f"正则匹配({regex_score:.2f})")

            # 2.3 数据验证（如果有样本数据）
            if sample_data is not None and pattern.validator:
                validation_score = self._validate_data(sample_data, pattern.validator)
                if validation_score > 0:
                    score += validation_score * 0.3  # 提高到 30% 权重 ✅ 已修复
                    reasons.append(f"数据验证通过({validation_score:.2f})")

            # 2.4 优先级加成
            score += pattern.priority / 100  # ✅ 已修复：1000 → 100

            if score > 0:
                matches.append((field_name, score, reasons))

        # 3. 选择最高分的匹配
        if not matches:
            return None, 0.0, ["未匹配到任何模式"]

        matches.sort(key=lambda x: x[1], reverse=True)
        best_match = matches[0]

        # 4. 计算置信度（0-1）✅ 已修复：新的归一化公式
        # 修改归一化公式：任何匹配就给基础分 0.5，然后根据匹配质量加分
        base_score = 0.5  # 基础分
        quality_score = min(best_match[1] * 0.5, 0.5)  # 质量分（最多 0.5）
        confidence = base_score + quality_score  # 范围：0.5-1.0

        return best_match[0], confidence, best_match[2]

    def _match_keywords(self, text: str, keywords: List[str]) -> float:
        """关键词匹配（模糊匹配）"""
        text_lower = text.lower()
        matches = sum(1 for kw in keywords if kw.lower() in text_lower)
        return matches / len(keywords) if keywords else 0.0

    def _match_patterns(self, text: str, patterns: List[str]) -> float:
        """正则表达式匹配"""
        matches = sum(1 for pattern in patterns if re.search(pattern, text))
        return matches / len(patterns) if patterns else 0.0

    def _validate_data(self, data: pd.Series, validator: callable) -> float:
        """数据验证（检查前10个非空值）"""
        sample = data.dropna().head(10)
        if len(sample) == 0:
            return 0.0

        valid_count = 0
        for val in sample:
            try:
                if validator(val):
                    valid_count += 1
            except Exception:
                continue
        return valid_count / len(sample)

    def auto_map_columns(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Tuple[str, float, List[str]]]]:
        """
        自动映射所有列（参考利润算法的批量处理）

        返回:
            (映射后的DataFrame, 映射详情字典)
        """
        mapping_info = {}
        column_mapping = {}

        print("\n🔍 智能字段映射分析")
        print("=" * 80)

        for col in df.columns:
            sample_data = df[col] if col in df.columns else None
            standard_name, confidence, reasons = self.detect_field(col, sample_data)

            if standard_name:
                column_mapping[col] = standard_name
                mapping_info[col] = (standard_name, confidence, reasons)

                # 打印映射结果
                status = "✅" if confidence >= 0.7 else "⚠️" if confidence >= 0.4 else "❓"
                print(f"{status} {col:30s} → {standard_name:15s} (置信度: {confidence:.2f})")
                print(f"   原因: {', '.join(reasons)}")
            else:
                print(f"❌ {col:30s} → 无法识别")

        print("=" * 80)
        print(f"✅ 成功映射: {len(column_mapping)}/{len(df.columns)} 个字段")

        # 应用映射
        if column_mapping:
            df = df.rename(columns=column_mapping)

        return df, mapping_info

    def suggest_sku_field(self, df: pd.DataFrame) -> Optional[str]:
        """
        智能识别 SKU 字段（如果自动映射失败）

        返回:
            最可能的 SKU 列名
        """
        candidates = []

        for col in df.columns:
            standard_name, confidence, _ = self.detect_field(col, df[col])

            if standard_name == "sku":
                candidates.append((col, confidence))

        if not candidates:
            return None

        # 返回置信度最高的
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def interactive_mapping(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        交互式映射（如果自动映射置信度低）
        提示用户手动确认映射
        """
        print("\n⚠️  自动映射置信度较低，建议手动确认")
        print("=" * 80)

        for col in df.columns:
            if col in ['sku', 'name', 'impressions', 'orders', 'revenue', 'rating', 'stock']:
                continue

            print(f"\n列名: {col}")
            print(f"示例数据: {df[col].dropna().head(3).tolist()}")

            suggestion = input("请输入标准字段名（或按 Enter 跳过）: ").strip()
            if suggestion and suggestion in self.field_patterns:
                df = df.rename(columns={col: suggestion})
                print(f"✅ 已映射: {col} → {suggestion}")

        return df


# 使用示例
if __name__ == "__main__":
    import pandas as pd

    # 创建测试数据
    data = {
        'Артикул товара': ['SKU-001', 'SKU-002', 'SKU-003'],
        'Название': ['产品A', '产品B', '产品C'],
        'Показы': [1000, 2000, 3000],
        'Кол-во заказов': [10, 20, 30],
        'Сумма продаж': [5000, 10000, 15000],
        'Рейтинг товара': [4.5, 4.8, 4.2],
        'Остатки на складе': [100, 200, 150],
    }

    df = pd.DataFrame(data)

    # 智能映射
    mapper = IntelligentFieldMapper()
    mapped_df, mapping_info = mapper.auto_map_columns(df)

    print("\n映射后的列名:")
    print(mapped_df.columns.tolist())
