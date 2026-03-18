
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(r"C:\Operation-system\System")
TARGET = REPO_ROOT / "src" / "ecom_v51" / "services" / "import_service.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[{label}] expected 1 match, got {count}")
    return text.replace(old, new, 1)


OLD_CONSTANTS = """    DYNAMIC_PATTERNS = [
        "динамик",
        "изменени",
        "change",
        "delta",
        "trend",
        "рост",
        "снижение",
    ]
    GENERIC_HEADER_PIECES = {
"""
NEW_CONSTANTS = """    DYNAMIC_PATTERNS = [
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
        "рекомендац",
        "сколько товаров",
        "среднее время доставки",
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
"""

OLD_RU_RULES = """    RU_PHRASE_CANONICAL_RULES = [
        (["артикул"], "sku"),
        (["seller sku"], "sku"),
        (["offer id"], "sku"),
        (["показы в поиске", "каталоге"], "impressions_search_catalog"),
        (["показы", "всего"], "impressions_total"),
        (["показы"], "impressions_total"),
        (["посещ", "карточк"], "product_card_visits"),
        (["переход", "карточк"], "product_card_visits"),
        (["добав", "корзин"], "add_to_cart_total"),
        (["заказано на сумму"], "order_amount"),
        (["сумма заказ"], "order_amount"),
        (["заказ"], "orders"),
        (["остат", "склад"], "stock_total"),
        (["в наличии"], "stock_total"),
        (["рейтинг"], "rating_value"),
        (["отзыв"], "review_count"),
        (["индекс цен"], "price_index_status"),
        (["средняя позиция", "поиск"], "search_catalog_position_avg"),
    ]
"""
NEW_RU_RULES = """    RU_PHRASE_CANONICAL_RULES = [
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
"""

OLD_PREVIEW = """    def _preview_values_for_column(
        self, df: pd.DataFrame, col: Any, limit: int = 3
    ) -> List[Any]:
        if col not in df.columns:
            return []
        selected = df.loc[:, col]
        values: List[Any] = []

        if isinstance(selected, pd.DataFrame):
            for row in selected.head(limit).itertuples(index=False, name=None):
                for item in row if isinstance(row, tuple) else (row,):
                    values.append(self._safe_scalar(item))
                    if len(values) >= limit:
                        return values[:limit]
            return values[:limit]

        try:
            raw_values = selected.head(limit).tolist()
        except Exception:
            raw_values = (
                selected.head(limit).values.tolist()
                if hasattr(selected.head(limit), "values")
                else []
            )
        for item in raw_values:
            if isinstance(item, list):
                for nested in item:
                    values.append(self._safe_scalar(nested))
                    if len(values) >= limit:
                        return values[:limit]
            else:
                values.append(self._safe_scalar(item))
                if len(values) >= limit:
                    return values[:limit]
        return values[:limit]
"""
NEW_PREVIEW = """    def _preview_values_for_column(
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
"""

OLD_HELPER_START = """    def _is_dynamic_companion(self, text: str) -> bool:
        normalized = self._normalize_header(text)
        return any(token in normalized for token in self.DYNAMIC_PATTERNS)

    def _compress_header_phrase(self, original: Any) -> List[Tuple[str, str]]:
"""
NEW_HELPER_START = """    def _is_dynamic_companion(self, text: str) -> bool:
        normalized = self._normalize_header(text)
        return any(token in normalized for token in self.DYNAMIC_PATTERNS)

    def _is_soft_excluded_header(self, text: str) -> bool:
        normalized = self._normalize_header(text)
        return any(token in normalized for token in self.SOFT_EXCLUDE_PATTERNS)

    def _looks_like_explainer_text(self, text: str) -> bool:
        raw = str(text or "").strip().lower()
        if not raw:
            return False
        return (
            len(raw) >= 40
            or "оцениваем" in raw
            or "считаем" in raw
            or "для этого" in raw
            or "динамика по сравнению" in raw
            or "товары a приносят" in raw
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
"""

