#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V5.1 数据导入服务
提供完整的Excel/CSV导入、清洗、验证、保存功能
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import pandas as pd
from dataclasses import dataclass, field
from datetime import datetime
import json

from .models import ImportBatchDiagnosis
from .ingestion import ImportDiagnoser


@dataclass
class ImportResult:
    """导入结果"""
    success: bool
    total_rows: int
    imported: int
    failed: int
    errors: List[Dict] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    data: Optional[List[Dict]] = None

def list_batches(self) -> list:
    """
    列出所有导入批次（示例实现，需根据实际存储方式调整）
    """
    # 这里需要根据你的实际数据存储方式来写
    # 比如从数据库、文件或内存中读取批次列表
    # 以下是示例返回空列表

@dataclass
class FieldMapping:
    """字段映射配置"""
    # Ozon 俄语字段 -> 标准字段
    ozon_mapping = {
        "Артикул": "sku",
        "Показы": "impressions",
        "Добавления в корзину": "add_to_cart",
        "Заказы": "orders",
        "Сумма заказов": "revenue",
        "Рейтинг": "rating",
        "Отзывы": "reviews",
        "Возвраты": "returns",
        "Остатки": "stock",
    }
    
    # 英文字段 -> 标准字段
    english_mapping = {
        "SKU": "sku",
        "sku": "sku",
        "Impressions": "impressions",
        "impressions": "impressions",
        "Add to Cart": "add_to_cart",
        "Orders": "orders",
        "Revenue": "revenue",
        "Rating": "rating",
        "Reviews": "reviews",
        "Returns": "returns",
        "Stock": "stock",
    }


class DataCleaner:
    """数据清洗器"""
    
    @staticmethod
    def clean_numeric(value):
        """清洗数字字段"""
        if pd.isna(value) or value == '' or value is None:
            return None
        
        if isinstance(value, (int, float)):
            return float(value)
        
        # 移除空格、逗号、货币符号
        value_str = str(value)
        value_str = value_str.replace(' ', '').replace(',', '').replace('¥', '').replace('₽', '').replace('$', '')
        value_str = value_str.replace('%', '').replace('руб.', '').replace('CNY', '').replace('RUB', '')
        
        try:
            return float(value_str)
        except:
            return None
    
    @staticmethod
    def clean_text(value):
        """清洗文本字段"""
        if pd.isna(value) or value == '' or value is None:
            return None
        
        value_str = str(value).strip()
        return value_str if value_str else None
    
    @staticmethod
    def clean_rating(value):
        """清洗评分（0-5范围）"""
        rating = DataCleaner.clean_numeric(value)
        if rating is None:
            return None
        
        if rating < 0 or rating > 5:
            return None
        
        return round(rating, 2)
    
    @staticmethod
    def clean_percentage(value):
        """清洗百分比（0-1范围）"""
        pct = DataCleaner.clean_numeric(value)
        if pct is None:
            return None
        
        # 如果大于1，说明是百分比形式（如20表示20%），需要转换
        if pct > 1:
            pct = pct / 100.0
        
        return round(pct, 4)


class DataValidator:
    """数据验证器"""
    
    @staticmethod
    def validate_row(row: Dict, row_index: int) -> Tuple[bool, List[str]]:
        """
        验证单行数据
        
        返回：(是否有效, 错误列表)
        """
        errors = []
        
        # SKU必填
        if not row.get('sku'):
            errors.append(f"行{row_index}: SKU不能为空")
        
        # 订单数不能为负
        if row.get('orders') is not None and row['orders'] < 0:
            errors.append(f"行{row_index}: 订单数不能为负数")
        
        # 评分范围检查
        if row.get('rating') is not None:
            if row['rating'] < 0 or row['rating'] > 5:
                errors.append(f"行{row_index}: 评分必须在0-5之间")
        
        # 收入不能为负
        if row.get('revenue') is not None and row['revenue'] < 0:
            errors.append(f"行{row_index}: 收入不能为负数")
        
        return len(errors) == 0, errors


