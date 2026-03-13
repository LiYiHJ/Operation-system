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
import re

from ecom_v51.models import ImportBatchDiagnosis, ProfitInput
from ecom_v51.ingestion import ImportDiagnoser
from ecom_v51.intelligent_field_mapper import IntelligentFieldMapper
from ecom_v51.db.session import get_session
from ecom_v51.db.models import (
    DimPlatform,
    DimShop,
    DimSku,
    DimDate,
    ImportBatch,
    ImportBatchFile,
    ImportErrorLog,
    MappingFeedback,
    FactSkuDaily,
    FactOrdersDaily,
    FactReviewsDaily,
    FactAdsDaily,
    FactInventoryDaily,
    FactProfitSnapshot,
)
from ecom_v51.profit_solver import ProfitSolver




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


@dataclass
class FieldMapping:
    """字段映射配置"""
    # Ozon 俄语字段 -> 标准字段
    ozon_mapping = {
        # SKU 字段（多种可能的列名）
        "Артикул": "sku",
        "Артикул товара": "sku",
        "SKU": "sku",
        "sku": "sku",
        "ID товара": "sku",
        "Product ID": "sku",
        "Offer ID": "sku",
        "offer_id": "sku",
        "seller_sku": "sku",
        "Seller SKU": "sku",
        
        # 产品名称
        "Название": "name",
        "Название товара": "name",
        "Product name": "name",
        "Name": "name",
        
        # 展示量
        "Показы": "impressions",
        "Просмотры": "impressions",
        "Impressions": "impressions",
        "impressions": "impressions",
        "Views": "impressions",
        
        # 访问量
        "Посещения": "visits",
        "Visits": "visits",
        "Card visits": "visits",
        
        # 加购
        "Добавления в корзину": "add_to_cart",
        "Добавлено в корзину": "add_to_cart",
        "Add to Cart": "add_to_cart",
        "Add to cart": "add_to_cart",
        "Added to cart": "add_to_cart",
        
        # 订单
        "Заказы": "orders",
        "Кол-во заказов": "orders",
        "Orders": "orders",
        "orders": "orders",
        
        # 收入
        "Сумма заказов": "revenue",
        "Выручка": "revenue",
        "Revenue": "revenue",
        "revenue": "revenue",
        "Sales": "revenue",
        
        # 评分
        "Рейтинг": "rating",
        "Rating": "rating",
        "rating": "rating",
        
        # 评论
        "Отзывы": "reviews",
        "Reviews": "reviews",
        "reviews": "reviews",
        
        # 退货
        "Возвраты": "returns",
        "Returns": "returns",
        "returns": "returns",
        
        # 库存
        "Остатки": "stock",
        "Доступно": "stock",
        "Stock": "stock",
        "stock": "stock",
        "Available": "stock",
        
        # 广告相关
        "Расход на рекламу": "ad_spend",
        "Ad spend": "ad_spend",
        "ad_spend": "ad_spend",
        "Рекламные заказы": "ad_orders",
        "Ad orders": "ad_orders",
        
        # 转化率
        "Конверсия": "conversion_rate",
        "Conversion rate": "conversion_rate",
        
        # 取消率
        "Отмены": "cancel_rate",
        "Cancel rate": "cancel_rate",
    }
    
    # 英文字段 -> 标准字段（已整合到上面的映射中）
    english_mapping = {}


