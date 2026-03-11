#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整数据导入模块 - 修复导入失败 bug
支持 Excel/CSV/JSON 多格式导入
"""

from __future__ import annotations

import pandas as pd
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
import logging

from .models import ImportBatchDiagnosis, SkuSnapshot
from .ingestion import ImportDiagnoser
from .intelligent_field_mapper import IntelligentFieldMapper

logger = logging.getLogger(__name__)


@dataclass
class ImportError:
    """导入错误详情"""
    row: int
    field: str
    value: any
    error_type: str
    message: str


@dataclass
class ImportResult:
    """导入结果"""
    success: bool
    total_rows: int
    success_rows: int
    failed_rows: int
    data: List[Dict]
    errors: List[ImportError]
    diagnosis: ImportBatchDiagnosis
    field_mapping: Dict[str, str]
    
    def to_dict(self):
        return {
            "success": self.success,
            "total_rows": self.total_rows,
            "success_rows": self.success_rows,
            "failed_rows": self.failed_rows,
            "data": self.data[:10],  # 只返回前10行预览
            "errors": [asdict(e) for e in self.errors[:20]],  # 只返回前20个错误
            "diagnosis": asdict(self.diagnosis),
            "field_mapping": self.field_mapping,
        }


class DataImporter:
    """完整数据导入器 - 修复导入失败问题"""
    
    REQUIRED_FIELDS = {
        "sku": "sku",
        "impressions": "impressions",
        "card_visits": "card_visits",
        "orders": "orders",
        "sale_price": "sale_price",
        "list_price": "list_price",
        "variable_rate_total": "variable_rate_total",
        "fixed_cost_total": "fixed_cost_total",
    }
    
    OPTIONAL_FIELDS = {
        "add_to_cart": "add_to_cart",
        "ad_spend": "ad_spend",
        "ad_revenue": "ad_revenue",
        "stock_total": "stock_total",
        "days_of_supply": "days_of_supply",
        "rating": "rating",
        "return_rate": "return_rate",
        "cancel_rate": "cancel_rate",
    }
    
    DEFAULT_VALUES = {
        "add_to_cart": 0,
        "ad_spend": 0,
        "ad_revenue": 0,
        "stock_total": 0,
        "days_of_supply": 999,
        "rating": 5.0,
        "return_rate": 0.0,
        "cancel_rate": 0.0,
    }
    
    def __init__(self):
        self.diagnoser = ImportDiagnoser()
        self.mapper = IntelligentFieldMapper()
        
    def import_from_file(
        self, 
        file_path: str, 
        sheet_name: Optional[str] = None,
        header_row: Optional[int] = None,
        skip_rows: int = 0
    ) -> ImportResult:
        """
        从文件导入数据（支持 Excel/CSV/JSON）
        
        参数:
            file_path: 文件路径
            sheet_name: Excel 工作表名（可选）
            header_row: 手动指定表头行（可选）
            skip_rows: 跳过行数（可选）
        
        返回:
            ImportResult: 导入结果
        """
        file_path = Path(file_path)
        
        # 1. 读取文件
        try:
            df = self._read_file(file_path, sheet_name, skip_rows)
            logger.info(f"成功读取文件: {file_path}, 行数: {len(df)}")
        except Exception as e:
            logger.error(f"文件读取失败: {e}")
            return self._create_error_result(str(e))
        
        # 2. 智能定位表头
        if header_row is not None:
            df.columns = df.iloc[header_row]
            df = df.drop(df.index[:header_row + 1]).reset_index(drop=True)
            logger.info(f"使用手动指定表头行: {header_row}")
        
        # 3. 智能字段映射
        df, field_mapping, mapping_info = self._auto_map_fields(df)
        logger.info(f"字段映射完成: {len(field_mapping)}/{len(df.columns)}")
        
        # 4. 诊断
        diagnosis = self.diagnoser.diagnose(
            file_name=file_path.name,
            preview_rows=df.head(20).values.tolist(),
            headers=df.columns.tolist(),
            mapped_fields=len(field_mapping),
            unmapped_fields=[col for col in df.columns if col not in field_mapping],
            row_error_count=0,
        )
        
        # 5. 验证必填字段
        missing_fields = self._validate_required_fields(field_mapping)
        if missing_fields:
            error_msg = f"缺少必填字段: {', '.join(missing_fields)}"
            logger.error(error_msg)
            diagnosis.suggestions.append(f"❌ {error_msg}")
            diagnosis.status = "failed"
        
        # 6. 数据清洗和验证
        cleaned_data, errors = self._clean_and_validate(df, field_mapping)
        logger.info(f"数据清洗完成: {len(cleaned_data)} 行成功, {len(errors)} 行失败")
        
        # 7. 生成结果
        return ImportResult(
            success=len(cleaned_data) > 0 and diagnosis.status != "failed",
            total_rows=len(df),
            success_rows=len(cleaned_data),
            failed_rows=len(errors),
            data=cleaned_data,
            errors=errors,
            diagnosis=diagnosis,
            field_mapping=field_mapping,
        )
    
    def _read_file(
        self, 
        file_path: Path, 
        sheet_name: Optional[str] = None,
        skip_rows: int = 0
    ) -> pd.DataFrame:
        """读取不同格式的文件"""
        
        suffix = file_path.suffix.lower()
        
        if suffix in ['.xlsx', '.xls']:
            # Excel 文件
            if sheet_name:
                df = pd.read_excel(file_path, sheet_name=sheet_name, skiprows=skip_rows)
            else:
                df = pd.read_excel(file_path, skiprows=skip_rows)
        
        elif suffix == '.csv':
            # CSV 文件（自动检测编码）
            try:
                df = pd.read_csv(file_path, skiprows=skip_rows, encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, skiprows=skip_rows, encoding='gbk')
        
        elif suffix == '.json':
            # JSON 文件
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                df = pd.DataFrame([data])
            else:
                raise ValueError("不支持的 JSON 格式")
        
        else:
            raise ValueError(f"不支持的文件格式: {suffix}")
        
        return df
    
    def _auto_map_fields(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str], Dict]:
        """智能字段映射"""
        field_mapping = {}
        mapping_info = {}
        
        for col in df.columns:
            # 使用智能映射器
            standard_name, confidence, reasons = self.mapper.detect_field(col, df[col])
            
            if standard_name and confidence >= 0.5:  # 降低阈值到 0.5
                field_mapping[col] = standard_name
                mapping_info[col] = {
                    "standard_name": standard_name,
                    "confidence": confidence,
                    "reasons": reasons,
                }
        
        # 应用映射
        if field_mapping:
            df = df.rename(columns=field_mapping)
        
        return df, field_mapping, mapping_info
    
    def _validate_required_fields(self, field_mapping: Dict[str, str]) -> List[str]:
        """验证必填字段"""
        mapped_standard_fields = set(field_mapping.values())
        required = set(self.REQUIRED_FIELDS.keys())
        
        return list(required - mapped_standard_fields)
    
    def _clean_and_validate(
        self, 
        df: pd.DataFrame, 
        field_mapping: Dict[str, str]
    ) -> Tuple[List[Dict], List[ImportError]]:
        """数据清洗和验证"""
        cleaned_data = []
        errors = []
        
        # 合并必填和可选字段
        all_fields = {**self.REQUIRED_FIELDS, **self.OPTIONAL_FIELDS}
        
        for idx, row in df.iterrows():
            try:
                # 提取数据
                data = {}
                row_has_error = False
                
                # 必填字段
                for col, standard_field in self.REQUIRED_FIELDS.items():
                    if col not in df.columns:
                        errors.append(ImportError(
                            row=idx,
                            field=col,
                            value=None,
                            error_type="missing_field",
                            message=f"缺少必填字段: {col}"
                        ))
                        row_has_error = True
                        continue
                    
                    value = row[col]
                    
                    # 数据清洗
                    cleaned_value = self._clean_value(value, col)
                    
                    # 数据验证
                    if cleaned_value is None or (isinstance(cleaned_value, (int, float)) and pd.isna(cleaned_value)):
                        errors.append(ImportError(
                            row=idx,
                            field=col,
                            value=value,
                            error_type="invalid_value",
                            message=f"字段 {col} 值无效: {value}"
                        ))
                        row_has_error = True
                    else:
                        data[standard_field] = cleaned_value
                
                # 可选字段（使用默认值）
                for col, standard_field in self.OPTIONAL_FIELDS.items():
                    if col in df.columns:
                        value = row[col]
                        cleaned_value = self._clean_value(value, col)
                        data[standard_field] = cleaned_value if cleaned_value is not None else self.DEFAULT_VALUES.get(col, 0)
                    else:
                        data[standard_field] = self.DEFAULT_VALUES.get(col, 0)
                
                # 只有必填字段全部通过才添加
                if not row_has_error:
                    cleaned_data.append(data)
                
            except Exception as e:
                errors.append(ImportError(
                    row=idx,
                    field="unknown",
                    value=None,
                    error_type="processing_error",
                    message=f"行处理错误: {str(e)}"
                ))
        
        return cleaned_data, errors
    
    def _clean_value(self, value: any, field: str) -> any:
        """清洗单个值"""
        if pd.isna(value):
            return None
        
        # 数字字段清洗
        if field in ["impressions", "card_visits", "add_to_cart", "orders", "stock_total"]:
            try:
                # 移除逗号、空格等
                if isinstance(value, str):
                    value = value.replace(',', '').replace(' ', '').strip()
                return int(float(value))
            except (ValueError, TypeError):
                return None
        
        # 百分比字段清洗
        elif field in ["variable_rate_total", "return_rate", "cancel_rate"]:
            try:
                if isinstance(value, str):
                    value = value.replace('%', '').strip()
                    if '.' in value:
                        return float(value) / 100 if float(value) > 1 else float(value)
                    else:
                        return float(value) / 100
                return float(value) if 0 <= float(value) <= 1 else float(value) / 100
            except (ValueError, TypeError):
                return None
        
        # 评分字段清洗
        elif field == "rating":
            try:
                rating = float(value)
                return rating if 0 <= rating <= 5 else None
            except (ValueError, TypeError):
                return None
        
        # 金额字段清洗
        elif field in ["sale_price", "list_price", "ad_spend", "ad_revenue", "fixed_cost_total"]:
            try:
                if isinstance(value, str):
                    value = value.replace(',', '').replace(' ', '').replace('¥', '').replace('$', '').strip()
                return float(value)
            except (ValueError, TypeError):
                return None
        
        # 天数字段清洗
        elif field == "days_of_supply":
            try:
                return float(value)
            except (ValueError, TypeError):
                return None
        
        # 字符串字段
        elif field == "sku":
            return str(value).strip()
        
        # 默认返回原值
        return value
    
    def _create_error_result(self, error_message: str) -> ImportResult:
        """创建错误结果"""
        return ImportResult(
            success=False,
            total_rows=0,
            success_rows=0,
            failed_rows=0,
            data=[],
            errors=[ImportError(
                row=0,
                field="file",
                value=None,
                error_type="file_error",
                message=error_message
            )],
            diagnosis=ImportBatchDiagnosis(
                file_name="unknown",
                detected_header_row=None,
                platform="unknown",
                mapped_fields=0,
                unmapped_fields=[],
                key_field=None,
                row_error_count=0,
                status="failed",
                suggestions=[f"❌ {error_message}"],
            ),
            field_mapping={},
        )


# 使用示例
if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 测试导入
    importer = DataImporter()
    
    # 从命令行获取文件路径
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        result = importer.import_from_file(file_path)
        
        # 输出结果
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        print("用法: python data_importer.py <文件路径>")
