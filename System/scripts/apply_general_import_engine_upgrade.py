from __future__ import annotations

import re
from pathlib import Path

ROOT = Path.cwd()
SERVICE_PATH = ROOT / "src" / "ecom_v51" / "services" / "import_service.py"
ENGINE_DIR = ROOT / "src" / "ecom_v51" / "import_engine"


CANONICAL_REGISTRY = '''from __future__ import annotations

ENTITY_KEY_FIELD_CANDIDATES = (
    "sku",
    "seller_sku",
    "offer_id",
    "product_id",
    "item_id",
    "asin",
    "ean",
    "barcode",
)

ENTITY_KEY_HEADER_KEYWORDS = (
    "sku",
    "seller sku",
    "seller_sku",
    "offer id",
    "offer_id",
    "product id",
    "product_id",
    "item id",
    "item_id",
    "asin",
    "ean",
    "barcode",
    "货号",
    "商品编码",
    "商家编码",
    "产品编号",
    "商品id",
    "商品编号",
    "条码",
    "артикул",
    "артикул продавца",
    "код товара",
)
'''


VALUE_SEMANTIC = '''from __future__ import annotations

import re
from typing import Iterable, Optional

from .canonical_registry import ENTITY_KEY_HEADER_KEYWORDS

ENTITY_KEY_PATTERNS = [
    re.compile(r"(?i)\\b[A-Z]{2,}[A-Z0-9-]{3,}\\b"),
    re.compile(r"(?i)\\b[A-Z0-9]{2,}-[A-Z0-9-]{2,}\\b"),
    re.compile(r"(?i)\\bSKU[-_ ]?[A-Z0-9]{2,}\\b"),
    re.compile(r"(?i)\\b[A-Z]{1,4}\\d{2,}[A-Z0-9-]*\\b"),
    re.compile(r"\\b\\d{8,14}\\b"),
]


def normalize_text_token(value: object) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\u3000", " ").replace("\xa0", " ")
    text = re.sub(r"\\s+", " ", text)
    return text.strip()


def extract_entity_key_token(value: object) -> Optional[str]:
    text = normalize_text_token(value)
    if not text:
        return None
    for pattern in ENTITY_KEY_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(0)
    return None


def looks_like_entity_key(value: object) -> bool:
    return extract_entity_key_token(value) is not None


def infer_entity_key_from_header(header: object) -> Optional[str]:
    text = normalize_text_token(header).lower()
    if not text:
        return None
    for keyword in ENTITY_KEY_HEADER_KEYWORDS:
        if keyword.lower() in text:
            if "barcode" in keyword.lower() or "ean" in keyword.lower() or "条码" in keyword:
                return "barcode"
            if "asin" in keyword.lower():
                return "asin"
            if "offer" in keyword.lower():
                return "offer_id"
            return "sku"
    return None


def score_series_as_entity_key(values: Iterable[object], header: object = "") -> float:
    values = list(values)
    non_empty = [normalize_text_token(v) for v in values if normalize_text_token(v)]
    if not non_empty:
        return 0.0
    hits = sum(1 for v in non_empty if looks_like_entity_key(v))
    unique_ratio = len(set(non_empty)) / max(len(non_empty), 1)
    score = (hits / len(non_empty)) * 0.7 + unique_ratio * 0.2
    if infer_entity_key_from_header(header):
        score += 0.1
    return round(min(score, 1.0), 3)
'''


