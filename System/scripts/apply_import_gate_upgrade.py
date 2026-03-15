from __future__ import annotations

import re
from pathlib import Path

TARGET = Path(r"C:\Operation-system\System\src\ecom_v51\services\import_service.py")


def replace_once(text: str, pattern: str, replacement: str, label: str) -> str:
    new_text, count = re.subn(pattern, replacement, text, count=1, flags=re.DOTALL | re.MULTILINE)
    if count != 1:
        raise RuntimeError(f"[{label}] replacement failed; expected 1 match, got {count}")
    return new_text


def main() -> None:
    if not TARGET.exists():
        raise SystemExit(f"Target file not found: {TARGET}")

    text = TARGET.read_text(encoding="utf-8")
    original = text

    if "DYNAMIC_HEADER_PATTERNS" not in text:
        text = replace_once(
            text,
            r"(\n\s*NUMERIC_CANONICALS = \{.*?\n\s*\}\n)(\n\s*def __init__\(self\) -> None:)",
            """\1
    DYNAMIC_HEADER_PATTERNS = (
        \"динамика\",
        \"изменение\",
        \"trend\",
        \"delta\",
        \"growth\",
        \"变化\",
        \"环比\",
        \"同比\",
    )
\2""",
            "insert dynamic header patterns",
        )

    if "def _is_dynamic_metric_col" not in text:
        text = replace_once(
            text,
            r"(\n\s*@staticmethod\n\s*def _is_placeholder_col\(name: Any\) -> bool:\n.*?\n\s*return lower\.startswith\(\"unnamed:\"\) or re\.fullmatch\(r\"col_\?\\d\+\", lower\) is not None or lower in \{\"none\", \"nan\"\}\n)(\n\s*@staticmethod\n\s*def _safe_scalar\(value: Any\) -> Any:)",
            """\1

    @classmethod
    def _is_dynamic_metric_col(cls, name: Any) -> bool:
        normalized = cls._normalize_header_without_unit(name)
        return any(token in normalized for token in cls.DYNAMIC_HEADER_PATTERNS)
\2""",
            "insert dynamic metric helper",
        )

    text = replace_once(
        text,
        r"\n\s*def _detect_header_block\(self, raw_df: pd\.DataFrame\) -> dict:\n.*?\n\s*def _flatten_headers\(self, raw_df: pd\.DataFrame, header_block: dict\) -> Tuple\[List\[str\], List\[str\], List\[str\]\]:",
        """
    def _detect_header_block(self, raw_df: pd.DataFrame) -> dict:
        if raw_df.empty:
            return {"startRow": 0, "endRow": 0, "confidence": 0.0, "signals": ["empty_file"]}

        max_scan = min(len(raw_df), 20)
        best_row = 0
        best_score = -1.0
        signals: List[str] = []

        for idx in range(max_scan):
            row = raw_df.iloc[idx].tolist()
            non_empty = [str(x).strip() for x in row if str(x).strip() not in {"", "nan", "None"}]
            if not non_empty:
                continue

            unique = len(set(non_empty))
            text_like = sum(1 for x in non_empty if re.search(r"[A-Za-zА-Яа-я一-龥]", x))
            numeric_like = sum(1 for x in non_empty if re.fullmatch(r"[-+]?[%\\d\\s,._/]+", x) is not None)
            placeholder_like = sum(1 for x in non_empty if self._is_placeholder_col(x))
            preferred_bonus = max(0.0, 0.6 - (idx * 0.08)) if idx <= 6 else 0.0

            score = (
                len(non_empty)
                + (unique * 0.25)
                + (text_like * 0.25)
                + preferred_bonus
                - (numeric_like * 0.35)
                - (placeholder_like * 0.5)
            )

            if score > best_score:
                best_score = score
                best_row = idx

        end_row = best_row
        if best_row + 1 < max_scan:
            next_row = [str(x).strip() for x in raw_df.iloc[best_row + 1].tolist()]
            next_non_empty = [x for x in next_row if x not in {"", "nan", "None"}]
            current_non_empty = [x for x in raw_df.iloc[best_row].tolist() if str(x).strip() not in {"", "nan", "None"}]
            if len(next_non_empty) >= max(2, int(len(current_non_empty) * 0.45)):
                end_row = best_row + 1
                signals.append("multi_row_header_block")

        header_values = [str(x).strip() for x in raw_df.iloc[best_row].tolist()]
        placeholder_count = sum(1 for x in header_values if self._is_placeholder_col(x))
        if placeholder_count > 0:
            signals.append("placeholder_columns_present")
        if len([x for x in header_values if str(x).strip()]) < 4:
            signals.append("short_explainable_column_run")

        confidence = min(0.95, 0.45 + max(0.0, best_score) / max(8.0, raw_df.shape[1] + 4.0))
        return {
            "startRow": int(best_row),
            "endRow": int(end_row),
            "confidence": round(float(confidence), 3),
            "signals": signals,
        }

    def _flatten_headers(self, raw_df: pd.DataFrame, header_block: dict) -> Tuple[List[str], List[str], List[str]]:""",
        "replace detect header block",
    )

    text = replace_once(
        text,
        r"\n\s*@staticmethod\n\s*def _build_core_field_hit_summary\(mapped_targets: List\[str\]\) -> dict:\n.*?\n\s*@staticmethod\n\s*def _compute_header_structure_score\(header_block: dict, flattened_headers: List\[str\], dropped_placeholders: List\[str\]\) -> Tuple\[float, List\[str\]\]:",
        """
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
            "impressions_total_or_search_catalog": bool({"impressions_total", "impressions_search_catalog"} & targets),
            "product_card_visits": "product_card_visits" in targets,
            "add_to_cart_total": "add_to_cart_total" in targets,
            "product_card_visits_or_add_to_cart_total": bool({"product_card_visits", "add_to_cart_total"} & targets),
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
    def _compute_header_structure_score(header_block: dict, flattened_headers: List[str], dropped_placeholders: List[str]) -> Tuple[float, List[str]]:""",
        "replace core field summary",
    )

    text = replace_once(
        text,
        r"\n\s*@staticmethod\n\s*def _semantic_gate\(mapped_targets: List\[str\], candidate_columns: int, mapped_count: int, wrongly_mapped_count: int, header_signals: List\[str\], header_structure_score: float\) -> Tuple\[str, List\[str\], List\[str\], List\[str\], dict\]:\n.*?\n\s*# ---------- 主链路 ----------",
        """
    @staticmethod
    def _semantic_gate(mapped_targets: List[str], candidate_columns: int, mapped_count: int, wrongly_mapped_count: int, header_signals: List[str], header_structure_score: float) -> Tuple[str, List[str], List[str], List[str], dict]:
        reasons: List[str] = []
        risk_override_reasons: List[str] = []
        acceptance_reason: List[str] = []
        coverage = round(mapped_count / candidate_columns, 3) if candidate_columns > 0 else 0.0
        core = ImportService._build_core_field_hit_summary(mapped_targets)
        strong_risk_signals = {"multi_row_header_block", "short_explainable_column_run", "placeholder_columns_present"}
        risk_signal_hits = sorted(strong_risk_signals & set(header_signals))
        under_structure_scrutiny = bool(risk_signal_hits) or header_structure_score < 0.72
        metrics = {
            "mappingCoverage": coverage,
            "mappedCount": mapped_count,
            "unmappedCount": max(candidate_columns - mapped_count, 0),
            "funnelSignalCount": int(core.get("funnelSignalCount") or 0),
            "structureRiskHitCount": len(risk_signal_hits),
            "underStructureScrutiny": under_structure_scrutiny,
        }

        if mapped_count == 0 or candidate_columns == 0:
            return "failed", ["no_mapped_fields"], [], [], metrics

        if not core["sku"]:
            reasons.append("missing_sku")
        if not core["orders_or_order_amount"]:
            reasons.append("missing_orders_or_order_amount")
        if coverage < 0.5:
            reasons.append("mapping_coverage_below_0_5")
        if mapped_count < 4:
            reasons.append("mapped_count_below_4")
        if wrongly_mapped_count > 0:
            reasons.append("wrongly_mapped_fields_present")

        if under_structure_scrutiny:
            if not core["impressions_total_or_search_catalog"]:
                reasons.append("missing_impression_signal_under_header_risk")
            if not core["product_card_visits_or_add_to_cart_total"]:
                reasons.append("missing_engagement_signal_under_header_risk")
            if int(core.get("funnelSignalCount") or 0) < 3:
                reasons.append("insufficient_funnel_signal_count_under_header_risk")

        if len(risk_signal_hits) >= 2 and header_structure_score < 0.72:
            risk_override_reasons.append("multiple_header_risk_signals_low_structure_score")
        if "short_explainable_column_run" in risk_signal_hits and int(core.get("funnelSignalCount") or 0) < 4:
            risk_override_reasons.append("short_explainable_column_run")

        if not reasons:
            acceptance_reason.extend(["mapping_thresholds_met", "core_fields_present"])
            if under_structure_scrutiny:
                acceptance_reason.append("funnel_combo_present_under_header_risk")
            if risk_override_reasons:
                return "risk", [], risk_override_reasons, acceptance_reason, metrics
            return "passed", [], [], acceptance_reason, metrics

        if mapped_count >= 3:
            return "risk", reasons, risk_override_reasons, acceptance_reason, metrics
        return "failed", reasons, risk_override_reasons, acceptance_reason, metrics

    # ---------- 主链路 ----------""",
        "replace semantic gate",
    )

    text = replace_once(
        text,
        r"candidate_columns = sum\(1 for col in df\.columns if not self\._is_placeholder_col\(col\)\)",
        "candidate_columns = sum(1 for col in df.columns if not self._is_placeholder_col(col) and not self._is_dynamic_metric_col(col))",
        "filter dynamic columns from candidate count",
    )

    text = replace_once(
        text,
        r"unmapped_fields = \[str\(item\[\"originalField\"\]\) for item in field_mappings if not item\.get\(\"standardField\"\)\]",
        "unmapped_fields = [str(item[\"originalField\"]) for item in field_mappings if not item.get(\"standardField\") and item.get(\"mappingSource\") not in {\"placeholder\", \"dynamic_metric\"}]",
        "filter placeholder and dynamic unmapped fields",
    )

    text = replace_once(
        text,
        r"wrongly_mapped_count = 0\n\s*header_structure_score, header_structure_signals = self\._compute_header_structure_score\(header_block, flattened_headers, dropped_placeholder_columns\)",
        """wrongly_mapped_count = 0
        mapped_canonical_fields = sorted(set(mapped_targets))
        top_unmapped_headers = unmapped_fields[:10]
        header_structure_score, header_structure_signals = self._compute_header_structure_score(header_block, flattened_headers, dropped_placeholder_columns)""",
        "add mapped/unmapped diagnostics",
    )

    text = replace_once(
        text,
        r'"coreFieldHitSummary": self\._build_core_field_hit_summary\(mapped_targets\),\n',
        '"coreFieldHitSummary": self._build_core_field_hit_summary(mapped_targets),\n            "mappedCanonicalFields": mapped_canonical_fields,\n            "topUnmappedHeaders": top_unmapped_headers,\n',
        "add bundle diagnostics fields",
    )

    if 'dynamicMetricColumns' not in text:
        text = replace_once(
            text,
            r'"ignoredFields": active_bundle\["droppedPlaceholderColumns"\],\n',
            '"ignoredFields": active_bundle["droppedPlaceholderColumns"],\n            "dynamicMetricColumns": [item["originalField"] for item in active_bundle["fieldMappings"] if item.get("mappingSource") == "dynamic_metric"],\n',
            "add dynamic metric stats",
        )

    if '"mappedCanonicalFields": active_bundle["mappedCanonicalFields"]' not in text:
        text = replace_once(
            text,
            r'"coreFieldHitSummary": active_bundle\["coreFieldHitSummary"\],\n',
            '"coreFieldHitSummary": active_bundle["coreFieldHitSummary"],\n            "mappedCanonicalFields": active_bundle["mappedCanonicalFields"],\n            "topUnmappedHeaders": active_bundle["topUnmappedHeaders"],\n',
            "expose diagnostics in parse result",
        )

    text = replace_once(
        text,
        r"\n\s*def _map_single_column\(self, col: Any\) -> Tuple\[Optional\[str\], str, List\[str\]\]:\n\s*original = str\(col or \"\"\)\n\s*normalized = self\._normalize_header\(original\)\n\s*normalized_wo_unit = self\._normalize_header_without_unit\(original\)\n\s*reasons: List\[str\] = \[\]\n\s*canonical = None\n\s*source = \"unmapped\"",
        """
    def _map_single_column(self, col: Any) -> Tuple[Optional[str], str, List[str]]:
        original = str(col or "")
        reasons: List[str] = []
        if self._is_placeholder_col(original):
            return None, "placeholder", ["placeholder_column"]
        if self._is_dynamic_metric_col(original):
            return None, "dynamic_metric", ["dynamic_metric_column"]

        normalized = self._normalize_header(original)
        normalized_wo_unit = self._normalize_header_without_unit(original)
        canonical = None
        source = "unmapped""",
        "ignore placeholder and dynamic columns in mapping",
    )

    if text == original:
        raise SystemExit("No changes applied; file may already contain the upgrade or the source layout changed.")

    backup = TARGET.with_suffix(TARGET.suffix + ".bak_import_gate_upgrade")
    backup.write_text(original, encoding="utf-8")
    TARGET.write_text(text, encoding="utf-8")
    print(f"Updated: {TARGET}")
    print(f"Backup : {backup}")


if __name__ == "__main__":
    main()
