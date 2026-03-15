from __future__ import annotations

from pathlib import Path
import re

TARGET = Path(r"C:\Operation-system\System\src\ecom_v51\services\import_service.py")


def replace_once(text: str, pattern: str, replacement: str, label: str) -> str:
    new_text, count = re.subn(pattern, replacement, text, count=1, flags=re.DOTALL)
    if count != 1:
        raise RuntimeError(f"[{label}] replacement failed; expected 1 match, got {count}")
    return new_text


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")
    backup = TARGET.with_suffix(TARGET.suffix + ".bak_semantic_gate_clean_bundle")
    backup.write_text(text, encoding="utf-8")

    old_metrics = r'''        metrics = \{
            "mappingCoverage": coverage,
            "mappedCount": mapped_count,
            "unmappedCount": max\(candidate_columns - mapped_count, 0\),
            "funnelSignalCount": int\(core.get\("funnelSignalCount"\) or 0\),
            "structureRiskHitCount": len\(risk_signal_hits\),
            "underStructureScrutiny": under_structure_scrutiny,
        \}
'''
    new_metrics = '''        clean_strong_bundle_without_sku = (
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
        critical_requirements_met = bool(core.get("criticalComboComplete")) or clean_strong_bundle_without_sku
        metrics = {
            "mappingCoverage": coverage,
            "mappedCount": mapped_count,
            "unmappedCount": max(candidate_columns - mapped_count, 0),
            "funnelSignalCount": int(core.get("funnelSignalCount") or 0),
            "structureRiskHitCount": len(risk_signal_hits),
            "underStructureScrutiny": under_structure_scrutiny,
            "cleanStrongBundleWithoutSku": clean_strong_bundle_without_sku,
        }
'''
    text = replace_once(text, old_metrics, new_metrics, "insert clean strong bundle metrics")

    old_missing_sku = r'''        if not core\["sku"\]:
            reasons.append\("missing_sku"\)
'''
    new_missing_sku = '''        if not core["sku"] and not clean_strong_bundle_without_sku:
            reasons.append("missing_sku")
'''
    text = replace_once(text, old_missing_sku, new_missing_sku, "soften missing_sku for clean bundle")

    old_core_hits = r'''        if not core.get\("criticalComboComplete"\):
            reasons.append\("insufficient_core_field_hits"\)
'''
    new_core_hits = '''        if not critical_requirements_met:
            reasons.append("insufficient_core_field_hits")
'''
    text = replace_once(text, old_core_hits, new_core_hits, "soften critical combo for clean bundle")

    old_accept = r'''            acceptance_reason.extend\(\["mapping_thresholds_met", "core_fields_present", "funnel_shape_present"\]\)
            return "passed", \[\], \[\], acceptance_reason, metrics
'''
    new_accept = '''            if clean_strong_bundle_without_sku:
                acceptance_reason.extend([
                    "mapping_thresholds_met",
                    "clean_structure_exception",
                    "funnel_shape_present",
                ])
            else:
                acceptance_reason.extend(["mapping_thresholds_met", "core_fields_present", "funnel_shape_present"])
            return "passed", [], [], acceptance_reason, metrics
'''
    text = replace_once(text, old_accept, new_accept, "adjust acceptance reason")

    TARGET.write_text(text, encoding="utf-8")
    print(f"patched: {TARGET}")
    print(f"backup : {backup}")


if __name__ == "__main__":
    main()