HELPER_BLOCK = '''
    def _entity_key_fields(self) -> List[str]:
        return list(ENTITY_KEY_FIELD_CANDIDATES)

    def _mapped_target_set(self, field_mappings: List[dict]) -> set[str]:
        targets: set[str] = set()
        for item in field_mappings or []:
            target = item.get("standardField")
            if target:
                targets.add(str(target))
        return targets

    def _apply_entity_key_rescue(self, mapped_df: pd.DataFrame, field_mappings: List[dict]) -> Tuple[pd.DataFrame, List[dict], Dict[str, Any]]:
        audit: Dict[str, Any] = {
            "detected": False,
            "field": None,
            "sourceHeader": None,
            "detectedBy": None,
            "confidence": 0.0,
            "sampleToken": None,
            "candidateHeaders": [],
        }

        if mapped_df is None:
            return mapped_df, field_mappings, audit

        existing_targets = self._mapped_target_set(field_mappings)
        existing_entity_keys = sorted(existing_targets & set(self._entity_key_fields()))
        if existing_entity_keys:
            audit.update({
                "detected": True,
                "field": existing_entity_keys[0],
                "sourceHeader": existing_entity_keys[0],
                "detectedBy": "header_alias",
                "confidence": 1.0,
                "sampleToken": None,
                "candidateHeaders": existing_entity_keys,
            })
            return mapped_df, field_mappings, audit

        best_index: Optional[int] = None
        best_header: Optional[str] = None
        best_score = 0.0
        best_token: Optional[str] = None
        candidate_headers: List[str] = []

        for idx, item in enumerate(field_mappings or []):
            if item.get("standardField"):
                continue
            header = str(item.get("originalField") or "")
            if not header:
                continue
            candidate_headers.append(header)
            if header not in mapped_df.columns:
                continue
            series = mapped_df.loc[:, header]
            if isinstance(series, pd.DataFrame):
                if series.empty:
                    continue
                series = series.bfill(axis=1).iloc[:, 0]
            values = [self._safe_scalar(v) for v in series.head(50).tolist()]
            score = score_series_as_entity_key(values, header=header)
            if score > best_score:
                best_index = idx
                best_header = header
                best_score = score
                best_token = next((extract_entity_key_token(v) for v in values if extract_entity_key_token(v)), None)

        audit["candidateHeaders"] = candidate_headers[:12]
        if best_index is None or best_header is None or best_score < 0.62:
            return mapped_df, field_mappings, audit

        target_field = infer_entity_key_from_header(best_header) or "sku"
        field_mappings[best_index]["standardField"] = target_field
        field_mappings[best_index]["confidence"] = max(float(field_mappings[best_index].get("confidence") or 0.0), float(best_score))
        field_mappings[best_index]["entityKeyRescued"] = True
        field_mappings[best_index].setdefault("reasons", [])
        if "value_entity_key_rescued" not in field_mappings[best_index]["reasons"]:
            field_mappings[best_index]["reasons"].append("value_entity_key_rescued")

        mapped_df = mapped_df.rename(columns={best_header: target_field})
        mapped_df = self._collapse_duplicate_columns(mapped_df)

        audit.update({
            "detected": True,
            "field": target_field,
            "sourceHeader": best_header,
            "detectedBy": "value_semantic",
            "confidence": float(best_score),
            "sampleToken": best_token,
        })
        return mapped_df, field_mappings, audit
'''


