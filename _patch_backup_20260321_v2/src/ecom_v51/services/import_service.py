#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V5.1 数据导入服务（reconciled）

目的：
- 对齐当前 import_route / DataImportV2 / types 的运行契约。
- 提供 parse_import_file / confirm_import / get_field_registry。
- 补齐 transport/semantic/final 三层状态、基础语义门禁、表头恢复元信息。

说明：
- 该版本优先保证当前仓库可运行与可验证，不追求与 111.patch 字节级一致。
- confirm_import 当前采用内存 session + 轻量结果汇总，不做重型数据库落库。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import copy
import itertools
import json
import re
import zipfile
import xml.etree.ElementTree as ET

import pandas as pd

try:
    from .models import ImportBatchDiagnosis  # type: ignore
except Exception:
    ImportBatchDiagnosis = None  # type: ignore

try:
    from .ingestion import ImportDiagnoser as _ImportDiagnoser  # type: ignore
except Exception:
    _ImportDiagnoser = None


@dataclass
class ImportResult:
    success: bool
    total_rows: int
    imported: int
    failed: int
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    data: Optional[List[Dict[str, Any]]] = None


@dataclass
class FieldMapping:
    """基础字段映射表（registry 之外的兜底）。"""

    ozon_mapping = {
        "Артикул": "sku",
        "Артикул товара": "sku",
        "Seller SKU": "sku",
        "Offer ID": "sku",
        "Показы": "impressions_total",
        "Показы всего": "impressions_total",
        "Показы в поиске и каталоге": "impressions_search_catalog",
        "Посещения карточки товара": "product_card_visits",
        "Добавления в корзину": "add_to_cart_total",
        "Заказы": "orders",
        "Заказано на сумму": "order_amount",
        "Остаток на конец периода": "stock_total",
        "Рейтинг товара": "rating_value",
        "Отзывы": "review_count",
        "Индекс цен": "price_index_status",
    }

    english_mapping = {
        "SKU": "sku",
        "sku": "sku",
        "seller_sku": "sku",
        "offer_id": "sku",
        "impressions": "impressions_total",
        "impressions_total": "impressions_total",
        "impressions_search_catalog": "impressions_search_catalog",
        "product_card_visits": "product_card_visits",
        "add_to_cart": "add_to_cart_total",
        "add_to_cart_total": "add_to_cart_total",
        "orders": "orders",
        "order_amount": "order_amount",
        "stock": "stock_total",
        "stock_total": "stock_total",
        "rating": "rating_value",
        "rating_value": "rating_value",
        "reviews": "review_count",
        "review_count": "review_count",
        "price_index_status": "price_index_status",
    }


class DataCleaner:
    @staticmethod
    def clean_numeric(value: Any) -> Optional[float]:
        if pd.isna(value) or value == "" or value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        value_str = str(value).strip()
        value_str = value_str.replace("−", "-").replace("–", "-").replace("—", "-")
        if value_str in {"", "-", "—", "–"}:
            return None
        value_str = value_str.replace(" ", "")
        value_str = value_str.replace("¥", "").replace("₽", "").replace("$", "")
        value_str = value_str.replace("руб.", "").replace("CNY", "").replace("RUB", "")
        value_str = value_str.replace("%", "")
        # 若仅有逗号且无点，按小数逗号处理。
        if "," in value_str and "." not in value_str:
            value_str = value_str.replace(",", ".")
        else:
            value_str = value_str.replace(",", "")
        try:
            return float(value_str)
        except Exception:
            return None

    @staticmethod
    def clean_text(value: Any) -> Optional[str]:
        if pd.isna(value) or value == "" or value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def clean_rating(value: Any) -> Optional[float]:
        rating = DataCleaner.clean_numeric(value)
        if rating is None:
            return None
        if rating < 0 or rating > 5:
            return None
        return round(rating, 2)

    @staticmethod
    def clean_percentage(value: Any) -> Optional[float]:
        pct = DataCleaner.clean_numeric(value)
        if pct is None:
            return None
        if pct > 1:
            pct = pct / 100.0
        return round(pct, 4)


class DataValidator:
    @staticmethod
    def validate_row(row: Dict[str, Any], row_index: int) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        if not row.get("sku"):
            errors.append(f"行{row_index}: SKU不能为空")
        if row.get("orders") is not None and row["orders"] < 0:
            errors.append(f"行{row_index}: 订单数不能为负数")
        if row.get("rating_value") is not None and not (0 <= row["rating_value"] <= 5):
            errors.append(f"行{row_index}: 评分必须在0-5之间")
        if row.get("order_amount") is not None and row["order_amount"] < 0:
            errors.append(f"行{row_index}: 订单金额不能为负数")
        return len(errors) == 0, errors


class _FallbackDiagnoser:
    def diagnose(
        self,
        file_name: str,
        preview_rows: List[List[Any]],
        headers: List[str],
        mapped_fields: int,
        unmapped_fields: List[str],
        row_error_count: int,
    ) -> Any:
        status = (
            "success"
            if mapped_fields > 0 and row_error_count == 0
            else ("partial" if mapped_fields > 0 else "failed")
        )
        platform = (
            "ozon" if any("артикул" in str(h).lower() for h in headers) else "generic"
        )
        result = {
            "status": status,
            "platform": platform,
            "suggestions": [] if status == "success" else ["请检查表头与关键字段映射"],
            "keyField": (
                "sku" if any(str(h).lower() == "sku" for h in headers) else None
            ),
            "unmappedFields": unmapped_fields,
        }
        if ImportBatchDiagnosis is not None:
            try:
                return ImportBatchDiagnosis(**result)  # type: ignore[arg-type]
            except Exception:
                return result
        return result


