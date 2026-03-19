from __future__ import annotations

import re
from pathlib import Path


TARGET = Path(r"src\ecom_v51\services\import_service.py")


def _replace_once(text: str, pattern: str, replacement: str, label: str) -> str:
    new_text, count = re.subn(pattern, replacement, text, count=1, flags=re.DOTALL)
    if count != 1:
        raise RuntimeError(f"{label} 替换失败，命中次数={count}")
    return new_text


def main() -> None:
    if not TARGET.exists():
        raise SystemExit(f"未找到文件: {TARGET}")

    text = TARGET.read_text(encoding="utf-8")
    original = text

    text = _replace_once(
        text,
        r'''    DYNAMIC_PATTERNS\s*=\s*\[(?:.*?)\]\s*    GENERIC_HEADER_PIECES''',
        '''    DYNAMIC_PATTERNS = [
        "динамик",
        "изменени",
        "change",
        "delta",
        "trend",
        "рост",
        "снижение",
    ]

    CORE_SAFE_NOISE_TOKENS = {
        "динамик": "dynamic",
        "изменени": "dynamic",
        "trend": "dynamic",
        "delta": "dynamic",
        "change": "dynamic",
        "рост": "dynamic",
        "снижение": "dynamic",
        "доля": "share",
        "share": "share",
        "процент": "share",
        "%": "share",
        "abc": "abc",
        "abc-анализ": "abc",
        "рекомендац": "recommendation",
        "recommend": "recommendation",
        "建议": "recommendation",
        "补货": "ops_extension",
        "时效": "ops_extension",
        "оборач": "ops_extension",
        "доставка": "ops_extension",
        "平均时效": "ops_extension",
    }

    MAX_SAMPLE_VALUE_LENGTH = 72
    MAX_SAMPLE_VALUE_TOKENS = 8
    ENTITY_KEY_MIN_CONFIDENCE = 0.58

    GENERIC_HEADER_PIECES''',
        "常量区",
    )

    text = _replace_once(
        text,
        r'''    RU_PHRASE_CANONICAL_RULES\s*=\s*\[(?:.*?)\]\s*    def __init__''',
        '''    RU_PHRASE_CANONICAL_RULES = [
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
        (["индекс цен"], "price_index_status"),
        (["средняя позиция", "поиск"], "search_catalog_position_avg"),
    ]

    def __init__''',
        "俄语规则",
    )

    text = _replace_once(
        text,
        r'''    def _preview_values_for_column\((?:.*?)\n    @staticmethod''',
        '''    @staticmethod
    def _normalize_preview_text(value: object) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        text = re.sub(r"\s+", " ", text)
        return text

    def _looks_like_explanatory_text(self, value: object) -> bool:
        text = self._normalize_preview_text(value)
        if not text:
            return False

        if len(text) > self.MAX_SAMPLE_VALUE_LENGTH:
            return True

        if text.count(".") >= 2:
            return True

        comma_count = text.count(",") + text.count("，") + text.count("；") + text.count(";")
        if comma_count >= 2:
            return True

        tokens = [x for x in re.split(r"[\s/|,;:]+", text) if x]
        if len(tokens) > self.MAX_SAMPLE_VALUE_TOKENS:
            return True

        return False

    def _detect_core_safe_noise(self, value: object) -> str | None:
        text = self._normalize_preview_text(value).lower()
        if not text:
            return None

        for token, label in self.CORE_SAFE_NOISE_TOKENS.items():
            if token in text:
                return label

        if self._looks_like_explanatory_text(text):
            return "explanatory_text"

        return None

    def _sanitize_sample_values(self, values: list[object], limit: int = 3) -> list[object]:
        cleaned: list[object] = []
        seen: set[str] = set()

        for raw in values or []:
            scalar = self._safe_scalar(raw)
            if scalar is None:
                continue

            if isinstance(scalar, float) and pd.isna(scalar):
                continue

            if isinstance(scalar, (int, float)) and not isinstance(scalar, bool):
                text = str(scalar)
                if text not in seen:
                    seen.add(text)
                    cleaned.append(scalar)
                if len(cleaned) >= limit:
                    break
                continue

            text = self._normalize_preview_text(scalar)
            if not text or text.lower() == "nan":
                continue

            if self._looks_like_explanatory_text(text):
                continue

            if text in seen:
                continue

            seen.add(text)
            cleaned.append(text)

            if len(cleaned) >= limit:
                break

        return cleaned

    def _preview_values_for_column(
        self, df: pd.DataFrame, col: object, limit: int = 3
    ) -> list[object]:
        if col not in df.columns:
            return []

        selected = df.loc[:, col]
        raw_values: list[object] = []

        if isinstance(selected, pd.DataFrame):
            for row in selected.head(max(limit * 3, 9)).itertuples(index=False, name=None):
                for item in row if isinstance(row, tuple) else (row,):
                    raw_values.append(self._safe_scalar(item))
                    if len(raw_values) >= max(limit * 4, 12):
                        return self._sanitize_sample_values(raw_values, limit=limit)
            return self._sanitize_sample_values(raw_values, limit=limit)

        try:
            source = selected.head(max(limit * 3, 9)).tolist()
        except Exception:
            head_part = selected.head(max(limit * 3, 9))
            source = head_part.values.tolist() if hasattr(head_part, "values") else []

        for item in source:
            if isinstance(item, list):
                for nested in item:
                    raw_values.append(self._safe_scalar(nested))
            else:
                raw_values.append(self._safe_scalar(item))

            if len(raw_values) >= max(limit * 4, 12):
                break

        return self._sanitize_sample_values(raw_values, limit=limit)

    @staticmethod''',
        "样本值清洗",
    )

    text = _replace_once(
        text,
        r'''    def _score_entity_key_candidate\((?:.*?)\n    def _collect_entity_key_probe_values''',
        '''    def _score_entity_key_candidate(self, text: str) -> float:
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

        if self._detect_core_safe_noise(raw):
            score -= 0.35

        if self._looks_like_explanatory_text(raw):
            score -= 0.4

        if raw.startswith("Unnamed:") or raw.startswith("col_"):
            score -= 0.15

        return round(max(score, 0.0), 4)

    def _collect_entity_key_probe_values''',
        "entity key 评分",
    )

    text = _replace_once(
        text,
        r'''    def _collect_entity_key_probe_values\((?:.*?)\n    def _build_entity_key_suggestion''',
        '''    def _collect_entity_key_probe_values(
        self,
        df: pd.DataFrame,
        field_mappings: list[dict],
        limit: int = 12,
    ) -> list[tuple[str, str]]:
        values: list[tuple[str, str]] = []
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
            lower = header.lower()

            if self._detect_core_safe_noise(header):
                continue

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

                if self._detect_core_safe_noise(text):
                    continue

                token = self._extract_entity_key_token(text)
                if token:
                    values.append((header, token))
                elif not self._looks_like_explanatory_text(text) and len(text) <= 48:
                    values.append((header, text))

                if len(values) >= limit:
                    return values

        return values

    def _build_entity_key_suggestion''',
        "entity key 探针",
    )

    text = _replace_once(
        text,
        r'''    def _build_entity_key_suggestion\((?:.*?)\n    # ---------- 读取 / 表头恢复 ----------''',
        '''    def _build_entity_key_suggestion(
        self,
        top_unmapped_headers: list[str],
        recovery_candidate_preview: list[dict],
        mapped_canonical_fields: list[str],
        field_mappings: list[dict] | None = None,
        df: pd.DataFrame | None = None,
    ) -> dict | None:
        if "sku" in {str(x) for x in (mapped_canonical_fields or [])}:
            return None

        candidate_pool: list[tuple[str, str | None, str]] = []

        for item in top_unmapped_headers or []:
            candidate_pool.append(("topUnmappedHeaders", None, str(item)))

        for candidate in recovery_candidate_preview or []:
            for example in candidate.get("flattenedHeaderExamples") or []:
                candidate_pool.append(("recoveryCandidatePreview", None, str(example)))

        for item in field_mappings or []:
            if item.get("standardField") or item.get("dynamicCompanion"):
                continue

            original_field = str(item.get("originalField") or "")
            if original_field:
                candidate_pool.append(("fieldMappings.originalField", original_field, original_field))

            for value in self._sanitize_sample_values(item.get("sampleValues") or [], limit=3):
                candidate_pool.append(("fieldMappings.sampleValues", original_field or None, str(value)))

        if df is not None:
            for column_name, value in self._collect_entity_key_probe_values(df, field_mappings or []):
                candidate_pool.append(("dataProbeValues", column_name, value))

        best = None
        best_score = 0.0
        best_token = None
        best_source = None
        best_column = None
        best_text = None

        for source, column_name, raw in candidate_pool:
            if self._detect_core_safe_noise(raw):
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

    # ---------- 读取 / 表头恢复 ----------''',
        "entity key 建议",
    )

    if text == original:
        raise RuntimeError("没有产生任何改动，说明补丁没有命中当前分支代码。")

    with TARGET.open("w", encoding="utf-8", newline="") as f:
        f.write(text)

    print("patched:", TARGET)


if __name__ == "__main__":
    main()