MATRIX_SCRIPT = r'''from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path.cwd()
BASE_URL = "http://127.0.0.1:5000"
OPERATOR = "general_import_matrix"
SHOP_ID = 1
OUT_DIR = REPO_ROOT / "docs"

SAMPLES = [
    ("ru_real_xlsx", REPO_ROOT / "data" / "analytics_report_2026-03-12_23_49.xlsx"),
    ("cn_real_xlsx", REPO_ROOT / "data" / "销售数据分析.xlsx"),
    ("ru_bad_header_xlsx", REPO_ROOT / "sample_data" / "ozon_bad_header_or_missing_sku.xlsx"),
]


def run_curl(args: list[str]) -> str:
    proc = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"curl failed: {' '.join(args)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    return proc.stdout.strip()


def post_upload(sample_path: Path) -> dict:
    out = run_curl([
        "curl.exe", "-sS", "-X", "POST",
        "-F", f"file=@{sample_path}",
        "-F", f"shop_id={SHOP_ID}",
        "-F", f"operator={OPERATOR}",
        f"{BASE_URL}/api/import/upload",
    ])
    return json.loads(out)


def post_confirm(session_id: int) -> dict:
    payload = json.dumps({"sessionId": session_id, "shopId": SHOP_ID, "manualOverrides": []}, ensure_ascii=False)
    out = run_curl([
        "curl.exe", "-sS", "-X", "POST",
        "-H", "Content-Type: application/json",
        "-d", payload,
        f"{BASE_URL}/api/import/confirm",
    ])
    return json.loads(out)


def slim_upload(upload: dict) -> dict:
    return {
        "sessionId": upload.get("sessionId"),
        "transportStatus": upload.get("transportStatus"),
        "semanticStatus": upload.get("semanticStatus"),
        "finalStatus": upload.get("finalStatus"),
        "semanticGateReasons": upload.get("semanticGateReasons"),
        "riskOverrideReasons": upload.get("riskOverrideReasons"),
        "semanticAcceptanceReason": upload.get("semanticAcceptanceReason"),
        "mappedCount": upload.get("mappedCount"),
        "unmappedCount": upload.get("unmappedCount"),
        "mappingCoverage": (upload.get("semanticMetrics") or {}).get("mappingCoverage") or upload.get("mappingCoverage"),
        "headerStructureScore": upload.get("headerStructureScore"),
        "headerStructureRiskSignals": upload.get("headerStructureRiskSignals"),
        "preRecoveryStatus": upload.get("preRecoveryStatus"),
        "postRecoveryStatus": upload.get("postRecoveryStatus"),
        "recoveryAttempted": upload.get("recoveryAttempted"),
        "headerRecoveryApplied": upload.get("headerRecoveryApplied"),
        "recoveryImproved": upload.get("recoveryImproved"),
        "recoveryDiff": upload.get("recoveryDiff"),
        "mappedCanonicalFields": upload.get("mappedCanonicalFields"),
        "topUnmappedHeaders": upload.get("topUnmappedHeaders"),
        "dynamicMetricColumns": (upload.get("stats") or {}).get("dynamicMetricColumns"),
        "recoveryCandidatePreview": upload.get("recoveryCandidatePreview"),
        "entityKeyAudit": upload.get("entityKeyAudit"),
    }


def slim_confirm(confirm: dict) -> dict:
    return {
        "importedRows": confirm.get("importedRows"),
        "errorRows": confirm.get("errorRows"),
        "quarantineCount": confirm.get("quarantineCount"),
        "factLoadErrors": confirm.get("factLoadErrors"),
        "transportStatus": confirm.get("transportStatus"),
        "semanticStatus": confirm.get("semanticStatus"),
        "finalStatus": confirm.get("finalStatus"),
        "semanticGateReasons": confirm.get("semanticGateReasons"),
        "riskOverrideReasons": confirm.get("riskOverrideReasons"),
        "recoverySummary": confirm.get("recoverySummary"),
        "importabilityStatus": confirm.get("importabilityStatus"),
        "importabilityReasons": confirm.get("importabilityReasons"),
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = OUT_DIR / f"p0_general_import_matrix_{timestamp}.json"

    rows: list[dict] = []
    for sample_name, sample_path in SAMPLES:
        item: dict = {"sample": sample_name, "path": str(sample_path)}
        if not sample_path.exists():
            item["upload"] = {"status": "missing_file"}
            item["confirm"] = None
            rows.append(item)
            continue

        upload = post_upload(sample_path)
        confirm = None
        if upload.get("sessionId"):
            confirm = post_confirm(int(upload["sessionId"]))

        item["upload"] = slim_upload(upload)
        item["confirm"] = None if not confirm else slim_confirm(confirm)
        rows.append(item)

    out_file.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved: {out_file}")


if __name__ == "__main__":
    main()
'''


def replace_once(text: str, pattern: str, repl: str, label: str, flags: int = re.S) -> str:
    new_text, count = re.subn(pattern, repl, text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"[{label}] replacement failed; expected 1 match, got {count}")
    return new_text