class DataCleaner:
    """数据清洗器"""
    
    @staticmethod
    def clean_numeric(value):
        """清洗数字字段"""
        if pd.isna(value) or value == '' or value is None:
            return None
        
        if isinstance(value, (int, float)):
            return float(value)
        
        # 移除空格、货币符号，兼容俄文小数逗号与破折号
        value_str = str(value).strip().replace('−', '-').replace('–', '-').replace('—', '-')
        if value_str in {'', '-', '—', '–'}:
            return None
        value_str = value_str.replace(' ', '').replace('¥', '').replace('₽', '').replace('$', '')
        value_str = value_str.replace('%', '').replace('руб.', '').replace('CNY', '').replace('RUB', '')
        if ',' in value_str and '.' not in value_str:
            value_str = value_str.replace(',', '.')
        else:
            value_str = value_str.replace(',', '')
        
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
        self.batches = []  # 新增这一行
        self._root_dir = Path(__file__).resolve().parents[3]
        self._field_aliases = self._load_json_yaml(self._root_dir / 'config' / 'field_aliases_zh_ru_en.yaml', default={'fields': []})
        self._report_templates = self._load_json_yaml(self._root_dir / 'config' / 'report_templates.yaml', default={'templates': []})
        self._alias_lookup = self._build_alias_lookup(self._field_aliases)
        self.diagnoser = ImportDiagnoser()
        self.cleaner = DataCleaner()
        self.validator = DataValidator()
        self.mapping = FieldMapping()
        self.intelligent_mapper = IntelligentFieldMapper()  # 🆕 智能映射器
        self.profit_solver = ProfitSolver()

    @staticmethod
    def _load_json_yaml(path: Path, default: dict) -> dict:
        if not path.exists():
            return default
        try:
            with path.open('r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, dict) else default
        except Exception:
            return default

    @staticmethod
    def _normalize_header(value: str) -> str:
        return re.sub(r'\s+', ' ', str(value or '').strip().lower())

    def _build_alias_lookup(self, aliases_cfg: dict) -> dict[str, str]:
        lookup: dict[str, str] = {}
        for field in aliases_cfg.get('fields', []):
            canonical = str(field.get('canonical') or '').strip()
            if not canonical:
                continue
            for lang in ['zh', 'ru', 'en', 'platform']:
                for alias in field.get('aliases', {}).get(lang, []):
                    key = self._normalize_header(str(alias))
                    if key:
                        lookup[key] = canonical
            lookup[self._normalize_header(canonical)] = canonical
        return lookup

    def _detect_report_template(self, file_name: str, columns: list[str]) -> str:
        norm_name = self._normalize_header(file_name)
        norm_columns = {self._normalize_header(col) for col in columns}
        best_code = 'generic'
        best_score = -1
        for tpl in self._report_templates.get('templates', []):
            score = 0
            score += sum(1 for k in [self._normalize_header(x) for x in tpl.get('file_name_keywords', [])] if k and k in norm_name)
            score += sum(1 for k in [self._normalize_header(x) for x in tpl.get('header_keywords', [])] if k and k in norm_columns)
            score += 2 * sum(1 for k in [self._normalize_header(x) for x in tpl.get('field_signatures', [])] if k and k in norm_columns)
            if score > best_score:
                best_score = score
                best_code = str(tpl.get('code') or 'generic')
        return best_code

    @staticmethod
    def _is_summary_text(text: str) -> bool:
        value = str(text or '').strip().lower()
        return value in {'总计', '合计', '总计和平均值', 'итого', 'итого и среднее', 'summary', 'total', 'grand total'}

    def _drop_summary_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        if 'sku' not in df.columns:
            return df
        return df.loc[~df['sku'].astype(str).apply(self._is_summary_text)].copy()
    
    def _detect_excel_header_row(self, file_path: str, max_scan_rows: int = 30) -> int:
        """尝试检测 Excel 真正表头行（兼容 Ozon 导出前置说明行）"""
        try:
            preview = pd.read_excel(file_path, header=None, nrows=max_scan_rows, engine='openpyxl')
        except Exception:
            return 0

        known_headers = {str(k).strip().lower() for k in self.mapping.ozon_mapping.keys()}
        known_headers.update({
            'sku', 'seller sku', 'seller_sku', 'offer_id', 'артикул', 'name', 'product name',
            'orders', 'revenue', 'impressions', 'card visits', 'add to cart', 'sale_price',
            'list_price', 'cost_price', 'commission_rate',
        })

        for idx in range(min(len(preview), max_scan_rows)):
            row = [str(x).strip().lower() for x in preview.iloc[idx].tolist() if str(x).strip() and str(x).lower() != 'nan']
            if not row:
                continue
            hit = sum(1 for cell in row if cell in known_headers)
            if hit >= 2:
                return idx
        return 0

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
                if path.suffix == '.xlsx':
                    header_row = self._detect_excel_header_row(file_path)
                    try:
                        df = pd.read_excel(file_path, header=header_row, engine='openpyxl')
                    except Exception as ex:
                        return None, f"读取 XLSX 失败：文件可能损坏、加密或样式异常，请另存为标准 .xlsx 后重试。原始错误：{ex}"
                else:
                    try:
                        df = pd.read_excel(file_path, engine='xlrd')
                    except Exception as ex:
                        return None, f"读取 XLS 失败：请另存为 .xlsx 或 .csv 后重试。原始错误：{ex}"
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
        映射列名（智能识别 + 模糊匹配）
        
        优先使用智能映射器，失败时降级到静态映射
        """
        # 🆕 使用智能映射器
        try:
            mapped_df, mapping_info = self.intelligent_mapper.auto_map_columns(df)
            alias_map = {}
            for col in mapped_df.columns:
                canonical = self._alias_lookup.get(self._normalize_header(col))
                if canonical:
                    alias_map[col] = canonical
            if alias_map:
                mapped_df = mapped_df.rename(columns=alias_map)

            # 检查是否有 SKU 字段
            if 'sku' not in mapped_df.columns:
                # 尝试智能识别 SKU 字段
                suggested_sku = self.intelligent_mapper.suggest_sku_field(df)
                if suggested_sku:
                    print(f"\n💡 建议：将 '{suggested_sku}' 映射为 SKU 字段")
                    # 如果只有一个高置信度的 SKU 候选，自动使用
                    mapped_df = mapped_df.rename(columns={suggested_sku: 'sku'})
                else:
                    print("\n⚠️  警告：未找到 SKU 字段，请手动映射")
            
            return mapped_df
            
        except Exception as e:
            print(f"⚠️  智能映射失败，降级到静态映射：{str(e)}")
            # 降级到旧的静态映射
            column_mapping = {}
            for col in df.columns:
                canonical = self._alias_lookup.get(self._normalize_header(col))
                if canonical:
                    column_mapping[col] = canonical
                    continue
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
        df = df.drop_duplicates(subset=['sku'], keep='last')
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

    def list_batches(self) -> list:
        """
        列出所有导入批次
        """
        if not hasattr(self, 'batches'):
            self.batches = []
        return self.batches

    def parse_import_file(self, file_path: str, shop_id: int = 1, operator: str = 'frontend_user') -> dict:
        """上传后解析文件，返回诊断与映射结果（创建后端草稿 session）"""
        df, error = self.read_file(file_path)
        if error:
            raise ValueError(error)

        mapped_df = self.map_columns(df.copy())
        unmapped_fields = [col for col in df.columns if col not in mapped_df.columns]

        diagnosis = self.diagnoser.diagnose(
            file_name=Path(file_path).name,
            preview_rows=df.head(20).fillna('').values.tolist(),
            headers=df.columns.astype(str).tolist(),
            mapped_fields=len(mapped_df.columns),
            unmapped_fields=unmapped_fields,
            row_error_count=0,
        )

        field_mappings: list[dict] = []
        extra_map = {
            'sale_price': 'sale_price',
            'list_price': 'list_price',
            'cost_price': 'cost_price',
            'commission_rate': 'commission_rate',
            'orders': 'orders',
            'revenue': 'revenue',
            'impressions': 'impressions',
            'add to cart': 'add_to_cart',
            'add_to_cart': 'add_to_cart',
        }
        for col in df.columns.astype(str):
            norm_col = self._normalize_header(col)
            std_field = None
            confidence = 0.0
            reasons: list[str] = []

            # 先用显式映射，避免智能映射误判
            std_field = self._alias_lookup.get(norm_col)
            if not std_field:
                std_field = self.mapping.ozon_mapping.get(col) or self.mapping.ozon_mapping.get(col.strip())
            if not std_field:
                std_field = extra_map.get(norm_col)
            if std_field:
                confidence = 0.95
                reasons = ['explicit_mapping']
            else:
                mapped_name, mapped_conf, mapped_reasons = self.intelligent_mapper.detect_field(col)
                if mapped_name != 'unknown':
                    std_field = mapped_name
                    confidence = mapped_conf
                    reasons = mapped_reasons

            # 防止非SKU字段被错误识别为SKU
            if std_field == 'sku' and norm_col not in {'sku', 'артикул', 'offer_id', 'seller_sku', 'product id'}:
                explicit_sku_alias = {'sku', 'артикул', 'offer_id', 'seller_sku', 'product id'}
                if norm_col not in explicit_sku_alias:
                    std_field = extra_map.get(norm_col)
                    if std_field != 'sku':
                        confidence = 0.8 if std_field else 0.0
                        reasons = ['sku_false_positive_fixed'] if std_field else []

            sample_values = df[col].dropna().head(5).astype(str).tolist() if col in df.columns else []
            field_mappings.append(
                {
                    'originalField': col,
                    'standardField': std_field,
                    'confidence': round(confidence, 3),
                    'sampleValues': sample_values,
                    'isManual': False,
                    'reasons': reasons,
                }
            )

        preview_rows = df.head(10).fillna('').values.tolist()
        template_code = self._detect_report_template(Path(file_path).name, df.columns.astype(str).tolist())

        with get_session() as session:
            platform_code = diagnosis.platform if diagnosis.platform != 'unknown' else 'ozon'
            platform_name = platform_code.upper() if platform_code != 'ozon' else 'Ozon'
            platform = self._ensure_platform(session, platform_code, platform_name)
            shop = self._ensure_shop(session, platform.id, shop_id)

            batch = ImportBatch(
                source_type='file_upload',
                platform_code=platform_code,
                shop_id=shop.id,
                started_at=datetime.utcnow(),
                status='draft',
                message='upload parsed, waiting confirm',
            )
            session.add(batch)
            session.flush()

            mapped_fields_json = {
                'filePath': file_path,
                'fieldMappings': field_mappings,
                'dataPreview': preview_rows,
                'totalRows': len(df),
                'totalColumns': len(df.columns),
                'headerRow': (diagnosis.detected_header_row or 0) + 1,
                'platform': platform_code,
                'diagnosis': {
                    'suggestions': diagnosis.suggestions,
                    'keyField': diagnosis.key_field,
                    'unmappedFields': diagnosis.unmapped_fields,
                    'status': diagnosis.status,
                    'templateCode': template_code,
                },
            }
            batch_file = ImportBatchFile(
                batch_id=batch.id,
                file_name=Path(file_path).name,
                detected_header_row=(diagnosis.detected_header_row or 0) + 1,
                detected_key_field=diagnosis.key_field,
                mapped_fields_json=mapped_fields_json,
                unmapped_fields_json=diagnosis.unmapped_fields,
                status='draft',
            )
            session.add(batch_file)

            return {
                'sessionId': batch.id,
                'fileName': Path(file_path).name,
                'fileSize': Path(file_path).stat().st_size,
                'sheetNames': ['Sheet1'],
                'selectedSheet': 'Sheet1',
                'totalRows': len(df),
                'totalColumns': len(df.columns),
                'headerRow': (diagnosis.detected_header_row or 0) + 1,
                'dataPreview': preview_rows,
                'fieldMappings': field_mappings,
                'mappedCount': len([x for x in field_mappings if x['standardField']]),
                'unmappedCount': len([x for x in field_mappings if not x['standardField']]),
                'confidence': round(sum(x['confidence'] for x in field_mappings) / max(len(field_mappings), 1), 3),
                'platform': platform_code,
                'status': diagnosis.status,
                'templateCode': template_code,
                'diagnosis': {
                    'suggestions': diagnosis.suggestions,
                    'keyField': diagnosis.key_field,
                    'unmappedFields': diagnosis.unmapped_fields,
                    'status': diagnosis.status,
                    'templateCode': template_code,
                },
            }

    def confirm_import(self, session_id: int, shop_id: int, manual_overrides: list[dict], operator: str = 'system') -> dict:
        """确认导入并入库：以后端 draft session 为真实来源"""
        with get_session() as session:
            batch = session.query(ImportBatch).filter(ImportBatch.id == session_id).one_or_none()
            if not batch:
                raise ValueError(f'导入会话不存在: {session_id}')

            batch_file = session.query(ImportBatchFile).filter(ImportBatchFile.batch_id == batch.id).one_or_none()
            if not batch_file:
                raise ValueError(f'导入会话缺少批次文件: {session_id}')

            parsed_state = batch_file.mapped_fields_json or {}
            file_path = parsed_state.get('filePath')
            if not file_path:
                raise ValueError('导入会话缺少源文件路径')

            df, error = self.read_file(file_path)
            if error:
                raise ValueError(error)

            draft_mappings = parsed_state.get('fieldMappings', [])
            merged = {item.get('originalField'): item.get('standardField') for item in draft_mappings if item.get('standardField')}
            for item in manual_overrides or []:
                if item.get('originalField'):
                    merged[item['originalField']] = item.get('standardField')

            rename_map = {k: v for k, v in merged.items() if v}
            df = df.rename(columns=rename_map)
            df = df.loc[:, ~df.columns.duplicated()]
            df = self.clean_data(df)
            df = self._drop_summary_rows(df)
            valid_df, errors = self.validate_data(df)
            valid_df, duplicate_count = self.remove_duplicates(valid_df)

            platform = self._ensure_platform(session, batch.platform_code, 'Ozon')
            shop = self._ensure_shop(session, platform.id, shop_id)

            batch.shop_id = shop.id
            batch.status = 'processing'
            batch_file.mapped_fields_json = {
                **parsed_state,
                'finalMappings': rename_map,
                'manualOverrides': manual_overrides,
                'confirmedBy': operator,
                'confirmedAt': datetime.utcnow().isoformat(),
            }
            batch_file.status = 'processing'

            inserted = 0
            for idx, row in valid_df.iterrows():
                row_dict = row.to_dict()
                try:
                    sku_obj = self._ensure_sku(session, shop.id, str(row_dict.get('sku')), row_dict.get('product_name') or row_dict.get('name'))
                    date_obj = self._ensure_date(session, datetime.utcnow().date())
                    self._upsert_daily_facts(session, batch.id, shop.id, sku_obj.id, date_obj.id, row_dict)
                    inserted += 1
                except Exception as exc:
                    errors.append(f"行{idx + 1}入库失败: {exc}")
                    session.add(
                        ImportErrorLog(
                            batch_file_id=batch_file.id,
                            row_no=idx + 1,
                            column_name=None,
                            error_type='db_insert',
                            raw_value=str(row_dict),
                            error_message=str(exc),
                        )
                    )

            for original, mapped in rename_map.items():
                session.add(
                    MappingFeedback(
                        platform_code=batch.platform_code,
                        raw_field_name=original,
                        mapped_field_name=mapped,
                        confirmed_by=operator,
                        confirmed_at=datetime.utcnow(),
                    )
                )

            batch.success_count = inserted
            batch.error_count = len(errors)
            batch.status = 'success' if inserted > 0 else 'failed'
            batch.message = f"去重{duplicate_count}条，错误{len(errors)}条"
            batch.finished_at = datetime.utcnow()
            batch_file.status = batch.status

            return {
                'sessionId': session_id,
                'batchId': batch.id,
                'importedRows': inserted,
                'errorRows': len(errors),
                'status': batch.status,
                'warnings': [f'发现并移除 {duplicate_count} 条重复记录'] if duplicate_count else [],
                'errors': errors[:20],
            }

    def _ensure_platform(self, session, platform_code: str, platform_name: str) -> DimPlatform:
        obj = session.query(DimPlatform).filter(DimPlatform.platform_code == platform_code).one_or_none()
        if obj:
            return obj
        obj = DimPlatform(platform_code=platform_code, platform_name=platform_name, is_active=True)
        session.add(obj)
        session.flush()
        return obj

    def _ensure_shop(self, session, platform_id: int, shop_id: int) -> DimShop:
        obj = session.query(DimShop).filter(DimShop.id == shop_id).one_or_none()
        if obj:
            return obj
        obj = DimShop(
            id=shop_id,
            platform_id=platform_id,
            shop_code=f'shop-{shop_id}',
            shop_name=f'默认店铺{shop_id}',
            currency_code='RUB',
            timezone='Europe/Moscow',
            status='active',
        )
        session.add(obj)
        session.flush()
        return obj

    def _ensure_sku(self, session, shop_id: int, sku: str, sku_name: str | None) -> DimSku:
        obj = session.query(DimSku).filter(DimSku.shop_id == shop_id, DimSku.sku == sku).one_or_none()
        if obj:
            if sku_name and not obj.sku_name:
                obj.sku_name = sku_name
            return obj
        obj = DimSku(shop_id=shop_id, sku=sku, sku_name=sku_name, status='active', is_active=True)
        session.add(obj)
        session.flush()
        return obj

    def _ensure_date(self, session, target_date) -> DimDate:
        obj = session.query(DimDate).filter(DimDate.date_value == target_date).one_or_none()
        if obj:
            return obj
        obj = DimDate(
            date_value=target_date,
            year=target_date.year,
            month=target_date.month,
            day=target_date.day,
            week_of_year=target_date.isocalendar().week,
        )
        session.add(obj)
        session.flush()
        return obj


    @staticmethod
    def _scalar(value):
        """将可能为 Series/list 的值转成标量"""
        try:
            import pandas as _pd
            if isinstance(value, _pd.Series):
                return value.iloc[0] if len(value) else None
        except Exception:
            pass
        if isinstance(value, (list, tuple)):
            return value[0] if value else None
        return value

    def _upsert_daily_facts(self, session, batch_id: int, shop_id: int, sku_id: int, date_id: int, row: dict) -> None:
        def pick(*keys, default=None):
            for key in keys:
                value = self._scalar(row.get(key))
                if value is not None and value != '':
                    return value
            return default

        fact = (
            session.query(FactSkuDaily)
            .filter(
                FactSkuDaily.date_id == date_id,
                FactSkuDaily.shop_id == shop_id,
                FactSkuDaily.sku_id == sku_id,
            )
            .one_or_none()
        )
        if fact is None:
            fact = FactSkuDaily(
                date_id=date_id,
                shop_id=shop_id,
                sku_id=sku_id,
                batch_id=batch_id,
            )
            session.add(fact)

        impressions_total = int(pick('impressions_total', 'impressions', default=0) or 0)
        card_visits = int(pick('product_card_visits', 'card_visits', 'visits', default=0) or 0)
        add_to_cart_total = int(pick('add_to_cart_total', 'add_to_cart', default=0) or 0)
        items_ordered = int(pick('items_ordered', 'orders', default=0) or 0)
        items_canceled = int(pick('items_canceled', 'cancelled_count', default=0) or 0)
        items_returned = int(pick('items_returned', 'returns', default=0) or 0)
        order_amount = float(pick('order_amount', 'revenue', default=0) or 0)

        fact.impressions_total = impressions_total
        fact.card_visits = card_visits
        fact.add_to_cart_total = add_to_cart_total
        fact.orders_count = items_ordered
        fact.cancelled_count = items_canceled
        fact.returned_count = items_returned
        fact.revenue_ordered = order_amount
        fact.revenue_delivered = float(pick('delivered_amount', default=order_amount) or order_amount)
        fact.batch_id = batch_id

        sale_price = float(pick('sale_price', default=pick('avg_sale_price', 'list_price', default=0)) or 0)
        list_price = float(pick('list_price', default=sale_price) or sale_price)
        fixed_cost_total = float(pick('fixed_cost_total', 'cost_price', default=0) or 0)
        variable_rate_total = float(pick('variable_rate_total', 'commission_rate', default=0.2) or 0.2)
        profit = self.profit_solver.solve_current(
            ProfitInput(
                sale_price=sale_price,
                list_price=list_price,
                variable_rate_total=variable_rate_total,
                fixed_cost_total=fixed_cost_total,
            )
        )

        profit_fact = (
            session.query(FactProfitSnapshot)
            .filter(
                FactProfitSnapshot.date_id == date_id,
                FactProfitSnapshot.shop_id == shop_id,
                FactProfitSnapshot.sku_id == sku_id,
            )
            .one_or_none()
        )
        if profit_fact is None:
            profit_fact = FactProfitSnapshot(
                date_id=date_id,
                shop_id=shop_id,
                sku_id=sku_id,
                batch_id=batch_id,
                sale_price=0.0,
                list_price=0.0,
                fixed_cost_total=0.0,
                variable_rate_total=0.0,
                base_profit=0.0,
                contribution_profit=0.0,
                post_fulfillment_profit=0.0,
                net_profit=0.0,
                net_margin=0.0,
                break_even_price=0.0,
                break_even_discount_ratio=0.0,
            )
            session.add(profit_fact)

        profit_fact.sale_price = sale_price
        profit_fact.list_price = list_price
        profit_fact.fixed_cost_total = fixed_cost_total
        profit_fact.variable_rate_total = variable_rate_total
        profit_fact.base_profit = profit.net_profit
        profit_fact.contribution_profit = profit.net_profit
        profit_fact.post_fulfillment_profit = profit.net_profit
        profit_fact.net_profit = profit.net_profit
        profit_fact.net_margin = profit.net_margin
        profit_fact.break_even_price = profit.break_even_price
        profit_fact.break_even_discount_ratio = profit.break_even_discount_ratio
        profit_fact.batch_id = batch_id

        orders_fact = (
            session.query(FactOrdersDaily)
            .filter(
                FactOrdersDaily.date_id == date_id,
                FactOrdersDaily.shop_id == shop_id,
                FactOrdersDaily.sku_id == sku_id,
            )
            .one_or_none()
        )
        if orders_fact is None:
            orders_fact = FactOrdersDaily(date_id=date_id, shop_id=shop_id, sku_id=sku_id, batch_id=batch_id)
            session.add(orders_fact)
        orders_fact.ordered_qty = items_ordered
        orders_fact.delivered_qty = int(pick('items_delivered', default=items_ordered - items_canceled - items_returned) or 0)
        orders_fact.cancelled_qty = items_canceled
        orders_fact.returned_qty = items_returned
        orders_fact.ordered_amount = order_amount
        orders_fact.delivered_amount = float(pick('delivered_amount', default=order_amount) or order_amount)
        orders_fact.batch_id = batch_id

        reviews_fact = (
            session.query(FactReviewsDaily)
            .filter(
                FactReviewsDaily.date_id == date_id,
                FactReviewsDaily.shop_id == shop_id,
                FactReviewsDaily.sku_id == sku_id,
            )
            .one_or_none()
        )
        if reviews_fact is None:
            reviews_fact = FactReviewsDaily(date_id=date_id, shop_id=shop_id, sku_id=sku_id, batch_id=batch_id)
            session.add(reviews_fact)
        reviews_fact.rating_avg = float(pick('rating_value', 'rating', default=0) or 0)
        reviews_fact.new_reviews_count = int(pick('review_count', 'reviews', default=0) or 0)
        reviews_fact.negative_reviews_count = int(pick('negative_review_count', default=0) or 0)
        reviews_fact.quality_risk_score = float(max(0.0, 5.0 - reviews_fact.rating_avg))
        reviews_fact.batch_id = batch_id

        ads_fact = (
            session.query(FactAdsDaily)
            .filter(
                FactAdsDaily.date_id == date_id,
                FactAdsDaily.shop_id == shop_id,
                FactAdsDaily.sku_id == sku_id,
            )
            .one_or_none()
        )
        if ads_fact is None:
            ads_fact = FactAdsDaily(date_id=date_id, shop_id=shop_id, sku_id=sku_id, campaign_id=None, batch_id=batch_id)
            session.add(ads_fact)
        ads_fact.ad_spend = float(pick('ad_spend', default=0) or 0)
        ads_fact.ad_orders = int(pick('ad_orders', default=0) or 0)
        ads_fact.ad_revenue = float(pick('ad_revenue', default=order_amount) or 0)
        ads_fact.ad_clicks = int(pick('ad_clicks', default=card_visits) or 0)
        ads_fact.cpc = ads_fact.ad_spend / ads_fact.ad_clicks if ads_fact.ad_clicks else 0.0
        ads_fact.roas = ads_fact.ad_revenue / ads_fact.ad_spend if ads_fact.ad_spend else float(pick('ad_revenue_rate', default=0) or 0)
        ads_fact.batch_id = batch_id

        inventory_fact = (
            session.query(FactInventoryDaily)
            .filter(
                FactInventoryDaily.date_id == date_id,
                FactInventoryDaily.shop_id == shop_id,
                FactInventoryDaily.sku_id == sku_id,
            )
            .one_or_none()
        )
        if inventory_fact is None:
            inventory_fact = FactInventoryDaily(date_id=date_id, shop_id=shop_id, sku_id=sku_id, batch_id=batch_id)
            session.add(inventory_fact)
        inventory_fact.stock_total = int(pick('stock_total', 'stock', default=0) or 0)
        inventory_fact.stock_fbo = int(pick('stock_fbo', default=inventory_fact.stock_total) or 0)
        inventory_fact.stock_fbs = int(pick('stock_fbs', default=0) or 0)
        inventory_fact.days_of_supply = float(
            pick('days_of_supply', default=(inventory_fact.stock_total / items_ordered if items_ordered else 0.0)) or 0.0
        )
        inventory_fact.batch_id = batch_id