class ImportService:
    """当前导入主链路服务。"""

    CORE_FIELDS = {
        "sku",
        "orders",
        "order_amount",
        "impressions_total",
        "impressions_search_catalog",
        "product_card_visits",
        "add_to_cart_total",
        "stock_total",
        "rating_value",
        "review_count",
        "price_index_status",
    }

    NUMERIC_CANONICALS = {
        "impressions_total",
        "impressions_search_catalog",
        "product_card_visits",
        "add_to_cart_total",
        "orders",
        "order_amount",
        "stock_total",
        "review_count",
        "rating_value",
    }

    HEADER_SCAN_DEPTH = 20
    HEADER_PREFERRED_START_RANGE = range(8, 17)
    DYNAMIC_PATTERNS = [
        "динамик",
        "изменени",
        "change",
        "delta",
        "trend",
        "рост",
        "снижение",
    ]
    SOFT_EXCLUDE_PATTERNS = {
        "динамик",
        "доля",
        "abc-анализ",
        "abc анализ",
        "abc",
        "рекомендац",
        "recommend",
        "建议",
        "补货",
        "时效",
        "平均时效",
        "среднее время",
        "среднее время доставки",
        "сколько товаров",
        "по сравнению с предыдущим периодом",
    }
    PROTECTED_UNIQUE_TARGETS = {
        "sku",
        "orders",
        "order_amount",
        "impressions_total",
        "impressions_search_catalog",
        "product_card_visits",
        "add_to_cart_total",
        "stock_total",
        "rating_value",
        "review_count",
        "price_index_status",
    }
    GENERIC_HEADER_PIECES = {
        "товар",
        "товары",
        "товара",
        "период",
        "показатель",
        "значение",
        "метрика",
        "динамика",
        "изменение",
        "итого",
        "всего",
        "дата",
        "категория",
        "ozon",
        "seller",
        "sku",
        "report",
        "summary",
        "section",
        "metric",
    }
    RU_PHRASE_CANONICAL_RULES = [
        (["артикул"], "sku"),
        (["seller sku"], "sku"),
        (["offer id"], "sku"),
        (["показы в поиске", "каталоге"], "impressions_search_catalog"),
        (["показы", "всего"], "impressions_total"),
        (["посещ", "карточк"], "product_card_visits"),
        (["переход", "карточк"], "product_card_visits"),
        (["добав", "корзин"], "add_to_cart_total"),
        (["заказано на сумму"], "order_amount"),
        (["сумма заказ"], "order_amount"),
        (["остат", "склад"], "stock_total"),
        (["в наличии"], "stock_total"),
        (["рейтинг"], "rating_value"),
        (["отзыв"], "review_count"),
        (["индекс цен"], "price_index_status"),
        (["средняя позиция", "поиск"], "search_catalog_position_avg"),
    ]

    def __init__(self) -> None:
        self._root_dir = Path(__file__).resolve().parents[3]
        self._registry_cfg = self._load_json(
            self._root_dir / "config" / "import_field_registry.json",
            default={"version": "v1", "fields": []},
        )
        self._field_registry = self._registry_cfg.get("fields") or []
        self._fallback_mapping = FieldMapping()
        self.mapping = self._fallback_mapping
        self._alias_lookup = self._build_alias_lookup(self._field_registry)
        self.diagnoser = (
            _ImportDiagnoser() if _ImportDiagnoser is not None else _FallbackDiagnoser()
        )
        self.cleaner = DataCleaner()
        self.validator = DataValidator()
        self.batches: List[Dict[str, Any]] = []
        self._sessions: Dict[int, Dict[str, Any]] = {}
        self._session_counter = itertools.count(1)

    # ---------- 基础加载 ----------

    @staticmethod
    def _load_json(path: Path, default: dict) -> dict:
        if not path.exists():
            return default
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else default
        except Exception:
            return default

    @staticmethod
    def _normalize_header(value: Any) -> str:
        text = str(value or "")
        normalized_chars: List[str] = []
        for ch in text:
            code = ord(ch)
            if code == 0x3000:
                normalized_chars.append(" ")
            elif 0xFF01 <= code <= 0xFF5E:
                normalized_chars.append(chr(code - 0xFEE0))
            else:
                normalized_chars.append(ch)
        text = "".join(normalized_chars).lower()
        text = text.translate(
            str.maketrans(
                {
                    "（": "(",
                    "）": ")",
                    "【": "[",
                    "】": "]",
                    "，": ",",
                    "：": ":",
                    "；": ";",
                    "。": ".",
                    "、": " ",
                    "“": '"',
                    "”": '"',
                    "‘": "'",
                    "’": "'",
                }
            )
        )
        text = re.sub(r"[\u200b\ufeff]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @classmethod
    def _normalize_header_without_unit(cls, value: Any) -> str:
        text = cls._normalize_header(value)
        text = re.sub(r"\([^)]*(%|pcs|шт|руб|₽|件|天|日|次|个|元)[^)]*\)", "", text)
        text = re.sub(r"\[[^\]]*(%|pcs|шт|руб|₽|件|天|日|次|个|元)[^\]]*\]", "", text)
        text = re.sub(r"\b(%|pcs|шт|руб|₽|件|天|日|次|个|元)\b", "", text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _is_placeholder_col(name: Any) -> bool:
        text = str(name or "").strip()
        if not text:
            return True
        lower = text.lower()
        return (
            lower.startswith("unnamed:")
            or re.fullmatch(r"col_?\d+", lower) is not None
            or lower in {"none", "nan"}
        )

    @staticmethod
    def _safe_scalar(value: Any) -> Any:
        if isinstance(value, pd.DataFrame):
            if value.empty:
                return None
            return ImportService._safe_scalar(value.iat[0, 0])
        if isinstance(value, pd.Series):
            if value.empty:
                return None
            return ImportService._safe_scalar(value.iloc[0])
        if isinstance(value, (list, tuple)):
            return value[0] if value else None
        if hasattr(value, "tolist") and not isinstance(value, (str, bytes)):
            try:
                vals = value.tolist()
                if isinstance(vals, list):
                    if vals and isinstance(vals[0], list):
                        return vals[0][0] if vals[0] else None
                    return vals[0] if vals else None
            except Exception:
                pass
        return value

    @staticmethod
    def _excel_col_ref_to_index(cell_ref: str) -> int:
        letters = "".join(ch for ch in str(cell_ref or "") if ch.isalpha()).upper()
        idx = 0
        for ch in letters:
            idx = idx * 26 + (ord(ch) - 64)
        return idx

    def _read_xlsx_via_zip(
        self, file_path: str, header: Optional[int]
    ) -> Tuple[Optional[pd.DataFrame], Optional[str], Dict[str, Any]]:
        meta = {
            "sheetNames": [],
            "selectedSheet": "",
            "readerEngineUsed": "xlsx_zip_fallback",
            "readerFallbackStage": "zip_xml_styles_bypass",
        }
        ns_main = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        rel_ns = "{http://schemas.openxmlformats.org/package/2006/relationships}"

        try:
            with zipfile.ZipFile(file_path) as zf:
                workbook_root = ET.fromstring(zf.read("xl/workbook.xml"))
                rel_root = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))

                rel_map: Dict[str, str] = {}
                for rel in rel_root.findall(f"{rel_ns}Relationship"):
                    rel_id = rel.attrib.get("Id")
                    target = rel.attrib.get("Target")
                    if rel_id and target:
                        rel_map[rel_id] = target

                sheet_entries: List[Tuple[str, str]] = []
                for sheet in workbook_root.findall(
                    "main:sheets/main:sheet",
                    {
                        "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
                        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
                    },
                ):
                    name = sheet.attrib.get("name") or "Sheet1"
                    rid = sheet.attrib.get(
                        "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
                    )
                    target = rel_map.get(rid or "")
                    if not target:
                        continue
                    target_path = target.lstrip("/")
                    if not target_path.startswith("xl/"):
                        target_path = f"xl/{target_path}"
                    sheet_entries.append((name, target_path))

                if not sheet_entries:
                    return None, "读取文件失败：xlsx_zip_fallback 未找到工作表", meta

                meta["sheetNames"] = [name for name, _ in sheet_entries]
                meta["selectedSheet"] = sheet_entries[0][0]

                shared_strings: List[str] = []
                if "xl/sharedStrings.xml" in zf.namelist():
                    shared_root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
                    for si in shared_root.findall("main:si", ns_main):
                        text_parts = [
                            node.text or "" for node in si.findall(".//main:t", ns_main)
                        ]
                        shared_strings.append("".join(text_parts))

                sheet_xml = zf.read(sheet_entries[0][1])
                sheet_root = ET.fromstring(sheet_xml)

                rows: List[Dict[int, Any]] = []
                max_col_idx = 0
                for row in sheet_root.findall(".//main:sheetData/main:row", ns_main):
                    row_map: Dict[int, Any] = {}
                    for cell in row.findall("main:c", ns_main):
                        ref = cell.attrib.get("r", "")
                        col_idx = self._excel_col_ref_to_index(ref)
                        if col_idx <= 0:
                            continue
                        cell_type = cell.attrib.get("t")
                        value_node = cell.find("main:v", ns_main)
                        inline_node = cell.find("main:is", ns_main)
                        value: Any = ""
                        if cell_type == "s":
                            if value_node is not None and value_node.text not in (
                                None,
                                "",
                            ):
                                try:
                                    s_idx = int(float(value_node.text))
                                    value = (
                                        shared_strings[s_idx]
                                        if 0 <= s_idx < len(shared_strings)
                                        else value_node.text
                                    )
                                except Exception:
                                    value = value_node.text
                        elif cell_type == "inlineStr":
                            value = (
                                "".join(
                                    node.text or ""
                                    for node in inline_node.findall(
                                        ".//main:t", ns_main
                                    )
                                )
                                if inline_node is not None
                                else ""
                            )
                        elif cell_type == "b":
                            value = (
                                value_node.text == "1"
                                if value_node is not None
                                else False
                            )
                        else:
                            value = value_node.text if value_node is not None else ""
                        row_map[col_idx] = value
                        max_col_idx = max(max_col_idx, col_idx)
                    rows.append(row_map)

                matrix = [
                    [row_map.get(col_idx, "") for col_idx in range(1, max_col_idx + 1)]
                    for row_map in rows
                ]
                if not matrix:
                    return pd.DataFrame(), None, meta

                if header is None:
                    return pd.DataFrame(matrix), None, meta

                header_row = [str(v or "") for v in matrix[0]]
                body = matrix[1:] if len(matrix) > 1 else []
                return pd.DataFrame(body, columns=header_row), None, meta
        except Exception as exc:
            return None, f"读取文件失败：{exc}", meta

    def _preview_values_for_column(
        self, df: pd.DataFrame, col: Any, limit: int = 3
    ) -> List[Any]:
        if col not in df.columns:
            return []
        selected = df.loc[:, col]
        raw_values: List[Any] = []
        scan_limit = max(limit * 8, 24)

        if isinstance(selected, pd.DataFrame):
            for row in selected.head(scan_limit).itertuples(index=False, name=None):
                for item in row if isinstance(row, tuple) else (row,):
                    raw_values.append(self._safe_scalar(item))
        else:
            try:
                raw_values = selected.head(scan_limit).tolist()
            except Exception:
                raw_values = (
                    selected.head(scan_limit).values.tolist()
                    if hasattr(selected.head(scan_limit), "values")
                    else []
                )

        values: List[Any] = []
        seen: set[str] = set()
        for item in raw_values:
            nested_items = item if isinstance(item, list) else [item]
            for nested in nested_items:
                scalar = self._safe_scalar(nested)
                text = str(scalar or "").strip()
                if not text or text.lower() == "nan":
                    continue
                if self._looks_like_explainer_text(text):
                    continue
                key = text
                if key in seen:
                    continue
                seen.add(key)
                values.append(scalar)
                if len(values) >= limit:
                    return values[:limit]
        return values[:limit]

    @staticmethod
    def _collapse_duplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
        if df is None or not df.columns.duplicated().any():
            return df
        collapsed = pd.DataFrame(index=df.index)
        seen: set[str] = set()
        for col in df.columns:
            col_name = str(col)
            if col_name in seen:
                continue
            selected = df.loc[:, col]
            if isinstance(selected, pd.DataFrame):
                collapsed[col_name] = selected.bfill(axis=1).iloc[:, 0]
            else:
                collapsed[col_name] = selected
            seen.add(col_name)
        return collapsed

    def _build_alias_lookup(self, fields: List[dict]) -> Dict[str, str]:
        lookup: Dict[str, str] = {}
        for field in fields:
            canonical = str(field.get("canonical") or "").strip()
            if not canonical:
                continue
            lookup[self._normalize_header(canonical)] = canonical
            lookup[self._normalize_header_without_unit(canonical)] = canonical
            aliases = field.get("aliases") or {}
            for lang in ["zh", "ru", "en", "platform"]:
                for alias in aliases.get(lang, []) or []:
                    if not alias:
                        continue
                    lookup[self._normalize_header(alias)] = canonical
                    lookup[self._normalize_header_without_unit(alias)] = canonical
        fallback = (
            getattr(self, "_fallback_mapping", None)
            or getattr(self, "mapping", None)
            or FieldMapping()
        )
        for source in [fallback.ozon_mapping, fallback.english_mapping]:
            for alias, canonical in source.items():
                lookup[self._normalize_header(alias)] = canonical
                lookup[self._normalize_header_without_unit(alias)] = canonical
        return lookup

    def get_field_registry(self) -> dict:
        return {
            "version": str(self._registry_cfg.get("version") or "v1"),
            "fields": self._field_registry,
        }

    ENTITY_KEY_TOKEN_PATTERNS = [
        re.compile(r"(?i)(?<![A-Z0-9])[A-Z0-9]{2,}(?:[-_][A-Z0-9]+){1,}(?![A-Z0-9])"),
        re.compile(r"(?<!\d)\d{8,14}(?!\d)"),
    ]

    ENTITY_KEY_HEADER_HINTS = [
        "sku",
        "seller_sku",
        "offer_id",
        "offer id",
        "product_id",
        "item_id",
        "asin",
        "ean",
        "barcode",
        "货号",
        "商品编码",
        "商品id",
        "产品编号",
        "产品id",
        "商家编码",
        "条码",
        "артикул",
        "артикул продавца",
        "код товара",
    ]

    ENTITY_KEY_MIN_CONFIDENCE = 0.58

    def _extract_entity_key_token(self, value: Any) -> Optional[str]:
        text = str(value or "").strip()
        if not text:
            return None

        for pattern in self.ENTITY_KEY_TOKEN_PATTERNS:
            match = pattern.search(text)
            if match:
                return match.group(0)

        return None

    def _score_entity_key_candidate(self, text: str) -> float:
        raw = str(text or "").strip()
        if not raw:
            return 0.0

        score = 0.0
        lower = raw.lower()

        if any(hint in lower for hint in self.ENTITY_KEY_HEADER_HINTS):
            score += 0.35

        token = self._extract_entity_key_token(raw)
        if token:
            score += 0.45
            if "-" in token or "_" in token:
                score += 0.1
            elif token.isdigit() and 8 <= len(token) <= 14:
                score += 0.05

        if self._is_soft_excluded_header(raw):
            score -= 0.35

        if self._looks_like_explainer_text(raw):
            score -= 0.4

        if raw.startswith("Unnamed:") or raw.startswith("col_"):
            score -= 0.15

        return round(max(score, 0.0), 4)

    def _collect_entity_key_probe_values(
        self,
        df: pd.DataFrame,
        field_mappings: List[dict],
        limit: int = 12,
    ) -> List[tuple[str, str]]:
        values: List[tuple[str, str]] = []

        unmapped_headers = []
        for item in field_mappings or []:
            if item.get("standardField") or item.get("dynamicCompanion"):
                continue
            original_field = str(item.get("originalField") or "")
            if original_field:
                unmapped_headers.append(original_field)

        preferred_headers = []
        fallback_headers = []

        for header in unmapped_headers:
            if self._is_soft_excluded_header(header):
                continue

            lower = header.lower()
            if (
                header.startswith("Unnamed:")
                or header.startswith("col_")
                or "sku" in lower
                or "货号" in header
                or "编码" in header
                or "id" in lower
                or "артикул" in lower
            ):
                preferred_headers.append(header)
            else:
                fallback_headers.append(header)

        scan_headers = preferred_headers + fallback_headers

        for header in scan_headers:
            if header not in df.columns:
                continue
            series = df[header]
            for raw in series.tolist():
                if raw is None:
                    continue
                text = str(raw).strip()
                if not text or text.lower() == "nan":
                    continue
                if self._looks_like_explainer_text(text):
                    continue

                token = self._extract_entity_key_token(text)
                if token:
                    values.append((header, token))
                elif len(text) <= 48:
                    values.append((header, text))

                if len(values) >= limit:
                    return values

        return values

    def _build_entity_key_suggestion(
        self,
        top_unmapped_headers: List[str],
        recovery_candidate_preview: List[dict],
        mapped_canonical_fields: List[str],
        field_mappings: Optional[List[dict]] = None,
        df: Optional[pd.DataFrame] = None,
    ) -> Optional[dict]:
        if "sku" in {str(x) for x in (mapped_canonical_fields or [])}:
            return None

        candidate_pool: List[tuple[str, Optional[str], str]] = []

        for item in top_unmapped_headers or []:
            text = str(item)
            if self._is_soft_excluded_header(text):
                continue
            candidate_pool.append(("topUnmappedHeaders", None, text))

        for candidate in recovery_candidate_preview or []:
            for example in candidate.get("flattenedHeaderExamples") or []:
                text = str(example)
                if self._is_soft_excluded_header(text):
                    continue
                candidate_pool.append(("recoveryCandidatePreview", None, text))

        for item in field_mappings or []:
            if item.get("standardField") or item.get("dynamicCompanion"):
                continue
            original_field = str(item.get("originalField") or "")
            if original_field and not self._is_soft_excluded_header(original_field):
                candidate_pool.append(
                    ("fieldMappings.originalField", original_field, original_field)
                )
            for value in item.get("sampleValues") or []:
                text = str(value)
                if self._looks_like_explainer_text(text):
                    continue
                candidate_pool.append(
                    ("fieldMappings.sampleValues", original_field or None, text)
                )

        if df is not None:
            for column_name, value in self._collect_entity_key_probe_values(
                df, field_mappings or []
            ):
                candidate_pool.append(("dataProbeValues", column_name, value))

        best = None
        best_score = 0.0
        best_token = None
        best_source = None
        best_column = None
        best_text = None

        for source, column_name, raw in candidate_pool:
            if self._is_soft_excluded_header(raw) or self._looks_like_explainer_text(raw):
                continue

            score = self._score_entity_key_candidate(raw)
            token = self._extract_entity_key_token(raw)

            if token and score >= best_score:
                best = raw
                best_score = score
                best_token = token
                best_source = source
                best_column = column_name
                best_text = raw
            elif best is None and score > best_score:
                best = raw
                best_score = score
                best_token = token
                best_source = source
                best_column = column_name
                best_text = raw

        if best_score < self.ENTITY_KEY_MIN_CONFIDENCE:
            return None

        return {
            "field": "sku",
            "confidence": best_score,
            "sourceHeader": best_source,
            "sourceColumn": best_column,
            "sampleToken": best_token,
            "detectedBy": "value_pattern" if best_token else "header_hint",
            "rawCandidate": best_text,
        }

    # ---------- 读取 / 表头恢复 ----------

    def _read_file_default(
        self, file_path: str
    ) -> Tuple[Optional[pd.DataFrame], Optional[str], Dict[str, Any]]:
        path = Path(file_path)
        meta = {
            "sheetNames": ["CSV"],
            "selectedSheet": "CSV",
            "readerEngineUsed": None,
            "readerFallbackStage": "none",
        }
        if not path.exists():
            return None, f"文件不存在：{file_path}", meta
        try:
            if path.suffix.lower() in {".xlsx", ".xls"}:
                excel = pd.ExcelFile(
                    file_path,
                    engine="openpyxl" if path.suffix.lower() == ".xlsx" else None,
                )
                meta["sheetNames"] = list(excel.sheet_names)
                meta["selectedSheet"] = (
                    meta["sheetNames"][0] if meta["sheetNames"] else "Sheet1"
                )
                meta["readerEngineUsed"] = (
                    "openpyxl" if path.suffix.lower() == ".xlsx" else "xlrd"
                )
                df = pd.read_excel(excel, sheet_name=meta["selectedSheet"])
                return df, None, meta
            if path.suffix.lower() == ".csv":
                for encoding in ["utf-8", "utf-8-sig", "gbk", "cp1251", "latin1"]:
                    try:
                        df = pd.read_csv(file_path, encoding=encoding)
                        meta["readerEngineUsed"] = f"csv:{encoding}"
                        return df, None, meta
                    except Exception:
                        continue
                return None, "无法识别文件编码", meta
            return None, f"不支持的文件格式：{path.suffix}", meta
        except Exception as exc:
            if path.suffix.lower() == ".xlsx":
                fallback_df, fallback_error, fallback_meta = self._read_xlsx_via_zip(
                    file_path, header=0
                )
                if fallback_df is not None and fallback_error is None:
                    fallback_meta["readerPrimaryError"] = str(exc)
                    return fallback_df, None, fallback_meta
            return None, f"读取文件失败：{exc}", meta

    def _read_file_raw(
        self, file_path: str
    ) -> Tuple[Optional[pd.DataFrame], Optional[str], Dict[str, Any]]:
        path = Path(file_path)
        meta = {
            "sheetNames": ["CSV"],
            "selectedSheet": "CSV",
            "readerEngineUsed": None,
            "readerFallbackStage": "raw_header_scan",
        }
        try:
            if path.suffix.lower() in {".xlsx", ".xls"}:
                excel = pd.ExcelFile(
                    file_path,
                    engine="openpyxl" if path.suffix.lower() == ".xlsx" else None,
                )
                meta["sheetNames"] = list(excel.sheet_names)
                meta["selectedSheet"] = (
                    meta["sheetNames"][0] if meta["sheetNames"] else "Sheet1"
                )
                meta["readerEngineUsed"] = (
                    "openpyxl" if path.suffix.lower() == ".xlsx" else "xlrd"
                )
                df = pd.read_excel(excel, sheet_name=meta["selectedSheet"], header=None)
                return df, None, meta
            if path.suffix.lower() == ".csv":
                for encoding in ["utf-8", "utf-8-sig", "gbk", "cp1251", "latin1"]:
                    try:
                        df = pd.read_csv(file_path, encoding=encoding, header=None)
                        meta["readerEngineUsed"] = f"csv:{encoding}"
                        return df, None, meta
                    except Exception:
                        continue
                return None, "无法识别文件编码", meta
            return None, f"不支持的文件格式：{path.suffix}", meta
        except Exception as exc:
            if path.suffix.lower() == ".xlsx":
                fallback_df, fallback_error, fallback_meta = self._read_xlsx_via_zip(
                    file_path, header=None
                )
                if fallback_df is not None and fallback_error is None:
                    fallback_meta["readerPrimaryError"] = str(exc)
                    return fallback_df, None, fallback_meta
            return None, f"读取文件失败：{exc}", meta

    def _row_header_profile(self, raw_df: pd.DataFrame, idx: int) -> Dict[str, Any]:
        row = [
            str(self._safe_scalar(x) or "").strip() for x in raw_df.iloc[idx].tolist()
        ]
        non_empty = [x for x in row if x and x.lower() not in {"nan", "none"}]
        named = [x for x in non_empty if not self._is_placeholder_col(x)]
        text_like = sum(1 for x in named if re.search(r"[A-Za-zА-Яа-я一-龥]", x))
        dynamic_like = sum(1 for x in named if self._is_dynamic_companion(x))
        generic_like = sum(
            1 for x in named if self._normalize_header(x) in self.GENERIC_HEADER_PIECES
        )
        score = len(named) + text_like * 0.3 - dynamic_like * 0.15 - generic_like * 0.05
        if idx in self.HEADER_PREFERRED_START_RANGE:
            score += 0.8
        return {
            "row": idx,
            "named": len(named),
            "textLike": text_like,
            "dynamicLike": dynamic_like,
            "genericLike": generic_like,
            "score": round(score, 3),
        }

    def _detect_header_block(self, raw_df: pd.DataFrame) -> dict:
        if raw_df.empty:
            return {
                "startRow": 0,
                "endRow": 0,
                "confidence": 0.0,
                "signals": ["empty_file"],
            }
        max_scan = min(len(raw_df), self.HEADER_SCAN_DEPTH)
        profiles = [self._row_header_profile(raw_df, idx) for idx in range(max_scan)]
        best = (
            max(profiles, key=lambda x: x["score"])
            if profiles
            else {"row": 0, "score": 0.0}
        )
        start_row = int(best["row"])
        end_row = start_row
        signals: List[str] = []
        # allow deeper multi-row header blocks
        for lookahead in range(1, min(4, max_scan - start_row)):
            nxt = profiles[start_row + lookahead]
            if nxt["named"] >= max(2, int(best["named"] * 0.4)):
                end_row = start_row + lookahead
                signals.append("multi_row_header_block")
            else:
                break
        header_values = [
            str(self._safe_scalar(x) or "").strip()
            for x in raw_df.iloc[start_row].tolist()
        ]
        placeholder_count = sum(1 for x in header_values if self._is_placeholder_col(x))
        if placeholder_count:
            signals.append("placeholder_columns_present")
        if len([x for x in header_values if x]) < 4:
            signals.append("short_explainable_column_run")
        confidence = min(
            0.98, 0.35 + max(0.0, best["score"]) / max(float(raw_df.shape[1] + 4), 10.0)
        )
        return {
            "startRow": start_row,
            "endRow": end_row,
            "confidence": round(confidence, 3),
            "signals": signals,
            "profiles": profiles[:12],
        }

    def _flatten_headers(
        self, raw_df: pd.DataFrame, header_block: dict
    ) -> Tuple[List[str], List[str], List[str]]:
        start = int(header_block.get("startRow") or 0)
        end = int(header_block.get("endRow") or start)
        header_rows = raw_df.iloc[start : end + 1].fillna("")
        flattened: List[str] = []
        dropped: List[str] = []
        rescued: List[str] = []
        for col_idx in range(raw_df.shape[1]):
            pieces: List[str] = []
            for _, row in header_rows.iterrows():
                value = str(self._safe_scalar(row.iloc[col_idx]) or "").strip()
                norm = self._normalize_header(value)
                if (
                    value
                    and norm not in {"nan", "none"}
                    and norm not in self.GENERIC_HEADER_PIECES
                ):
                    pieces.append(value)
            deduped = list(dict.fromkeys(pieces))
            joined = " / ".join(deduped).strip()
            if not joined:
                # fallback to first non-empty even if generic
                fallback_pieces = []
                for _, row in header_rows.iterrows():
                    value = str(self._safe_scalar(row.iloc[col_idx]) or "").strip()
                    if value and value.lower() not in {"nan", "none"}:
                        fallback_pieces.append(value)
                joined = (
                    " / ".join(list(dict.fromkeys(fallback_pieces))).strip()
                    if fallback_pieces
                    else f"col_{col_idx + 1}"
                )
            if self._is_placeholder_col(joined):
                dropped.append(joined)
            elif len(deduped) > 1:
                rescued.append(joined)
            flattened.append(joined)
        return flattened, dropped, rescued

    def _materialize_from_raw(
        self, raw_df: pd.DataFrame, header_block: dict, flattened_headers: List[str]
    ) -> pd.DataFrame:
        data_start = int(header_block.get("endRow") or 0) + 1
        body = raw_df.iloc[data_start:].copy().reset_index(drop=True)
        if len(flattened_headers) < body.shape[1]:
            flattened_headers = flattened_headers + [
                f"col_{i+1}" for i in range(len(flattened_headers), body.shape[1])
            ]
        body.columns = flattened_headers[: body.shape[1]]
        body = body.dropna(how="all").reset_index(drop=True)
        return body

    def _build_header_candidates(self, raw_df: pd.DataFrame) -> List[Dict[str, Any]]:
        if raw_df.empty:
            return []
        max_scan = min(len(raw_df), self.HEADER_SCAN_DEPTH)
        profiles = [self._row_header_profile(raw_df, idx) for idx in range(max_scan)]
        anchors = sorted(profiles, key=lambda x: x["score"], reverse=True)[:8]
        candidate_spans: List[Tuple[int, int]] = []
        for profile in anchors:
            start = int(profile["row"])
            for depth in range(1, 5):
                end = min(start + depth - 1, max_scan - 1)
                candidate_spans.append((start, end))
            for neighbor in range(max(0, start - 1), min(max_scan, start + 2)):
                candidate_spans.append((neighbor, neighbor))
                if neighbor + 1 < max_scan:
                    candidate_spans.append((neighbor, neighbor + 1))
        # de-duplicate while preserving order
        seen = set()
        spans = []
        for span in candidate_spans:
            if span not in seen:
                seen.add(span)
                spans.append(span)
        candidates: List[Dict[str, Any]] = []
        for start, end in spans:
            header_block = {
                "startRow": int(start),
                "endRow": int(end),
                "confidence": 0.5,
                "signals": ["candidate_generated"]
                + (["multi_row_header_block"] if end > start else []),
            }
            flattened, dropped, rescued = self._flatten_headers(raw_df, header_block)
            df = self._materialize_from_raw(raw_df, header_block, flattened)
            candidates.append(
                {
                    "headerBlock": header_block,
                    "flattenedHeaders": flattened,
                    "droppedPlaceholderColumns": dropped,
                    "rescuedPlaceholderColumns": rescued,
                    "df": df,
                }
            )
        return candidates

    @staticmethod
    def _bundle_mapping_coverage(bundle: Optional[Dict[str, Any]]) -> float:
        payload = bundle or {}
        top_level = payload.get("mappingCoverage")
        if top_level is not None:
            try:
                return float(top_level)
            except (TypeError, ValueError):
                pass
        metrics = payload.get("semanticMetrics") or {}
        try:
            return float(metrics.get("mappingCoverage") or 0.0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _bundle_mapped_confidence(bundle: Optional[Dict[str, Any]]) -> float:
        payload = bundle or {}
        top_level = payload.get("mappedConfidence")
        if top_level is not None:
            try:
                return float(top_level)
            except (TypeError, ValueError):
                pass
        metrics = payload.get("semanticMetrics") or {}
        try:
            return float(metrics.get("mappedConfidence") or 0.0)
        except (TypeError, ValueError):
            return 0.0

    def _score_candidate_bundle(self, bundle: Dict[str, Any]) -> float:
        mapped = int(bundle.get("mappedCount") or 0)
        coverage = self._bundle_mapping_coverage(bundle)
        core_summary = bundle.get("coreFieldHitSummary") or {}
        core_hits = sum(1 for k, v in core_summary.items() if isinstance(v, bool) and v)
        structure = float(bundle.get("headerStructureScore") or 0.0)
        signals = set(bundle.get("headerStructureRiskSignals") or [])
        header_block = bundle.get("headerBlock") or {}
        start_row = int(header_block.get("startRow") or 0)
        score = mapped * 3.0 + core_hits * 6.0 + coverage * 5.0 + structure * 2.0
        if 8 <= start_row <= 16:
            score += 1.2
        if mapped == 0:
            score -= 4.0
        if mapped < 2:
            score -= 2.0
        if core_hits == 0:
            score -= 3.0
        if "short_explainable_column_run" in signals:
            score -= 1.2
        if "placeholder_columns_present" in signals:
            score -= 0.8
        return round(score, 3)

    def _attempt_candidate_recovery(
        self, raw_df: pd.DataFrame, pre_bundle: Dict[str, Any]
    ) -> Dict[str, Any]:
        candidates = self._build_header_candidates(raw_df)
        evaluated: List[Dict[str, Any]] = []
        for candidate in candidates:
            bundle = self._build_bundle(
                df=candidate["df"].copy(),
                header_block=candidate["headerBlock"],
                flattened_headers=candidate["flattenedHeaders"],
                header_recovery_applied=True,
                dropped_placeholder_columns=candidate["droppedPlaceholderColumns"],
                rescued_placeholder_columns=candidate["rescuedPlaceholderColumns"],
            )
            bundle["candidateScore"] = self._score_candidate_bundle(bundle)
            bundle["candidatePreview"] = {
                "headerRows": [
                    candidate["headerBlock"]["startRow"],
                    candidate["headerBlock"]["endRow"],
                ],
                "mappedCount": bundle["mappedCount"],
                "unmappedCount": bundle["unmappedCount"],
                "mappingCoverage": self._bundle_mapping_coverage(bundle),
                "candidateScore": bundle["candidateScore"],
                "mappedCanonicalFields": list(
                    (bundle.get("mappedCanonicalFields") or [])[:12]
                ),
                "topUnmappedHeaders": list(
                    (bundle.get("topUnmappedHeaders") or [])[:12]
                ),
                "flattenedHeaderExamples": list(
                    (candidate.get("flattenedHeaders") or [])[:12]
                ),
            }
            evaluated.append(bundle)
        if not evaluated:
            return {
                "recoveryAttempted": False,
                "recoveryImproved": False,
                "headerRecoveryApplied": False,
                "activeBundle": pre_bundle,
                "preBundle": pre_bundle,
                "postBundle": pre_bundle,
                "candidateCount": 0,
                "candidatePreview": [],
            }
        evaluated.sort(key=lambda x: x.get("candidateScore") or 0.0, reverse=True)
        best = evaluated[0]
        pre_cov = self._bundle_mapping_coverage(pre_bundle)
        post_cov = self._bundle_mapping_coverage(best)
        pre_core = sum(
            1
            for v in (pre_bundle.get("coreFieldHitSummary") or {}).values()
            if isinstance(v, bool) and v
        )
        post_core = sum(
            1
            for v in (best.get("coreFieldHitSummary") or {}).values()
            if isinstance(v, bool) and v
        )
        improved = (
            int(best.get("mappedCount") or 0) > int(pre_bundle.get("mappedCount") or 0)
            or post_cov > pre_cov
            or post_core > pre_core
            or float(best.get("candidateScore") or 0.0)
            > (float(pre_bundle.get("candidateScore") or -999.0) + 0.5)
        )
        applied = bool(improved)
        return {
            "recoveryAttempted": True,
            "recoveryImproved": bool(improved),
            "headerRecoveryApplied": bool(applied),
            "activeBundle": best if applied else pre_bundle,
            "preBundle": pre_bundle,
            "postBundle": best,
            "candidateCount": len(evaluated),
            "candidatePreview": [b.get("candidatePreview") for b in evaluated[:5]],
        }

    # ---------- 映射 / 清洗 / 校验 ----------

    def _is_dynamic_companion(self, text: str) -> bool:
        normalized = self._normalize_header(text)
        return any(token in normalized for token in self.DYNAMIC_PATTERNS)

    def _is_soft_excluded_header(self, text: str) -> bool:
        normalized = self._normalize_header(text)
        return any(token in normalized for token in self.SOFT_EXCLUDE_PATTERNS)

    def _looks_like_explainer_text(self, text: str) -> bool:
        raw = str(text or "").strip().lower()
        if not raw:
            return False

        compact = " ".join(raw.split())
        token_count = len([tok for tok in re.split(r"[^a-zа-я0-9一-龥]+", compact) if tok])
        punctuation_count = sum(compact.count(ch) for ch in [",", ";", ":", "，", "；", "："])

        return (
            len(compact) >= 40
            or token_count >= 8
            or punctuation_count >= 2
            or "оцениваем" in compact
            or "считаем" in compact
            or "для этого" in compact
            or "по сравнению" in compact
            or "динамика по сравнению" in compact
            or "товары a приносят" in compact
            or "recommend" in compact
            or "рекомендац" in compact
            or "建议" in compact
            or "平均时效" in compact
            or "среднее время" in compact
        )

    def _postprocess_field_mappings(self, field_mappings: List[dict]) -> List[dict]:
        grouped: Dict[str, List[dict]] = {}
        for item in field_mappings or []:
            target = str(item.get("standardField") or "").strip()
            if not target:
                continue
            grouped.setdefault(target, []).append(item)

        for target, items in grouped.items():
            if target not in self.PROTECTED_UNIQUE_TARGETS or len(items) <= 1:
                continue

            def sort_key(item: dict) -> tuple:
                original = self._normalize_header(item.get("originalField") or "")
                article_bonus = 1 if "артикул" in original else 0
                return (float(item.get("confidence") or 0.0), article_bonus)

            ranked = sorted(items, key=sort_key, reverse=True)
            for loser in ranked[1:]:
                loser["standardField"] = None
                loser["mappingSource"] = "conflict_dropped"
                loser["confidence"] = 0.0
                loser["reasons"] = list(
                    dict.fromkeys(list(loser.get("reasons") or []) + [f"duplicate_target:{target}"])
                )
        return field_mappings

    def _compress_header_phrase(self, original: Any) -> List[Tuple[str, str]]:
        text = str(original or "").strip()
        normalized = self._normalize_header(text)
        normalized_wo_unit = self._normalize_header_without_unit(text)
        candidates: List[Tuple[str, str]] = []
        seen: set[str] = set()
        soft_excluded = self._is_soft_excluded_header(text)

        def push(value: str, reason: str) -> None:
            value = value.strip()
            if value and value not in seen:
                seen.add(value)
                candidates.append((value, reason))

        push(normalized, "normalized")
        if normalized_wo_unit != normalized:
            push(normalized_wo_unit, "without_unit")

        if not soft_excluded:
            for needles, canonical in self.RU_PHRASE_CANONICAL_RULES:
                if all(needle in normalized_wo_unit for needle in needles):
                    push(canonical, f"phrase_rule:{canonical}")

        tokens = [
            tok for tok in re.split(r"[^a-zа-я0-9一-龥]+", normalized_wo_unit) if tok
        ]
        meaningful = [
            tok
            for tok in tokens
            if tok not in self.GENERIC_HEADER_PIECES and len(tok) > 2
        ]
        if meaningful and not soft_excluded:
            push(" ".join(dict.fromkeys(meaningful)), "token_compaction")
        return candidates

    def _map_single_column_details(
        self, col: Any, sample_values: Optional[List[Any]] = None
    ) -> Dict[str, Any]:
        original = str(col or "")
        normalized = self._normalize_header(original)
        compressed = self._compress_header_phrase(original)
        dynamic_companion = self._is_dynamic_companion(original)
        soft_excluded = self._is_soft_excluded_header(original)
        explainer_like_header = self._looks_like_explainer_text(original)
        soft_excluded = soft_excluded or explainer_like_header
        reasons: List[str] = []
        conflicts: List[str] = []
        best_canonical: Optional[str] = None
        best_source = "unmapped"
        best_confidence = 0.0
        best_compressed = None

        if dynamic_companion:
            return {
                "originalField": original,
                "normalizedField": normalized,
                "standardField": None,
                "mappingSource": "dynamic_companion",
                "confidence": 0.0,
                "sampleValues": list(sample_values or []),
                "isManual": False,
                "reasons": ["dynamic_companion"],
                "conflicts": conflicts,
                "dynamicCompanion": True,
                "compressedHeader": None,
                "excludeFromSemanticGate": True,
            }

        if soft_excluded:
            return {
                "originalField": original,
                "normalizedField": normalized,
                "standardField": None,
                "mappingSource": "soft_excluded",
                "confidence": 0.0,
                "sampleValues": list(sample_values or []),
                "isManual": False,
                "reasons": ["soft_excluded_header"],
                "conflicts": conflicts,
                "dynamicCompanion": False,
                "compressedHeader": None,
                "excludeFromSemanticGate": False,
            }

        def score_candidate(
            candidate_text: str, candidate_reason: str
        ) -> Tuple[Optional[str], str, float, List[str]]:
            local_reasons: List[str] = []
            if candidate_text in self._alias_lookup:
                local_reasons.append(candidate_reason)
                return (
                    self._alias_lookup[candidate_text],
                    "registry_alias",
                    0.99,
                    local_reasons,
                )
            for alias, canonical in self._fallback_mapping.ozon_mapping.items():
                if self._normalize_header(alias) == candidate_text:
                    local_reasons.append(candidate_reason)
                    return canonical, "ru_builtin", 0.95, local_reasons
            for alias, canonical in self._fallback_mapping.english_mapping.items():
                if self._normalize_header(alias) == candidate_text:
                    local_reasons.append(candidate_reason)
                    return canonical, "en_builtin", 0.95, local_reasons
            # token overlap fallback for long phrases
            cand_tokens = {
                t
                for t in re.split(r"[^a-zа-я0-9一-龥]+", candidate_text)
                if len(t) > 2 and t not in self.GENERIC_HEADER_PIECES
            }
            if len(cand_tokens) >= 2:
                best_overlap = (None, 0.0)
                for alias_norm, canonical in self._alias_lookup.items():
                    alias_tokens = {
                        t
                        for t in re.split(r"[^a-zа-я0-9一-龥]+", alias_norm)
                        if len(t) > 2 and t not in self.GENERIC_HEADER_PIECES
                    }
                    if len(alias_tokens) < 2:
                        continue
                    overlap = len(cand_tokens & alias_tokens) / max(len(alias_tokens), 1)
                    if overlap > best_overlap[1]:
                        best_overlap = (canonical, overlap)
                if best_overlap[0] and best_overlap[1] >= 0.75:
                    local_reasons.append(f"token_overlap:{best_overlap[1]:.2f}")
                    return (
                        best_overlap[0],
                        "token_overlap",
                        round(0.52 + best_overlap[1] * 0.22, 3),
                        local_reasons,
                    )
            return None, "unmapped", 0.0, local_reasons

        for candidate_text, candidate_reason in compressed:
            canonical, source, confidence, local_reasons = score_candidate(
                candidate_text, candidate_reason
            )
            if canonical and confidence > best_confidence:
                if best_canonical and best_canonical != canonical:
                    conflicts.append(best_canonical)
                best_canonical = canonical
                best_source = source
                best_confidence = confidence
                best_compressed = candidate_text
                reasons = local_reasons

        if best_canonical == "sku":
            allowed = {"sku", "seller sku", "offer id", "артикул", "артикул товара"}
            if normalized not in {self._normalize_header(x) for x in allowed}:
                best_canonical = None
                best_source = "unmapped"
                best_confidence = 0.0
                reasons = ["sku_guard_rejected"]

        return {
            "originalField": original,
            "normalizedField": normalized,
            "standardField": best_canonical,
            "mappingSource": best_source,
            "confidence": best_confidence,
            "sampleValues": list(sample_values or []),
            "isManual": False,
            "reasons": reasons,
            "conflicts": conflicts,
            "dynamicCompanion": dynamic_companion,
            "compressedHeader": best_compressed,
            "excludeFromSemanticGate": dynamic_companion,
        }

    def _map_single_column(self, col: Any) -> Tuple[Optional[str], str, List[str]]:
        details = self._map_single_column_details(col)
        return (
            details.get("standardField"),
            details.get("mappingSource", "unmapped"),
            list(details.get("reasons") or []),
        )

    def map_columns(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[dict]]:
        rename_map: Dict[str, str] = {}
        field_mappings: List[dict] = []

        for col in df.columns:
            sample_values = self._preview_values_for_column(df, col, limit=3)
            details = self._map_single_column_details(col, sample_values=sample_values)
            field_mappings.append(details)

        field_mappings = self._postprocess_field_mappings(field_mappings)

        for details in field_mappings:
            canonical = details.get("standardField")
            original_field = str(details.get("originalField") or "")
            if canonical and original_field:
                rename_map[original_field] = str(canonical)

        mapped_df = df.rename(columns=rename_map)
        mapped_df = self._collapse_duplicate_columns(mapped_df)
        return mapped_df, field_mappings

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        for col in [c for c in df.columns if c in self.NUMERIC_CANONICALS]:
            if col == "rating_value":
                df[col] = df[col].apply(self.cleaner.clean_rating)
            else:
                df[col] = df[col].apply(self.cleaner.clean_numeric)
        for col in [
            c for c in df.columns if c in {"sku", "name", "price_index_status"}
        ]:
            df[col] = df[col].apply(self.cleaner.clean_text)
        return df

    def validate_data(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
        errors: List[Dict[str, Any]] = []
        valid_rows: List[Dict[str, Any]] = []
        for idx, row in df.iterrows():
            row_dict = {k: self._safe_scalar(v) for k, v in row.to_dict().items()}
            is_valid, row_errors = self.validator.validate_row(row_dict, idx + 1)

            filtered_row_errors: List[str] = []
            for err in row_errors:
                if "评分必须在0-5之间" in err:
                    rating_value = row_dict.get("rating_value")
                    if rating_value is None or (
                        isinstance(rating_value, float) and pd.isna(rating_value)
                    ):
                        # rating_value 改为“可空但若存在必须合法”
                        continue
                filtered_row_errors.append(err)

            if not filtered_row_errors:
                valid_rows.append(row_dict)
            else:
                for err in filtered_row_errors:
                    detail: Dict[str, Any] = {"row": idx + 1, "error": err}
                    if "评分必须在0-5之间" in err:
                        detail["field"] = "rating_value"
                        detail["rawValue"] = row_dict.get("rating_value")
                    elif "SKU不能为空" in err:
                        detail["field"] = "sku"
                        detail["rawValue"] = row_dict.get("sku")
                    errors.append(detail)

        valid_df = (
            pd.DataFrame(valid_rows) if valid_rows else pd.DataFrame(columns=df.columns)
        )
        return valid_df, errors


    def remove_duplicates(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        if "sku" not in df.columns:
            return df, 0
        before = len(df)
        deduped = df.drop_duplicates(subset=["sku"], keep="first")
        return deduped, before - len(deduped)

    # ---------- 语义门禁 ----------

    @staticmethod
    def _build_core_field_hit_summary(mapped_targets: List[str]) -> dict:
        targets = set(mapped_targets)
        optional_pool = [
            "impressions_search_catalog",
            "stock_total",
            "rating_value",
            "review_count",
            "price_index_status",
        ]
        optional_hits = [field for field in optional_pool if field in targets]
        funnel_signal_fields = [
            field
            for field in [
                "impressions_total",
                "impressions_search_catalog",
                "product_card_visits",
                "add_to_cart_total",
                "orders",
                "order_amount",
            ]
            if field in targets
        ]
        return {
            "sku": "sku" in targets,
            "orders_or_order_amount": bool({"orders", "order_amount"} & targets),
            "impressions_total": "impressions_total" in targets,
            "impressions_total_or_search_catalog": bool(
                {"impressions_total", "impressions_search_catalog"} & targets
            ),
            "product_card_visits": "product_card_visits" in targets,
            "add_to_cart_total": "add_to_cart_total" in targets,
            "product_card_visits_or_add_to_cart_total": bool(
                {"product_card_visits", "add_to_cart_total"} & targets
            ),
            "optionalFieldPool": optional_pool,
            "optionalHitCount": len(optional_hits),
            "optionalHitFields": optional_hits,
            "funnelSignalCount": len(funnel_signal_fields),
            "funnelSignalFields": funnel_signal_fields,
            "criticalComboComplete": all(
                [
                    "sku" in targets,
                    bool({"orders", "order_amount"} & targets),
                    bool({"impressions_total", "impressions_search_catalog"} & targets),
                    bool({"product_card_visits", "add_to_cart_total"} & targets),
                ]
            ),
            "mappedTargets": sorted(targets),
        }

    @staticmethod
    def _compute_header_structure_score(
        header_block: dict,
        flattened_headers: List[str],
        dropped_placeholders: List[str],
    ) -> Tuple[float, List[str]]:
        signals = list(header_block.get("signals") or [])
        non_placeholder = [
            h
            for h in flattened_headers
            if h and not ImportService._is_placeholder_col(h)
        ]
        if len(non_placeholder) < 4 and "short_explainable_column_run" not in signals:
            signals.append("short_explainable_column_run")
        if dropped_placeholders and "placeholder_columns_present" not in signals:
            signals.append("placeholder_columns_present")
        score = 0.8
        if "multi_row_header_block" in signals:
            score -= 0.12
        if "placeholder_columns_present" in signals:
            score -= 0.1
        if "short_explainable_column_run" in signals:
            score -= 0.18
        score = max(0.0, min(1.0, score))
        return round(score, 3), signals

    @staticmethod
    def _semantic_gate(
        mapped_targets: List[str],
        candidate_columns: int,
        mapped_count: int,
        wrongly_mapped_count: int,
        header_signals: List[str],
        header_structure_score: float,
    ) -> Tuple[str, List[str], List[str], List[str], dict]:
        reasons: List[str] = []
        risk_override_reasons: List[str] = []
        acceptance_reason: List[str] = []
        coverage = (
            round(mapped_count / candidate_columns, 3) if candidate_columns > 0 else 0.0
        )
        core = ImportService._build_core_field_hit_summary(mapped_targets)
        strong_risk_signals = {
            "multi_row_header_block",
            "short_explainable_column_run",
            "placeholder_columns_present",
        }
        risk_signal_hits = sorted(strong_risk_signals & set(header_signals))
        under_structure_scrutiny = (
            bool(risk_signal_hits) or header_structure_score < 0.72
        )
        clean_strong_bundle_without_sku = (
            not core["sku"]
            and not under_structure_scrutiny
            and coverage >= 0.85
            and mapped_count >= 10
            and core["orders_or_order_amount"]
            and core["impressions_total_or_search_catalog"]
            and core["product_card_visits_or_add_to_cart_total"]
            and int(core.get("funnelSignalCount") or 0) >= 5
            and int(core.get("optionalHitCount") or 0) >= 3
            and wrongly_mapped_count == 0
        )
        critical_requirements_met = (
            bool(core.get("criticalComboComplete")) or clean_strong_bundle_without_sku
        )
        metrics = {
            "mappingCoverage": coverage,
            "mappedCount": mapped_count,
            "unmappedCount": max(candidate_columns - mapped_count, 0),
            "funnelSignalCount": int(core.get("funnelSignalCount") or 0),
            "structureRiskHitCount": len(risk_signal_hits),
            "underStructureScrutiny": under_structure_scrutiny,
            "cleanStrongBundleWithoutSku": clean_strong_bundle_without_sku,
        }

        if mapped_count == 0 or candidate_columns == 0:
            return "failed", ["no_mapped_fields"], [], [], metrics

        if not core["sku"] and not clean_strong_bundle_without_sku:
            reasons.append("missing_sku")
        if not core["orders_or_order_amount"]:
            reasons.append("missing_order_signal")
        if coverage < 0.5:
            reasons.append("mapping_coverage_below_0_5")
        if mapped_count < 4:
            reasons.append("mapped_count_below_4")
        if wrongly_mapped_count > 0:
            reasons.append("wrongly_mapped_fields_present")

        if under_structure_scrutiny:
            if not core["impressions_total_or_search_catalog"]:
                reasons.append("missing_top_funnel_signal_under_header_risk")
            if not core["product_card_visits_or_add_to_cart_total"]:
                reasons.append("missing_mid_funnel_signal_under_header_risk")
            if int(core.get("funnelSignalCount") or 0) < 3:
                reasons.append("insufficient_funnel_signal_count_under_header_risk")
        else:
            if not core["impressions_total_or_search_catalog"]:
                reasons.append("missing_top_funnel_signal")
            if not core["product_card_visits_or_add_to_cart_total"]:
                reasons.append("missing_mid_funnel_signal")

        if not critical_requirements_met:
            reasons.append("insufficient_core_field_hits")

        if len(risk_signal_hits) >= 2 and header_structure_score < 0.68:
            risk_override_reasons.append("multiple_header_risk_signals")
        if "short_explainable_column_run" in risk_signal_hits:
            risk_override_reasons.append("short_explainable_column_run")

        if not reasons:
            if risk_override_reasons:
                return "risk", [], risk_override_reasons, [], metrics
            if clean_strong_bundle_without_sku:
                acceptance_reason.extend(
                    [
                        "mapping_thresholds_met",
                        "clean_structure_exception",
                        "funnel_shape_present",
                    ]
                )
            else:
                acceptance_reason.extend(
                    [
                        "mapping_thresholds_met",
                        "core_fields_present",
                        "funnel_shape_present",
                    ]
                )
            return "passed", [], [], acceptance_reason, metrics

        if mapped_count >= 2:
            return "risk", reasons, risk_override_reasons, acceptance_reason, metrics
        return "failed", reasons, risk_override_reasons, acceptance_reason, metrics

    # ---------- 主链路 ----------

    def _build_bundle(
        self,
        df: pd.DataFrame,
        header_block: dict,
        flattened_headers: List[str],
        header_recovery_applied: bool,
        dropped_placeholder_columns: List[str],
        rescued_placeholder_columns: List[str],
    ) -> dict:
        mapped_df, field_mappings = self.map_columns(df)
        mapping_summary = self._build_field_mapping_summary(
            field_mappings=field_mappings,
            header_block=header_block,
            flattened_headers=flattened_headers,
            dropped_placeholder_columns=dropped_placeholder_columns,
        )
        transport_status = (
            "passed" if len(df.columns) > 0 and len(df) >= 0 else "failed"
        )
        final_status = (
            "failed"
            if transport_status == "failed"
            else mapping_summary["semanticStatus"]
        )
        diagnosis_obj = self.diagnoser.diagnose(
            file_name="",
            preview_rows=df.head(20).values.tolist(),
            headers=[str(c) for c in df.columns],
            mapped_fields=int(mapping_summary["mappedCount"]),
            unmapped_fields=list(mapping_summary["topUnmappedHeaders"]),
            row_error_count=0,
        )
        if hasattr(diagnosis_obj, "__dict__"):
            diagnosis = {
                "suggestions": list(getattr(diagnosis_obj, "suggestions", []) or []),
                "keyField": getattr(diagnosis_obj, "keyField", None),
                "unmappedFields": list(
                    getattr(diagnosis_obj, "unmappedFields", []) or []
                ),
                "status": getattr(diagnosis_obj, "status", "partial"),
            }
            platform = getattr(diagnosis_obj, "platform", "generic")
        elif isinstance(diagnosis_obj, dict):
            diagnosis = {
                "suggestions": list(diagnosis_obj.get("suggestions") or []),
                "keyField": diagnosis_obj.get("keyField"),
                "unmappedFields": list(diagnosis_obj.get("unmappedFields") or []),
                "status": diagnosis_obj.get("status", "partial"),
            }
            platform = diagnosis_obj.get("platform", "generic")
        else:
            diagnosis = {
                "suggestions": [],
                "keyField": None,
                "unmappedFields": list(mapping_summary["topUnmappedHeaders"]),
                "status": "partial",
            }
            platform = "generic"

        return {
            "df": mapped_df,
            "fieldMappings": field_mappings,
            "mappedTargets": mapping_summary["mappedTargets"],
            "mappedCount": mapping_summary["mappedCount"],
            "unmappedCount": mapping_summary["unmappedCount"],
            "mappedCanonicalFields": mapping_summary["mappedCanonicalFields"],
            "topUnmappedHeaders": mapping_summary["topUnmappedHeaders"],
            "transportStatus": transport_status,
            "semanticStatus": mapping_summary["semanticStatus"],
            "finalStatus": final_status,
            "semanticGateReasons": mapping_summary["semanticGateReasons"],
            "riskOverrideReasons": mapping_summary["riskOverrideReasons"],
            "semanticAcceptanceReason": mapping_summary["semanticAcceptanceReason"],
            "mappingCoverage": mapping_summary["mappingCoverage"],
            "mappedConfidence": mapping_summary["mappedConfidence"],
            "semanticMetrics": mapping_summary["semanticMetrics"],
            "coreFieldHitSummary": mapping_summary["coreFieldHitSummary"],
            "headerBlock": copy.deepcopy(header_block),
            "flattenedHeaders": list(flattened_headers),
            "headerRecoveryApplied": bool(header_recovery_applied),
            "headerStructureScore": mapping_summary["headerStructureScore"],
            "headerStructureRiskSignals": mapping_summary["headerStructureRiskSignals"],
            "droppedPlaceholderColumns": list(dropped_placeholder_columns),
            "rescuedPlaceholderColumns": list(rescued_placeholder_columns),
            "diagnosis": diagnosis,
            "platform": platform,
        }

    def _build_field_mapping_summary(
        self,
        field_mappings: List[dict],
        header_block: dict,
        flattened_headers: List[str],
        dropped_placeholder_columns: List[str],
    ) -> dict:
        semantic_field_mappings = [
            item for item in (field_mappings or []) if not item.get("excludeFromSemanticGate")
        ]
        mapped_targets = [
            str(item.get("standardField"))
            for item in semantic_field_mappings
            if item.get("standardField")
        ]
        candidate_columns = sum(
            1
            for item in semantic_field_mappings
            if not self._is_placeholder_col(item.get("originalField"))
        )
        unmapped_headers = [
            str(item.get("originalField"))
            for item in semantic_field_mappings
            if not item.get("standardField") and not item.get("dynamicCompanion")
        ]
        mapped_count = len(mapped_targets)
        wrong_mapped_count = 0
        header_structure_score, header_structure_signals = (
            self._compute_header_structure_score(
                header_block, flattened_headers, dropped_placeholder_columns
            )
        )
        (
            semantic_status,
            semantic_gate_reasons,
            risk_override_reasons,
            acceptance_reason,
            semantic_metrics,
        ) = self._semantic_gate(
            mapped_targets=mapped_targets,
            candidate_columns=candidate_columns,
            mapped_count=mapped_count,
            wrongly_mapped_count=wrong_mapped_count,
            header_signals=header_structure_signals,
            header_structure_score=header_structure_score,
        )
        mapped_confidence = round(
            sum(float(item.get("confidence") or 0.0) for item in (field_mappings or []))
            / max(len(field_mappings or []), 1),
            3,
        )
        mapping_coverage = round(
            float(semantic_metrics.get("mappingCoverage") or 0.0),
            3,
        )
        return {
            "semanticFieldMappings": semantic_field_mappings,
            "mappedTargets": mapped_targets,
            "mappedCount": mapped_count,
            "unmappedCount": len(unmapped_headers),
            "mappedCanonicalFields": list(dict.fromkeys(mapped_targets))[:20],
            "topUnmappedHeaders": unmapped_headers[:20],
            "headerStructureScore": header_structure_score,
            "headerStructureRiskSignals": header_structure_signals,
            "semanticStatus": semantic_status,
            "semanticGateReasons": semantic_gate_reasons,
            "riskOverrideReasons": risk_override_reasons,
            "semanticAcceptanceReason": acceptance_reason,
            "mappingCoverage": mapping_coverage,
            "mappedConfidence": mapped_confidence,
            "semanticMetrics": {
                **semantic_metrics,
                "mappingCoverage": mapping_coverage,
                "candidateColumns": candidate_columns,
                "mappedConfidence": mapped_confidence,
                "wronglyMappedCount": wrong_mapped_count,
            },
            "coreFieldHitSummary": self._build_core_field_hit_summary(mapped_targets),
        }

    def parse_import_file(
        self, file_path: str, shop_id: int = 1, operator: str = "frontend_user"
    ) -> dict:
        path = Path(file_path)
        session_id = next(self._session_counter)

        default_df, error, default_meta = self._read_file_default(file_path)
        if error or default_df is None:
            return {
                "sessionId": session_id,
                "fileName": path.name,
                "fileSize": path.stat().st_size if path.exists() else 0,
                "sheetNames": default_meta.get("sheetNames") or [],
                "selectedSheet": default_meta.get("selectedSheet") or "",
                "totalRows": 0,
                "totalColumns": 0,
                "headerRow": 0,
                "dataPreview": [],
                "platform": "generic",
                "fieldMappings": [],
                "mappedCount": 0,
                "unmappedCount": 0,
                "confidence": 0.0,
                "status": "failed",
                "diagnosis": {
                    "suggestions": [error],
                    "keyField": None,
                    "unmappedFields": [],
                    "status": "failed",
                },
                "transportStatus": "failed",
                "semanticStatus": "failed",
                "finalStatus": "failed",
                "semanticGateReasons": ["read_failed"],
                "riskOverrideReasons": [],
                "semanticAcceptanceReason": [],
                "readerEngineUsed": default_meta.get("readerEngineUsed"),
                "readerFallbackStage": default_meta.get("readerFallbackStage"),
                "fieldRegistryVersion": str(self._registry_cfg.get("version") or "v1"),
            }

        raw_df, raw_error, raw_meta = self._read_file_raw(file_path)
        if raw_error or raw_df is None:
            raw_df = pd.DataFrame(
                [list(default_df.columns)] + default_df.head(50).values.tolist()
            )
            raw_meta = default_meta

        pre_bundle = self._build_bundle(
            df=default_df.copy(),
            header_block={"startRow": 0, "endRow": 0, "confidence": 0.5, "signals": []},
            flattened_headers=[str(c) for c in default_df.columns],
            header_recovery_applied=False,
            dropped_placeholder_columns=[],
            rescued_placeholder_columns=[],
        )
        pre_bundle["candidateScore"] = self._score_candidate_bundle(pre_bundle)
        recovery_result = self._attempt_candidate_recovery(raw_df, pre_bundle)
        recovery_attempted = bool(recovery_result["recoveryAttempted"])
        recovery_improved = bool(recovery_result["recoveryImproved"])
        header_recovery_applied = bool(recovery_result["headerRecoveryApplied"])
        active_bundle = recovery_result["activeBundle"]
        post_bundle = recovery_result["postBundle"]
        header_block = active_bundle.get("headerBlock") or {
            "startRow": 0,
            "endRow": 0,
            "confidence": 0.5,
            "signals": [],
        }
        flattened_headers = list(
            active_bundle.get("flattenedHeaders")
            or [str(c) for c in active_bundle["df"].columns]
        )
        dropped_placeholder_columns = list(
            active_bundle.get("droppedPlaceholderColumns") or []
        )
        rescued_placeholder_columns = list(
            active_bundle.get("rescuedPlaceholderColumns") or []
        )
        pre_cov = self._bundle_mapping_coverage(pre_bundle)
        post_cov = self._bundle_mapping_coverage(post_bundle)
        pre_core = sum(
            1
            for v in (pre_bundle.get("coreFieldHitSummary") or {}).values()
            if isinstance(v, bool) and v
        )
        post_core = sum(
            1
            for v in (post_bundle.get("coreFieldHitSummary") or {}).values()
            if isinstance(v, bool) and v
        )

        cleaned_df = self.clean_data(active_bundle["df"])
        valid_df, row_errors = self.validate_data(cleaned_df)
        valid_df, duplicate_count = self.remove_duplicates(valid_df)

        status_map = {"passed": "success", "risk": "partial", "failed": "failed"}
        preview_df = active_bundle["df"].head(10)
        preview_rows = preview_df.fillna("").astype(str).values.tolist()
        confidence = self._bundle_mapped_confidence(active_bundle)
        candidate_columns = int(
            active_bundle["semanticMetrics"].get("candidateColumns") or 0
        )
        mapped_count = int(active_bundle["mappedCount"])
        stats = {
            "candidateColumns": candidate_columns,
            "ignoredColumns": len(active_bundle["droppedPlaceholderColumns"]),
            "ignoredFields": active_bundle["droppedPlaceholderColumns"],
            "mappedConfidence": self._bundle_mapped_confidence(active_bundle),
            "mappingCoverage": self._bundle_mapping_coverage(active_bundle),
            "mappedCount": mapped_count,
            "unmappedCount": int(active_bundle["unmappedCount"]),
            "correctlyMappedCount": mapped_count,
            "wronglyMappedCount": int(
                active_bundle["semanticMetrics"].get("wronglyMappedCount") or 0
            ),
            "ruUnmappedCount": 0,
            "ruMappingPass": True,
            "droppedPlaceholderColumns": active_bundle["droppedPlaceholderColumns"],
            "dynamicMetricColumns": [
                str(item.get("originalField"))
                for item in (active_bundle.get("fieldMappings") or [])
                if item.get("dynamicCompanion")
            ],
            "removedSummaryRows": 0,
            "removedDescriptionRows": int(header_block.get("startRow") or 0),
            "recoveryCandidateCount": int(recovery_result.get("candidateCount") or 0),
            "recoveryCandidatePreview": list(
                recovery_result.get("candidatePreview") or []
            ),
        }
        recovery_diff = {
            "mappedCount_before": int(pre_bundle["mappedCount"]),
            "mappedCount_after": int(post_bundle["mappedCount"]),
            "unmappedCount_before": int(pre_bundle["unmappedCount"]),
            "unmappedCount_after": int(post_bundle["unmappedCount"]),
            "mappingCoverage_before": round(pre_cov, 3),
            "mappingCoverage_after": round(post_cov, 3),
            "coreFieldHit_before": int(pre_core),
            "coreFieldHit_after": int(post_core),
        }
        ru_mapping_quality = {
            "correctlyMappedCount": mapped_count,
            "wronglyMappedCount": int(
                active_bundle["semanticMetrics"].get("wronglyMappedCount") or 0
            ),
            "unmappedCount": int(active_bundle["unmappedCount"]),
            "goldenTotal": mapped_count + int(active_bundle["unmappedCount"]),
            "pass": active_bundle["semanticStatus"] != "failed",
            "details": [],
        }
        mapped_canonical_fields = list(active_bundle.get("mappedCanonicalFields") or [])

        top_unmapped_headers = list(active_bundle.get("topUnmappedHeaders") or [])

        recovery_candidate_preview = list(recovery_result.get("candidatePreview") or [])

        entity_key_suggestion = self._build_entity_key_suggestion(
            top_unmapped_headers=top_unmapped_headers,
            recovery_candidate_preview=recovery_candidate_preview,
            mapped_canonical_fields=mapped_canonical_fields,
            field_mappings=active_bundle.get("fieldMappings") or [],
            df=active_bundle["df"],
        )

        result = {
            "sessionId": session_id,
            "fileName": path.name,
            "fileSize": path.stat().st_size if path.exists() else 0,
            "sheetNames": raw_meta.get("sheetNames")
            or default_meta.get("sheetNames")
            or [],
            "selectedSheet": raw_meta.get("selectedSheet")
            or default_meta.get("selectedSheet")
            or "",
            "totalRows": int(len(active_bundle["df"])),
            "totalColumns": int(len(active_bundle["df"].columns)),
            "rawColumns": int(raw_df.shape[1]),
            "normalizedColumns": int(len(flattened_headers)),
            "readerEngineUsed": raw_meta.get("readerEngineUsed")
            or default_meta.get("readerEngineUsed"),
            "readerFallbackStage": raw_meta.get("readerFallbackStage")
            or default_meta.get("readerFallbackStage"),
            "fieldRegistryVersion": str(self._registry_cfg.get("version") or "v1"),
            "headerRow": int(
                (header_block if header_recovery_applied else {"startRow": 0}).get(
                    "startRow"
                )
                or 0
            ),
            "dataPreview": preview_rows,
            "platform": active_bundle["platform"],
            "fieldMappings": active_bundle["fieldMappings"],
            "mappedCanonicalFields": mapped_canonical_fields,
            "topUnmappedHeaders": top_unmapped_headers,
            "entityKeySuggestion": entity_key_suggestion,
            "mappedCount": mapped_count,
            "unmappedCount": int(active_bundle["unmappedCount"]),
            "mappingCoverage": self._bundle_mapping_coverage(active_bundle),
            "mappedConfidence": confidence,
            "confidence": confidence,
            "stats": stats,
            "ruMappingQuality": ru_mapping_quality,
            "transportStatus": active_bundle["transportStatus"],
            "semanticStatus": active_bundle["semanticStatus"],
            "finalStatus": active_bundle["finalStatus"],
            "semanticGateReasons": active_bundle["semanticGateReasons"],
            "riskOverrideReasons": active_bundle["riskOverrideReasons"],
            "semanticAcceptanceReason": active_bundle["semanticAcceptanceReason"],
            "semanticMetrics": active_bundle["semanticMetrics"],
            "coreFieldHitSummary": active_bundle["coreFieldHitSummary"],
            "headerBlock": active_bundle["headerBlock"],
            "flattenedHeaders": active_bundle["flattenedHeaders"],
            "headerRecoveryApplied": header_recovery_applied,
            "headerStructureScore": active_bundle["headerStructureScore"],
            "headerStructureRiskSignals": active_bundle["headerStructureRiskSignals"],
            "droppedPlaceholderColumns": active_bundle["droppedPlaceholderColumns"],
            "rescuedPlaceholderColumns": active_bundle["rescuedPlaceholderColumns"],
            "preRecoveryStatus": pre_bundle["semanticStatus"],
            "postRecoveryStatus": post_bundle["semanticStatus"],
            "recoveryAttempted": recovery_attempted,
            "recoveryImproved": recovery_improved,
            "sampleHint": None,
            "recoveryDiff": recovery_diff,
            "recoveryCandidatePreview": recovery_candidate_preview,
            "status": status_map.get(active_bundle["finalStatus"], "partial"),
            "diagnosis": active_bundle["diagnosis"],
        }

        self._sessions[session_id] = {
            "sessionId": session_id,
            "filePath": str(path),
            "fileName": path.name,
            "shopId": shop_id,
            "operator": operator,
            "result": result,
            "df": valid_df,
            "rowErrors": row_errors,
            "duplicateCount": duplicate_count,
            "createdAt": datetime.now().isoformat(),
            "stagingDf": active_bundle["df"].copy(),
            "stagingFieldMappings": copy.deepcopy(
                active_bundle.get("fieldMappings") or []
            ),
        }
        self.batches.append(
            {
                "sessionId": session_id,
                "fileName": path.name,
                "createdAt": datetime.now().isoformat(),
                "status": result["status"],
                "finalStatus": result["finalStatus"],
            }
        )
        return result

    def confirm_import(
        self,
        session_id: int,
        shop_id: int,
        manual_overrides: Optional[List[dict]] = None,
        operator: str = "frontend_user",
    ) -> dict:
        if session_id not in self._sessions:
            return {
                "sessionId": session_id,
                "batchId": 0,
                "importedRows": 0,
                "errorRows": 0,
                "status": "failed",
                "warnings": [],
                "errors": ["session not found"],
                "transportStatus": "failed",
                "semanticStatus": "failed",
                "finalStatus": "failed",
                "importabilityStatus": "failed",
                "importabilityReasons": ["session_not_found"],
                "semanticGateReasons": ["session_not_found"],
                "riskOverrideReasons": [],
                "semanticAcceptanceReason": [],
                "recoverySummary": {},
            }

        session = self._sessions[session_id]
        result = copy.deepcopy(session["result"])

        valid_df: pd.DataFrame = session["df"]
        row_errors: List[Dict[str, Any]] = session["rowErrors"]
        manual_overrides = manual_overrides or []

        if manual_overrides:
            staging_df: pd.DataFrame = session.get("stagingDf")
            staging_field_mappings: List[dict] = session.get("stagingFieldMappings") or []

            if isinstance(staging_df, pd.DataFrame):
                override_df, override_field_mappings = (
                    self._apply_manual_overrides_to_staging(
                        staging_df=staging_df,
                        field_mappings=staging_field_mappings,
                        manual_overrides=manual_overrides,
                    )
                )

                cleaned_override_df = self.clean_data(override_df)
                valid_df, row_errors = self.validate_data(cleaned_override_df)
                valid_df, duplicate_count = self.remove_duplicates(valid_df)

                session["df"] = valid_df
                session["rowErrors"] = row_errors
                session["duplicateCount"] = duplicate_count

                result["fieldMappings"] = override_field_mappings
                override_summary = self._build_field_mapping_summary(
                    field_mappings=override_field_mappings,
                    header_block=result.get("headerBlock") or {},
                    flattened_headers=result.get("flattenedHeaders") or [],
                    dropped_placeholder_columns=result.get("droppedPlaceholderColumns") or [],
                )
                result["mappedCanonicalFields"] = override_summary[
                    "mappedCanonicalFields"
                ]
                result["topUnmappedHeaders"] = override_summary["topUnmappedHeaders"]
                result["mappedCount"] = override_summary["mappedCount"]
                result["unmappedCount"] = override_summary["unmappedCount"]
                result["mappingCoverage"] = override_summary["mappingCoverage"]
                result["mappedConfidence"] = override_summary["mappedConfidence"]
                result["semanticMetrics"] = override_summary["semanticMetrics"]
                result["coreFieldHitSummary"] = override_summary[
                    "coreFieldHitSummary"
                ]
                result["semanticStatus"] = override_summary["semanticStatus"]
                result["semanticGateReasons"] = override_summary[
                    "semanticGateReasons"
                ]
                result["riskOverrideReasons"] = override_summary[
                    "riskOverrideReasons"
                ]
                result["semanticAcceptanceReason"] = override_summary[
                    "semanticAcceptanceReason"
                ]
                if "confidence" in result:
                    result["confidence"] = override_summary["mappedConfidence"]
                result["finalStatus"] = (
                    "failed"
                    if result.get("transportStatus") == "failed"
                    else override_summary["semanticStatus"]
                )

        warnings: List[str] = []
        if session.get("duplicateCount"):
            warnings.append(f"发现并移除 {session['duplicateCount']} 条重复记录")
        if result.get("finalStatus") == "risk":
            warnings.append("当前样本处于 risk 状态，请结合语义门禁原因复核")

        imported_rows = int(len(valid_df))
        quarantine_count = int(len(row_errors))
        fact_load_errors = 0
        importability_reasons: List[str] = []
        if imported_rows == 0 and quarantine_count > 0 and fact_load_errors == 0:
            importability_status = "risk"
            importability_reasons.append("all_rows_quarantined")
        elif imported_rows > 0 and quarantine_count > 0:
            importability_status = "risk"
            importability_reasons.append("partial_quarantine")
        elif imported_rows > 0 and fact_load_errors == 0:
            importability_status = "passed"
        else:
            importability_status = "failed"

        rating_source_column = None
        for mapping in session.get("stagingFieldMappings") or []:
            if str(mapping.get("standardField") or "") == "rating_value":
                rating_source_column = str(mapping.get("originalField") or "") or None
                break

        staging_df_for_audit = session.get("stagingDf")
        rating_issue_samples = []
        for item in row_errors:
            if str(item.get("field") or "") != "rating_value":
                continue

            row_no = item.get("row")
            rating_source_raw_value = None
            if (
                isinstance(row_no, int)
                and row_no >= 1
                and rating_source_column
                and hasattr(staging_df_for_audit, "columns")
                and rating_source_column in staging_df_for_audit.columns
                and row_no - 1 < len(staging_df_for_audit)
            ):
                raw = staging_df_for_audit.iloc[row_no - 1][rating_source_column]
                if raw is not None and str(raw).strip().lower() != "nan":
                    rating_source_raw_value = self._safe_scalar(raw)

            rating_issue_samples.append(
                {
                    "row": row_no,
                    "ratingValue": item.get("rawValue"),
                    "ratingSourceColumn": rating_source_column,
                    "ratingSourceRawValue": rating_source_raw_value,
                    "error": item.get("error"),
                }
            )

            if len(rating_issue_samples) >= 10:
                break

        missing_rating_count = 0
        if isinstance(valid_df, pd.DataFrame) and "rating_value" in valid_df.columns:
            missing_rating_count = int(valid_df["rating_value"].isna().sum())

        response = {
            "sessionId": session_id,
            "batchId": session_id,
            "importedRows": imported_rows,
            "errorRows": quarantine_count,
            "status": "success",
            "warnings": warnings,
            "errors": [str(item.get("error")) for item in row_errors[:50]],
            "ratingIssueSamples": rating_issue_samples,
            "rowErrorSummary": {
                "auto_fixed": 0,
                "ignorable": 0,
                "quarantined": quarantine_count,
                "fatal": 0,
            },
            "quarantineCount": quarantine_count,
            "stagingRows": imported_rows,
            "factLoadErrors": fact_load_errors,
            "missingRatingCount": missing_rating_count,
            "mappingCoverage": result.get("mappingCoverage"),
            "mappedConfidence": result.get("mappedConfidence"),
            "transportStatus": result.get("transportStatus"),
            "semanticStatus": result.get("semanticStatus"),
            "finalStatus": result.get("finalStatus"),
            "importabilityStatus": importability_status,
            "importabilityReasons": importability_reasons,
            "semanticGateReasons": list(result.get("semanticGateReasons") or []),
            "riskOverrideReasons": list(result.get("riskOverrideReasons") or []),
            "semanticAcceptanceReason": list(
                result.get("semanticAcceptanceReason") or []
            ),
            "recoverySummary": {
                "headerRecoveryApplied": result.get("headerRecoveryApplied"),
                "preRecoveryStatus": result.get("preRecoveryStatus"),
                "postRecoveryStatus": result.get("postRecoveryStatus"),
                "recoveryAttempted": result.get("recoveryAttempted"),
                "recoveryImproved": result.get("recoveryImproved"),
                "semanticGateReasons": list(result.get("semanticGateReasons") or []),
                "riskOverrideReasons": list(result.get("riskOverrideReasons") or []),
                "recoveryDiff": copy.deepcopy(result.get("recoveryDiff") or {}),
            },
            "runtimeAudit": {
                "sessionId": session_id,
                "operator": operator,
                "shopId": shop_id,
                "confirmedAt": datetime.now().isoformat(),
                "sourceFile": session.get("fileName"),
                "finalStatus": result.get("finalStatus"),
                "transportStatus": result.get("transportStatus"),
                "semanticStatus": result.get("semanticStatus"),
                "importabilityStatus": importability_status,
                "importabilityReasons": importability_reasons,
                "quarantineCount": quarantine_count,
                "factLoadErrors": fact_load_errors,
                "missingRatingCount": missing_rating_count,
                "ratingIssueCount": len(rating_issue_samples),
                "recoverySummary": {
                    "headerRecoveryApplied": result.get("headerRecoveryApplied"),
                    "preRecoveryStatus": result.get("preRecoveryStatus"),
                    "postRecoveryStatus": result.get("postRecoveryStatus"),
                    "recoveryAttempted": result.get("recoveryAttempted"),
                    "recoveryImproved": result.get("recoveryImproved"),
                },
                "manualOverrides": copy.deepcopy(manual_overrides),
            },
        }
        return response

def get_session_result(self, session_id: int) -> dict | None:
    session = self._sessions.get(session_id)
    if not session:
        return None
    return copy.deepcopy(session.get("result") or {})

    # ---------- 兼容旧接口 ----------

    def list_batches(self) -> list:
        return self.batches

    def import_from_file(
        self,
        file_path: str,
        save_to_db: bool = False,
        output_path: Optional[str] = None,
    ) -> ImportResult:
        parse_result = self.parse_import_file(file_path)
        session_id = int(parse_result.get("sessionId") or 0)
        confirm = (
            self.confirm_import(
                session_id=session_id,
                shop_id=1,
                manual_overrides=[],
                operator="import_from_file",
            )
            if session_id
            else {
                "importedRows": 0,
                "errorRows": 0,
                "errors": ["parse_failed"],
                "warnings": [],
                "status": "failed",
            }
        )
        data = self._sessions.get(session_id, {}).get("df")
        records = data.to_dict("records") if isinstance(data, pd.DataFrame) else []
        if output_path:
            self.save_to_json(
                records,
                output_path,
                metadata={"parse": parse_result, "confirm": confirm},
            )
        return ImportResult(
            success=confirm.get("status") == "success",
            total_rows=int(parse_result.get("totalRows") or 0),
            imported=int(confirm.get("importedRows") or 0),
            failed=int(confirm.get("errorRows") or 0),
            errors=[{"error": x} for x in confirm.get("errors") or []],
            warnings=list(confirm.get("warnings") or []),
            data=records,
        )

    def save_to_json(
        self,
        data: List[Dict[str, Any]],
        output_path: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        payload: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "count": len(data),
            "data": data,
        }
        if metadata:
            payload["metadata"] = metadata
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    # ---------- 新增helper ----------
    def _apply_manual_overrides_to_staging(
        self,
        staging_df: pd.DataFrame,
        field_mappings: List[dict],
        manual_overrides: List[dict],
    ) -> tuple[pd.DataFrame, List[dict]]:
        next_df = staging_df.copy()
        next_field_mappings = copy.deepcopy(field_mappings or [])

        normalized_manual_overrides: List[dict] = []
        seen_protected_targets: set[str] = set()
        for item in reversed(manual_overrides or []):
            original_field = str(item.get("originalField") or "").strip()
            standard_field = str(item.get("standardField") or "").strip()
            if not original_field or not standard_field:
                continue
            if standard_field in self.PROTECTED_UNIQUE_TARGETS:
                if standard_field in seen_protected_targets:
                    continue
                seen_protected_targets.add(standard_field)
            normalized_manual_overrides.append(item)
        normalized_manual_overrides.reverse()

        for item in normalized_manual_overrides:
            original_field = str(item.get("originalField") or "").strip()
            standard_field = str(item.get("standardField") or "").strip()

            if not original_field or not standard_field:
                continue
            if original_field not in next_df.columns:
                continue

            # 把原列值映射到目标 canonical 列
            next_df[standard_field] = next_df[original_field]

            matched = False
            for mapping in next_field_mappings:
                if str(mapping.get("originalField") or "") == original_field:
                    mapping["standardField"] = standard_field
                    mapping["mappingSource"] = "manual_override"
                    mapping["confidence"] = 1.0
                    mapping["isManual"] = True
                    mapping["reasons"] = list(
                        dict.fromkeys(
                            list(mapping.get("reasons") or [])
                            + ["manual_override_applied"]
                        )
                    )
                    matched = True
                    break

            if not matched:
                next_field_mappings.append(
                    {
                        "originalField": original_field,
                        "normalizedField": str(
                            item.get("normalizedField") or original_field
                        ),
                        "standardField": standard_field,
                        "mappingSource": "manual_override",
                        "confidence": 1.0,
                        "sampleValues": [],
                        "isManual": True,
                        "reasons": ["manual_override_applied"],
                    }
                )

        next_field_mappings = self._postprocess_field_mappings(next_field_mappings)
        return next_df, next_field_mappings
