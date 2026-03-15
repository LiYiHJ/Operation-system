from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(r"C:\Operation-system\System")
IMPORT_SERVICE = REPO_ROOT / "src" / "ecom_v51" / "services" / "import_service.py"
VALUE_SEMANTIC = REPO_ROOT / "src" / "ecom_v51" / "import_engine" / "value_semantic.py"

VALUE_SEMANTIC_CONTENT = '''from __future__ import annotations

import re
from typing import Iterable, Optional

ENTITY_KEY_HEADER_HINTS = {
    "sku": [
        "sku",
        "seller_sku",
        "offer_id",
        "offer id",
        "product_id",
        "product id",
        "item_id",
        "item id",
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
        "Артикул",
        "Артикул продавца",
        "Код товара",
        "Offer ID",
    ],
    "offer_id": ["offer_id", "offer id", "Offer ID"],
    "asin": ["asin"],
    "ean": ["ean"],
    "barcode": ["barcode", "条码"],
}

ENTITY_KEY_TOKEN_PATTERNS = [
    re.compile(r"(?i)\\b[A-Z0-9]{2,}[\\-_][A-Z0-9\\-_]{2,}\\b"),
    re.compile(r"\\b\\d{8,14}\\b"),
]

def _norm(value: object) -> str:
    text = str(value or "").strip()
    text = text.replace("\u3000", " ")
    text = re.sub(r"\\s+", " ", text)
    return text

def infer_entity_key_from_header(header: object) -> Optional[str]:
    text = _norm(header).lower()
    if not text:
        return None
    for field, hints in ENTITY_KEY_HEADER_HINTS.items():
        for hint in hints:
            if hint.lower() in text:
                return field
    return None

def extract_entity_key_token(value: object) -> Optional[str]:
    text = _norm(value)
    if not text:
        return None
    for pattern in ENTITY_KEY_TOKEN_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(0)
    return None

def score_series_as_entity_key(values: Iterable[object], header: object = "") -> float:
    header_field = infer_entity_key_from_header(header)
    score = 0.0
    if header_field:
        score += 0.45

    tokens = []
    digit_like = 0
    total = 0
    for value in values or []:
        total += 1
        token = extract_entity_key_token(value)
        if token:
            tokens.append(token)
            if token.isdigit():
                digit_like += 1

    if total == 0:
        return min(score, 1.0)

    hit_ratio = len(tokens) / total
    score += min(hit_ratio * 0.6, 0.45)

    if tokens:
        unique_ratio = len(set(tokens)) / len(tokens)
        score += min(unique_ratio * 0.15, 0.15)

    if digit_like and digit_like == len(tokens):
        score += 0.05

    return round(min(score, 0.99), 4)
'''

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[{label}] expected 1 match, got {count}")
    return text.replace(old, new, 1)

def main() -> None:
    if not IMPORT_SERVICE.exists():
        raise FileNotFoundError(f"import_service.py not found: {IMPORT_SERVICE}")

    VALUE_SEMANTIC.parent.mkdir(parents=True, exist_ok=True)

    backup = IMPORT_SERVICE.with_suffix(".py.bak_entity_key_hotfix_v2")
    if not backup.exists():
        backup.write_text(IMPORT_SERVICE.read_text(encoding="utf-8"), encoding="utf-8")

    VALUE_SEMANTIC.write_text(VALUE_SEMANTIC_CONTENT, encoding="utf-8")

    text = IMPORT_SERVICE.read_text(encoding="utf-8")

    text = replace_once(
        text,
        '"finalStatus": "risk" if int(quarantine_count or 0) > 0 and int(imported_rows or 0) == 0 else final_status,',
        '"finalStatus": final_status,',
        "revert build_bundle finalStatus",
    )
    text = replace_once(
        text,
        '"riskOverrideReasons": list(dict.fromkeys((risk_override_reasons or []) + (["all_rows_quarantined"] if int(quarantine_count or 0) > 0 and int(imported_rows or 0) == 0 else []))),',
        '"riskOverrideReasons": risk_override_reasons,',
        "revert build_bundle riskOverrideReasons",
    )

    old = '"entityKeyAudit": active_bundle.get("entityKeyAudit"),'
    new = '''"entityKeyAudit": active_bundle.get("entityKeyAudit"),
            "finalStatus": "risk" if int(imported_rows or 0) == 0 and int(quarantine_count or 0) > 0 else final_status,
            "riskOverrideReasons": list(dict.fromkeys((risk_override_reasons or []) + (["all_rows_quarantined"] if int(imported_rows or 0) == 0 and int(quarantine_count or 0) > 0 else []))),'''
    text = replace_once(text, old, new, "inject response-level quarantine risk")

    IMPORT_SERVICE.write_text(text, encoding="utf-8")

    print("Applied entity key hotfix v2")
    print(f"- wrote {VALUE_SEMANTIC}")
    print(f"- patched {IMPORT_SERVICE}")
    print(f"- backup at {backup}")

if __name__ == "__main__":
    main()