class ImportService:
    """完整导入服务"""
    
    def __init__(self):
        self.diagnoser = ImportDiagnoser()
        self.cleaner = DataCleaner()
        self.validator = DataValidator()
        self.mapping = FieldMapping()
    
    def read_file(self, file_path: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """
        读取Excel或CSV文件
        
        返回：(DataFrame, 错误信息)
        """
        path = Path(file_path)
        
        if not path.exists():
            return None, f"文件不存在：{file_path}"
        
        try:
            if path.suffix in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path, engine='openpyxl' if path.suffix == '.xlsx' else 'xlrd')
            elif path.suffix == '.csv':
                # 尝试不同编码
                for encoding in ['utf-8', 'utf-8-sig', 'gbk', 'cp1251']:
                    try:
                        df = pd.read_csv(file_path, encoding=encoding)
                        break
                    except:
                        continue
                else:
                    return None, "无法识别文件编码"
            else:
                return None, f"不支持的文件格式：{path.suffix}"
            
            return df, None
            
        except Exception as e:
            return None, f"读取文件失败：{str(e)}"
    
    def map_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        映射列名（俄语/英语 -> 标准字段名）
        """
        column_mapping = {}
        
        for col in df.columns:
            # 尝试Ozon俄语映射
            if col in self.mapping.ozon_mapping:
                column_mapping[col] = self.mapping.ozon_mapping[col]
            # 尝试英语映射
            elif col in self.mapping.english_mapping:
                column_mapping[col] = self.mapping.english_mapping[col]
        
        if column_mapping:
            df = df.rename(columns=column_mapping)
        
        return df
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        清洗数据
        """
        # 清洗数字列
        numeric_columns = ['impressions', 'card_visits', 'add_to_cart', 'orders', 
                          'revenue', 'ad_spend', 'ad_revenue', 'stock']
        
        for col in numeric_columns:
            if col in df.columns:
                df[col] = df[col].apply(self.cleaner.clean_numeric)
        
        # 清洗评分
        if 'rating' in df.columns:
            df['rating'] = df['rating'].apply(self.cleaner.clean_rating)
        
        # 清洗百分比
        percentage_columns = ['return_rate', 'cancel_rate', 'variable_rate_total']
        for col in percentage_columns:
            if col in df.columns:
                df[col] = df[col].apply(self.cleaner.clean_percentage)
        
        # 清洗文本列
        text_columns = ['sku', 'name']
        for col in text_columns:
            if col in df.columns:
                df[col] = df[col].apply(self.cleaner.clean_text)
        
        return df
    
    def validate_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[Dict]]:
        """
        验证数据
        
        返回：(有效数据, 错误列表)
        """
        errors = []
        valid_rows = []
        
        for idx, row in df.iterrows():
            row_dict = row.to_dict()
            is_valid, row_errors = self.validator.validate_row(row_dict, idx + 1)
            
            if is_valid:
                valid_rows.append(row_dict)
            else:
                errors.extend(row_errors)
        
        valid_df = pd.DataFrame(valid_rows) if valid_rows else pd.DataFrame()
        
        return valid_df, errors
    
    def remove_duplicates(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        """
        去重
        
        返回：(去重后的数据, 重复数量)
        """
        if 'sku' not in df.columns:
            return df, 0
        
        before_count = len(df)
        df = df.drop_duplicates(subset=['sku'], keep='first')
        after_count = len(df)
        
        return df, before_count - after_count
    
    def import_from_file(
        self, 
        file_path: str,
        save_to_db: bool = False,
        output_path: Optional[str] = None
    ) -> ImportResult:
        """
        从文件导入数据（完整流程）
        
        Args:
            file_path: 输入文件路径
            save_to_db: 是否保存到数据库（暂未实现）
            output_path: 输出JSON路径（可选）
        
        Returns:
            ImportResult: 导入结果
        """
        # 1. 读取文件
        df, error = self.read_file(file_path)
        if error:
            return ImportResult(
                success=False,
                total_rows=0,
                imported=0,
                failed=0,
                errors=[{"error": error}]
            )
        
        total_rows = len(df)
        
        # 2. 诊断
        preview_rows = df.head(20).values.tolist()
        diagnosis = self.diagnoser.diagnose(
            file_name=Path(file_path).name,
            preview_rows=preview_rows,
            headers=df.columns.tolist(),
            mapped_fields=len(df.columns),
            unmapped_fields=[],
            row_error_count=0
        )
        
        # 检查诊断结果
        if diagnosis.status == "failed":
            return ImportResult(
                success=False,
                total_rows=total_rows,
                imported=0,
                failed=total_rows,
                errors=[{"error": suggestion} for suggestion in diagnosis.suggestions]
            )
        
        # 3. 映射列名
        df = self.map_columns(df)
        
        # 4. 清洗数据
        df = self.clean_data(df)
        
        # 5. 验证数据
        df, errors = self.validate_data(df)
        
        # 6. 去重
        df, duplicate_count = self.remove_duplicates(df)
        
        # 7. 转换为字典列表
        data = df.to_dict('records')
        
        # 8. 保存到JSON（如果指定了输出路径）
        if output_path:
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        "timestamp": datetime.now().isoformat(),
                        "source_file": file_path,
                        "platform": diagnosis.platform,
                        "total_rows": total_rows,
                        "imported": len(data),
                        "duplicates": duplicate_count,
                        "errors": errors,
                        "data": data
                    }, f, ensure_ascii=False, indent=2)
            except Exception as e:
                errors.append({"error": f"保存文件失败：{str(e)}"})
        
        # 9. 返回结果
        return ImportResult(
            success=True,
            total_rows=total_rows,
            imported=len(data),
            failed=total_rows - len(data),
            errors=errors,
            warnings=[f"发现并移除 {duplicate_count} 条重复记录"] if duplicate_count > 0 else [],
            data=data
        )
    
    def save_to_json(self, data: List[Dict], output_path: str, metadata: Optional[Dict] = None):
        """
        保存数据到JSON文件
        """
        output = {
            "timestamp": datetime.now().isoformat(),
            "count": len(data),
            "data": data
        }
        
        if metadata:
            output["metadata"] = metadata
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