def main() -> None:
    if not SERVICE_PATH.exists():
        raise SystemExit(f"import_service.py not found: {SERVICE_PATH}")

    ENGINE_DIR.mkdir(parents=True, exist_ok=True)
    (ENGINE_DIR / "__init__.py").write_text("", encoding="utf-8")
    (ENGINE_DIR / "canonical_registry.py").write_text(CANONICAL_REGISTRY, encoding="utf-8")
    (ENGINE_DIR / "value_semantic.py").write_text(VALUE_SEMANTIC, encoding="utf-8")

    text = SERVICE_PATH.read_text(encoding="utf-8")
    original = text

    import_block = (
        "from ecom_v51.import_engine.canonical_registry import ENTITY_KEY_FIELD_CANDIDATES\n"
        "from ecom_v51.import_engine.value_semantic import (\n"
        "    extract_entity_key_token,\n"
        "    infer_entity_key_from_header,\n"
        "    score_series_as_entity_key,\n"
        ")\n"
    )
    if "ENTITY_KEY_FIELD_CANDIDATES" not in text:
        if "import pandas as pd\n" in text:
            text = text.replace("import pandas as pd\n", "import pandas as pd\n\n" + import_block, 1)
        else:
            raise RuntimeError("[insert imports] could not find pandas import anchor")

    helper_anchor = "    def _build_alias_lookup(self, fields: List[dict]) -> Dict[str, str]:\n"
    if "def _apply_entity_key_rescue(" not in text:
        if helper_anchor not in text:
            raise RuntimeError("[insert helper methods] could not find _build_alias_lookup anchor")
        text = text.replace(helper_anchor, HELPER_BLOCK + "\n" + helper_anchor, 1)

    if '"entity_key": bool(entity_key_hits),' not in text:
        core_pattern = re.escape(
            '        optional_hits = [field for field in optional_pool if field in targets]\n'
            '        funnel_signal_fields = [\n'
            '            field\n'
            '            for field in [\n'
            '                "impressions_total",\n'
            '                "impressions_search_catalog",\n'
            '                "product_card_visits",\n'
            '                "add_to_cart_total",\n'
            '                "orders",\n'
            '                "order_amount",\n'
            '            ]\n'
            '            if field in targets\n'
            '        ]\n'
            '        return {\n'
            '            "sku": "sku" in targets,\n'
            '            "orders_or_order_amount": bool({"orders", "order_amount"} & targets),\n'
            '            "impressions_total": "impressions_total" in targets,\n'
            '            "impressions_total_or_search_catalog": bool({"impressions_total", "impressions_search_catalog"} & targets),\n'
            '            "product_card_visits": "product_card_visits" in targets,\n'
            '            "add_to_cart_total": "add_to_cart_total" in targets,\n'
            '            "product_card_visits_or_add_to_cart_total": bool({"product_card_visits", "add_to_cart_total"} & targets),\n'
            '            "optionalFieldPool": optional_pool,\n'
            '            "optionalHitCount": len(optional_hits),\n'
            '            "optionalHitFields": optional_hits,\n'
            '            "funnelSignalCount": len(funnel_signal_fields),\n'
            '            "funnelSignalFields": funnel_signal_fields,\n'
            '            "criticalComboComplete": all([\n'
            '                "sku" in targets,\n'
            '                bool({"orders", "order_amount"} & targets),\n'
            '                bool({"impressions_total", "impressions_search_catalog"} & targets),\n'
            '                bool({"product_card_visits", "add_to_cart_total"} & targets),\n'
            '            ]),\n'
            '            "mappedTargets": sorted(targets),\n'
            '        }\n'
        )
        core_repl = '''        optional_hits = [field for field in optional_pool if field in targets]\n        entity_key_hits = sorted(targets & set(self._entity_key_fields()))\n        funnel_signal_fields = [\n            field\n            for field in [\n                "impressions_total",\n                "impressions_search_catalog",\n                "product_card_visits",\n                "add_to_cart_total",\n                "orders",\n                "order_amount",\n            ]\n            if field in targets\n        ]\n        return {\n            "sku": "sku" in targets,\n            "entity_key": bool(entity_key_hits),\n            "entityKeyFields": entity_key_hits,\n            "orders_or_order_amount": bool({"orders", "order_amount"} & targets),\n            "impressions_total": "impressions_total" in targets,\n            "impressions_total_or_search_catalog": bool({"impressions_total", "impressions_search_catalog"} & targets),\n            "product_card_visits": "product_card_visits" in targets,\n            "add_to_cart_total": "add_to_cart_total" in targets,\n            "product_card_visits_or_add_to_cart_total": bool({"product_card_visits", "add_to_cart_total"} & targets),\n            "optionalFieldPool": optional_pool,\n            "optionalHitCount": len(optional_hits),\n            "optionalHitFields": optional_hits,\n            "funnelSignalCount": len(funnel_signal_fields),\n            "funnelSignalFields": funnel_signal_fields,\n            "criticalComboComplete": all([\n                bool(entity_key_hits),\n                bool({"orders", "order_amount"} & targets),\n                bool({"impressions_total", "impressions_search_catalog"} & targets),\n                bool({"product_card_visits", "add_to_cart_total"} & targets),\n            ]),\n            "mappedTargets": sorted(targets),\n        }\n'''
        text = replace_once(text, core_pattern, core_repl, "entity key core field summary", flags=re.S)

    if "missing_entity_key" not in text:
        text = text.replace('reasons.append("missing_sku")', 'reasons.append("missing_entity_key")')
        text = text.replace('if not core["sku"]:', 'if not core.get("entity_key"):', 1)

    bundle_pattern = re.escape(
        '        mapped_df, field_mappings = self.map_columns(df)\n'
        '        semantic_field_mappings = [item for item in field_mappings if not item.get("excludeFromSemanticGate")]\n'
    )
    if "_apply_entity_key_rescue(mapped_df, field_mappings)" not in text:
        bundle_repl = (
            '        mapped_df, field_mappings = self.map_columns(df)\n'
            '        mapped_df, field_mappings, entity_key_audit = self._apply_entity_key_rescue(mapped_df, field_mappings)\n'
            '        semantic_field_mappings = [item for item in field_mappings if not item.get("excludeFromSemanticGate")]\n'
        )
        text = replace_once(text, bundle_pattern, bundle_repl, "apply entity key rescue in bundle", flags=re.S)

    if '"entityKeyAudit": entity_key_audit,' not in text:
        text = text.replace(
            '            "fieldMappings": field_mappings,\n',
            '            "fieldMappings": field_mappings,\n            "entityKeyAudit": entity_key_audit,\n',
            1,
        )

    if '"entityKeyAudit": active_bundle.get("entityKeyAudit"),' not in text:
        text = text.replace(
            '            "fieldMappings": active_bundle["fieldMappings"],\n',
            '            "fieldMappings": active_bundle["fieldMappings"],\n            "entityKeyAudit": active_bundle.get("entityKeyAudit"),\n',
            1,
        )

    if '"importabilityStatus": "risk" if int(quarantine_count or 0) > 0 and int(imported_rows or 0) == 0 else "passed",' not in text:
        text = text.replace(
            '            "quarantineCount": quarantine_count,\n',
            '            "quarantineCount": quarantine_count,\n            "importabilityStatus": "risk" if int(quarantine_count or 0) > 0 and int(imported_rows or 0) == 0 else "passed",\n            "importabilityReasons": ["all_rows_quarantined"] if int(quarantine_count or 0) > 0 and int(imported_rows or 0) == 0 else [],\n',
            1,
        )
        text = text.replace(
            '            "finalStatus": final_status,\n',
            '            "finalStatus": "risk" if int(quarantine_count or 0) > 0 and int(imported_rows or 0) == 0 else final_status,\n',
            1,
        )
        text = text.replace(
            '            "riskOverrideReasons": risk_override_reasons,\n',
            '            "riskOverrideReasons": list(dict.fromkeys((risk_override_reasons or []) + (["all_rows_quarantined"] if int(quarantine_count or 0) > 0 and int(imported_rows or 0) == 0 else []))),\n',
            1,
        )

    if text == original:
        raise RuntimeError("no changes were applied; current file shape may differ from expected local version")

    backup_path = SERVICE_PATH.with_suffix(".py.bak_general_import_engine")
    backup_path.write_text(original, encoding="utf-8")
    SERVICE_PATH.write_text(text, encoding="utf-8")

    scripts_dir = ROOT / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    (scripts_dir / "run_general_import_matrix.py").write_text(MATRIX_SCRIPT, encoding="utf-8")

    print("Applied general import engine upgrade")
    print(f"Backup: {backup_path}")
    print(f"Updated: {SERVICE_PATH}")
    print(f"Added: {ENGINE_DIR / 'canonical_registry.py'}")
    print(f"Added: {ENGINE_DIR / 'value_semantic.py'}")
    print(f"Added: {scripts_dir / 'run_general_import_matrix.py'}")


if __name__ == "__main__":
    main()