OLD_COMPRESS_SNIP = """        candidates: List[Tuple[str, str]] = []
        seen: set[str] = set()

        def push(value: str, reason: str) -> None:
"""
NEW_COMPRESS_SNIP = """        candidates: List[Tuple[str, str]] = []
        seen: set[str] = set()
        soft_excluded = self._is_soft_excluded_header(text)

        def push(value: str, reason: str) -> None:
"""

OLD_COMPRESS_RULES = """        for needles, canonical in self.RU_PHRASE_CANONICAL_RULES:
            if all(needle in normalized_wo_unit for needle in needles):
                push(canonical, f"phrase_rule:{canonical}")
"""
NEW_COMPRESS_RULES = """        if not soft_excluded:
            for needles, canonical in self.RU_PHRASE_CANONICAL_RULES:
                if all(needle in normalized_wo_unit for needle in needles):
                    push(canonical, f"phrase_rule:{canonical}")
"""

OLD_COMPRESS_MEANINGFUL = """        if meaningful:
            push(" ".join(dict.fromkeys(meaningful)), "token_compaction")
"""
NEW_COMPRESS_MEANINGFUL = """        if meaningful and not soft_excluded:
            push(" ".join(dict.fromkeys(meaningful)), "token_compaction")
"""

OLD_DETAILS_START = """        compressed = self._compress_header_phrase(original)
        dynamic_companion = self._is_dynamic_companion(original)
        reasons: List[str] = []
"""
NEW_DETAILS_START = """        compressed = self._compress_header_phrase(original)
        dynamic_companion = self._is_dynamic_companion(original)
        soft_excluded = self._is_soft_excluded_header(original)
        reasons: List[str] = []
"""

OLD_DETAILS_DYNAMIC = """        def score_candidate(
"""
NEW_DETAILS_DYNAMIC = """        if dynamic_companion:
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
"""

OLD_MAP_COLUMNS = """    def map_columns(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[dict]]:
        rename_map: Dict[str, str] = {}
        field_mappings: List[dict] = []

        for col in df.columns:
            sample_values = self._preview_values_for_column(df, col, limit=3)
            details = self._map_single_column_details(col, sample_values=sample_values)
            field_mappings.append(details)
            canonical = details.get("standardField")
            if canonical:
                rename_map[str(col)] = canonical

        mapped_df = df.rename(columns=rename_map)
        mapped_df = self._collapse_duplicate_columns(mapped_df)
        return mapped_df, field_mappings
"""
NEW_MAP_COLUMNS = """    def map_columns(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[dict]]:
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
"""


def main() -> None:
    if not TARGET.exists():
        raise FileNotFoundError(f"missing file: {TARGET}")

    text = TARGET.read_text(encoding="utf-8")
    backup = TARGET.with_suffix(".py.bak_mapping_accuracy_safe_v1")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")

    text = replace_once(text, OLD_CONSTANTS, NEW_CONSTANTS, "constants")
    text = replace_once(text, OLD_RU_RULES, NEW_RU_RULES, "ru rules")
    text = replace_once(text, OLD_PREVIEW, NEW_PREVIEW, "preview values")
    text = replace_once(text, OLD_HELPER_START, NEW_HELPER_START, "insert helpers")
    text = replace_once(text, OLD_COMPRESS_SNIP, NEW_COMPRESS_SNIP, "compress soft exclude flag")
    text = replace_once(text, OLD_COMPRESS_RULES, NEW_COMPRESS_RULES, "compress rules gate")
    text = replace_once(text, OLD_COMPRESS_MEANINGFUL, NEW_COMPRESS_MEANINGFUL, "compress token gate")
    text = replace_once(text, OLD_DETAILS_START, NEW_DETAILS_START, "details soft exclude flag")
    text = replace_once(text, OLD_DETAILS_DYNAMIC, NEW_DETAILS_DYNAMIC, "details early returns")
    text = replace_once(text, OLD_MAP_COLUMNS, NEW_MAP_COLUMNS, "map columns postprocess")

    TARGET.write_text(text, encoding="utf-8")
    print("Applied mapping accuracy safe patch v1")
    print(f"Patched: {TARGET}")
    print(f"Backup:  {backup}")


if __name__ == "__main__":
    main()
