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
        self.batches = []  # 新增这一行
        self.diagnoser = ImportDiagnoser()
        self.cleaner = DataCleaner()
        self.validator = DataValidator()
        self.mapping = FieldMapping()
        self.intelligent_mapper = IntelligentFieldMapper()  # 🆕 智能映射器
        self.profit_solver = ProfitSolver()
    
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
        映射列名（智能识别 + 模糊匹配）
        
        优先使用智能映射器，失败时降级到静态映射
        """
        # 🆕 使用智能映射器
        try:
            mapped_df, mapping_info = self.intelligent_mapper.auto_map_columns(df)
            
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
            norm_col = col.lower().strip()
            std_field = None
            confidence = 0.0
            reasons: list[str] = []

            # 先用显式映射，避免智能映射误判
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
                'platform': diagnosis.platform,
                'diagnosis': {
                    'suggestions': diagnosis.suggestions,
                    'keyField': diagnosis.key_field,
                    'unmappedFields': diagnosis.unmapped_fields,
                    'status': diagnosis.status,
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
                'platform': diagnosis.platform,
                'status': diagnosis.status,
                'diagnosis': {
                    'suggestions': diagnosis.suggestions,
                    'keyField': diagnosis.key_field,
                    'unmappedFields': diagnosis.unmapped_fields,
                    'status': diagnosis.status,
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

        fact.impressions_total = int(self._scalar(row.get('impressions')) or 0)
        fact.card_visits = int(self._scalar(row.get('card_visits')) or self._scalar(row.get('visits')) or 0)
        fact.add_to_cart_total = int(self._scalar(row.get('add_to_cart')) or 0)
        fact.orders_count = int(self._scalar(row.get('orders')) or 0)
        fact.cancelled_count = int(self._scalar(row.get('cancelled_count')) or 0)
        fact.returned_count = int(self._scalar(row.get('returns')) or 0)
        fact.revenue_ordered = float(self._scalar(row.get('revenue')) or 0)
        fact.revenue_delivered = float(self._scalar(row.get('revenue')) or 0)
        fact.batch_id = batch_id

        sale_price = float(self._scalar(row.get('sale_price')) or self._scalar(row.get('list_price')) or 0)
        list_price = float(self._scalar(row.get('list_price')) or sale_price)
        fixed_cost_total = float(self._scalar(row.get('fixed_cost_total')) or self._scalar(row.get('cost_price')) or 0)
        variable_rate_total = float(self._scalar(row.get('variable_rate_total')) or self._scalar(row.get('commission_rate')) or 0.2)
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
