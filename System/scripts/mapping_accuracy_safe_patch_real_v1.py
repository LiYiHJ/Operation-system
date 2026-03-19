from pathlib import Path

TARGET = Path(r"C:\Operation-system\System\src\ecom_v51\services\import_service.py")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label} 替换失败，命中次数={count}")
    return text.replace(old, new, 1)


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")

    old_header_hints = '''    ENTITY_KEY_HEADER_HINTS = [
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
'''
    new_header_hints = old_header_hints + '\n    ENTITY_KEY_MIN_CONFIDENCE = 0.58\n'

    old_score = '''    def _score_entity_key_candidate(self, text: str) -> float:
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

        if raw.startswith("Unnamed:") or raw.startswith("col_"):
            score -= 0.15

        return round(max(score, 0.0), 4)
'''
    new_score = '''    def _score_entity_key_candidate(self, text: str) -> float:
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
'''

    old_collect = '''    def _collect_entity_key_probe_values(
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
                values.append((header, text))
                if len(values) >= limit:
                    return values

        return values
'''
    new_collect = '''    def _collect_entity_key_probe_values(
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
'''

    old_build = '''    def _build_entity_key_suggestion(
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
            candidate_pool.append(("topUnmappedHeaders", None, str(item)))

        for candidate in recovery_candidate_preview or []:
            for example in candidate.get("flattenedHeaderExamples") or []:
                candidate_pool.append(("recoveryCandidatePreview", None, str(example)))

        for item in field_mappings or []:
            if item.get("standardField") or item.get("dynamicCompanion"):
                continue
            original_field = str(item.get("originalField") or "")
            if original_field:
                candidate_pool.append(
                    ("fieldMappings.originalField", original_field, original_field)
                )
            for value in item.get("sampleValues") or []:
                candidate_pool.append(
                    ("fieldMappings.sampleValues", original_field or None, str(value))
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

        if best_score < 0.45:
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
'''
    new_build = '''    def _build_entity_key_suggestion(
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
'''

    old_apply = '''    def _apply_manual_overrides_to_staging(
        self,
        staging_df: pd.DataFrame,
        field_mappings: List[dict],
        manual_overrides: List[dict],
    ) -> tuple[pd.DataFrame, List[dict]]:
        next_df = staging_df.copy()
        next_field_mappings = copy.deepcopy(field_mappings or [])

        for item in manual_overrides or []:
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

        return next_df, next_field_mappings
'''
    new_apply = '''    def _apply_manual_overrides_to_staging(
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
'''

    text = replace_once(text, old_header_hints, new_header_hints, "ENTITY_KEY_HEADER_HINTS")
    text = replace_once(text, old_score, new_score, "_score_entity_key_candidate")
    text = replace_once(text, old_collect, new_collect, "_collect_entity_key_probe_values")
    text = replace_once(text, old_build, new_build, "_build_entity_key_suggestion")
    text = replace_once(text, old_apply, new_apply, "_apply_manual_overrides_to_staging")

    TARGET.write_text(text, encoding="utf-8", newline="\n")
    print("已完成真实基线小补丁：entity-key 降噪 + manual override 唯一性收口")


if __name__ == "__main__":
    main()
