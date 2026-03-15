from __future__ import annotations

from pathlib import Path
import shutil
import sys

DEFAULT_TARGET = Path(r"C:\Operation-system\System\src\ecom_v51\services\import_service.py")


def replace_exact(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"[{label}] target block not found")
    return text.replace(old, new, 1)


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TARGET
    if not target.exists():
        raise SystemExit(f"Target file not found: {target}")

    backup = target.with_suffix(target.suffix + ".bak_import_gate_v2")
    shutil.copy2(target, backup)

    text = target.read_text(encoding="utf-8")
    original = text

    old_core = '''    @staticmethod
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
        return {
            "sku": "sku" in targets,
            "orders_or_order_amount": bool({"orders", "order_amount"} & targets),
            "impressions_total": "impressions_total" in targets,
            "product_card_visits_or_add_to_cart_total": bool({"product_card_visits", "add_to_cart_total"} & targets),
            "optionalFieldPool": optional_pool,
            "optionalHitCount": len(optional_hits),
            "optionalHitFields": optional_hits,
            "mappedTargets": sorted(targets),
        }
'''

    new_core = '''    @staticmethod
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
            "criticalComboComplete": all([
                "sku" in targets,
                bool({"orders", "order_amount"} & targets),
                bool({"impressions_total", "impressions_search_catalog"} & targets),
                bool({"product_card_visits", "add_to_cart_total"} & targets),
            ]),
            "mappedTargets": sorted(targets),
        }
'''

    if '"criticalComboComplete"' not in text:
        text = replace_exact(text, old_core, new_core, "core field summary")

    old_gate = '''    @staticmethod
    def _semantic_gate(mapped_targets: List[str], candidate_columns: int, mapped_count: int, wrongly_mapped_count: int, header_signals: List[str], header_structure_score: float) -> Tuple[str, List[str], List[str], List[str], dict]:
        reasons: List[str] = []
        risk_override_reasons: List[str] = []
        acceptance_reason: List[str] = []
        coverage = round(mapped_count / candidate_columns, 3) if candidate_columns > 0 else 0.0
        core = ImportService._build_core_field_hit_summary(mapped_targets)

        if mapped_count == 0 or candidate_columns == 0:
            return "failed", ["no_mapped_fields"], [], [], {"mappingCoverage": coverage, "mappedCount": mapped_count, "unmappedCount": max(candidate_columns - mapped_count, 0)}

        if not core["sku"]:
            reasons.append("missing_sku")
        if not core["orders_or_order_amount"]:
            reasons.append("missing_order_signal")
        if not core["impressions_total"]:
            reasons.append("missing_top_funnel_signal")
        if not core["product_card_visits_or_add_to_cart_total"]:
            reasons.append("missing_mid_funnel_signal")
        if coverage < 0.5:
            reasons.append("mapping_coverage_below_0_5")
        if mapped_count < 4:
            reasons.append("mapped_count_below_4")
        if core["sku"] is False or core["orders_or_order_amount"] is False or core["impressions_total"] is False or core["product_card_visits_or_add_to_cart_total"] is False:
            reasons.append("insufficient_core_field_hits")
        if wrongly_mapped_count > 0:
            reasons.append("wrongly_mapped_fields_present")

        strong_risk_signals = {"multi_row_header_block", "short_explainable_column_run", "placeholder_columns_present"}
        risk_signal_hits = sorted(strong_risk_signals & set(header_signals))
        if len(risk_signal_hits) >= 2 and header_structure_score < 0.65:
            risk_override_reasons.append("multiple_header_risk_signals")
        if "short_explainable_column_run" in risk_signal_hits:
            risk_override_reasons.append("short_explainable_column_run")

        if not reasons:
            if risk_override_reasons:
                return "risk", [], risk_override_reasons, [], {
                    "mappingCoverage": coverage,
                    "mappedCount": mapped_count,
                    "unmappedCount": max(candidate_columns - mapped_count, 0),
                }
            acceptance_reason.extend(["mapping_thresholds_met", "core_fields_present"])
            return "passed", [], [], acceptance_reason, {
                "mappingCoverage": coverage,
                "mappedCount": mapped_count,
                "unmappedCount": max(candidate_columns - mapped_count, 0),
            }

        if mapped_count >= 2:
            return "risk", reasons, risk_override_reasons, acceptance_reason, {
                "mappingCoverage": coverage,
                "mappedCount": mapped_count,
                "unmappedCount": max(candidate_columns - mapped_count, 0),
            }
        return "failed", reasons, risk_override_reasons, acceptance_reason, {
            "mappingCoverage": coverage,
            "mappedCount": mapped_count,
            "unmappedCount": max(candidate_columns - mapped_count, 0),
        }
'''

    new_gate = '''    @staticmethod
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

        if not core.get("criticalComboComplete"):
            reasons.append("insufficient_core_field_hits")

        if len(risk_signal_hits) >= 2 and header_structure_score < 0.68:
            risk_override_reasons.append("multiple_header_risk_signals")
        if "short_explainable_column_run" in risk_signal_hits:
            risk_override_reasons.append("short_explainable_column_run")

        if not reasons:
            if risk_override_reasons:
                return "risk", [], risk_override_reasons, [], metrics
            acceptance_reason.extend(["mapping_thresholds_met", "core_fields_present", "funnel_shape_present"])
            return "passed", [], [], acceptance_reason, metrics

        if mapped_count >= 2:
            return "risk", reasons, risk_override_reasons, acceptance_reason, metrics
        return "failed", reasons, risk_override_reasons, acceptance_reason, metrics
'''

    if '"underStructureScrutiny"' not in text:
        text = replace_exact(text, old_gate, new_gate, "semantic gate")

    old_build_bits = '''        mapped_targets = [str(item["standardField"]) for item in field_mappings if item.get("standardField")]
        candidate_columns = sum(1 for col in df.columns if not self._is_placeholder_col(col))
        mapped_count = len(mapped_targets)
        unmapped_fields = [str(item["originalField"]) for item in field_mappings if not item.get("standardField")]
'''

    new_build_bits = '''        semantic_field_mappings = [item for item in field_mappings if not item.get("excludeFromSemanticGate")]
        mapped_targets = [str(item["standardField"]) for item in semantic_field_mappings if item.get("standardField")]
        candidate_columns = sum(1 for item in semantic_field_mappings if not self._is_placeholder_col(item.get("originalField")))
        mapped_count = len(mapped_targets)
        unmapped_fields = [str(item["originalField"]) for item in semantic_field_mappings if not item.get("standardField")]
'''

    if 'semantic_field_mappings = [item for item in field_mappings if not item.get("excludeFromSemanticGate")]' not in text:
        text = replace_exact(text, old_build_bits, new_build_bits, "bundle semantic field filtering")

    old_stats = '''        stats = {
            "candidateColumns": candidate_columns,
            "ignoredColumns": len(active_bundle["droppedPlaceholderColumns"]),
            "ignoredFields": active_bundle["droppedPlaceholderColumns"],
            "mappedConfidence": float(active_bundle["semanticMetrics"].get("mappedConfidence") or 0.0),
            "mappingCoverage": float(active_bundle["semanticMetrics"].get("mappingCoverage") or 0.0),
            "mappedCount": mapped_count,
            "unmappedCount": int(active_bundle["unmappedCount"]),
            "correctlyMappedCount": mapped_count,
            "wronglyMappedCount": int(active_bundle["semanticMetrics"].get("wronglyMappedCount") or 0),
            "ruUnmappedCount": 0,
            "ruMappingPass": True,
            "droppedPlaceholderColumns": active_bundle["droppedPlaceholderColumns"],
            "removedSummaryRows": 0,
            "removedDescriptionRows": int(header_block.get("startRow") or 0),
            "recoveryCandidateCount": int(recovery_result.get("candidateCount") or 0),
            "recoveryCandidatePreview": list(recovery_result.get("candidatePreview") or []),
        }
'''

    new_stats = '''        stats = {
            "candidateColumns": candidate_columns,
            "ignoredColumns": len(active_bundle["droppedPlaceholderColumns"]),
            "ignoredFields": active_bundle["droppedPlaceholderColumns"],
            "mappedConfidence": float(active_bundle["semanticMetrics"].get("mappedConfidence") or 0.0),
            "mappingCoverage": float(active_bundle["semanticMetrics"].get("mappingCoverage") or 0.0),
            "mappedCount": mapped_count,
            "unmappedCount": int(active_bundle["unmappedCount"]),
            "correctlyMappedCount": mapped_count,
            "wronglyMappedCount": int(active_bundle["semanticMetrics"].get("wronglyMappedCount") or 0),
            "ruUnmappedCount": 0,
            "ruMappingPass": True,
            "droppedPlaceholderColumns": active_bundle["droppedPlaceholderColumns"],
            "dynamicMetricColumns": [str(item.get("originalField")) for item in (active_bundle.get("fieldMappings") or []) if item.get("dynamicCompanion")],
            "removedSummaryRows": 0,
            "removedDescriptionRows": int(header_block.get("startRow") or 0),
            "recoveryCandidateCount": int(recovery_result.get("candidateCount") or 0),
            "recoveryCandidatePreview": list(recovery_result.get("candidatePreview") or []),
        }
'''

    if '"dynamicMetricColumns"' not in text:
        text = replace_exact(text, old_stats, new_stats, "stats dynamic metric columns")

    old_result_tail = '''            "platform": active_bundle["platform"],
            "fieldMappings": active_bundle["fieldMappings"],
            "mappedCount": mapped_count,
            "unmappedCount": int(active_bundle["unmappedCount"]),
'''

    new_result_tail = '''            "platform": active_bundle["platform"],
            "fieldMappings": active_bundle["fieldMappings"],
            "mappedCanonicalFields": list(dict.fromkeys([str(item.get("standardField")) for item in (active_bundle.get("fieldMappings") or []) if item.get("standardField")]))[:20],
            "topUnmappedHeaders": [str(item.get("originalField")) for item in (active_bundle.get("fieldMappings") or []) if not item.get("standardField") and not item.get("dynamicCompanion")][:20],
            "mappedCount": mapped_count,
            "unmappedCount": int(active_bundle["unmappedCount"]),
'''

    if '"mappedCanonicalFields": list(dict.fromkeys([str(item.get("standardField")) for item in (active_bundle.get("fieldMappings") or []) if item.get("standardField")]))[:20]' not in text:
        text = replace_exact(text, old_result_tail, new_result_tail, "result mapped/unmapped detail fields")

    if text == original:
        print("No changes needed; file already contains the v2 gate upgrade.")
        print(f"Backup kept at: {backup}")
        return

    target.write_text(text, encoding="utf-8", newline="\n")
    print(f"Patched: {target}")
    print(f"Backup:  {backup}")


if __name__ == "__main__":
    main()
