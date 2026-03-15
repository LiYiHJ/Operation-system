
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(r"C:\Operation-system\System")
IMPORT_SERVICE = REPO_ROOT / "src" / "ecom_v51" / "services" / "import_service.py"
IMPORT_ENGINE_DIR = REPO_ROOT / "src" / "ecom_v51" / "import_engine"
CANONICAL_REGISTRY = IMPORT_ENGINE_DIR / "canonical_registry.py"
VALUE_SEMANTIC = IMPORT_ENGINE_DIR / "value_semantic.py"

CANONICAL_REGISTRY_CONTENT = textwrap.dedent("""\
from __future__ import annotations

ENTITY_KEY_FIELD_CANDIDATES = [
    "sku",
    "seller_sku",
    "offer_id",
    "product_id",
    "item_id",
    "asin",
    "ean",
    "barcode",
]
""")

VALUE_SEMANTIC_CONTENT = textwrap.dedent("""\
from __future__ import annotations

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
    text = text.replace("\\u3000", " ")
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
""")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[{label}] expected 1 match, got {count}")
    return text.replace(old, new, 1)

def main() -> None:
    import textwrap

    if not IMPORT_SERVICE.exists():
        raise FileNotFoundError(f"import_service.py not found: {IMPORT_SERVICE}")

    IMPORT_ENGINE_DIR.mkdir(parents=True, exist_ok=True)
    CANONICAL_REGISTRY.write_text(CANONICAL_REGISTRY_CONTENT, encoding="utf-8")
    VALUE_SEMANTIC.write_text(VALUE_SEMANTIC_CONTENT, encoding="utf-8")

    backup = IMPORT_SERVICE.with_suffix(".py.bak_entity_key_hotfix_v3")
    if not backup.exists():
        backup.write_text(IMPORT_SERVICE.read_text(encoding="utf-8"), encoding="utf-8")

    text = IMPORT_SERVICE.read_text(encoding="utf-8")

    direct_call = '        mapped_df, field_mappings, entity_key_audit = self._apply_entity_key_rescue(mapped_df, field_mappings)\n'
    guarded_call = textwrap.dedent("""\
        try:
            mapped_df, field_mappings, entity_key_audit = self._apply_entity_key_rescue(mapped_df, field_mappings)
        except Exception as exc:
            entity_key_audit = {
                "detected": False,
                "field": None,
                "sourceHeader": None,
                "detectedBy": "entity_key_rescue_error",
                "confidence": 0.0,
                "sampleToken": None,
                "candidateHeaders": [],
                "error": f"entity_key_rescue_failed: {exc}",
            }
""")
    text = replace_once(text, direct_call, guarded_call, "guard entity key rescue")

    text = replace_once(
        text,
        '        if not core["sku"] and not clean_strong_bundle_without_sku:\n',
        '        if not core["entity_key"] and not clean_strong_bundle_without_sku:\n',
        "use entity_key in semantic gate",
    )

    IMPORT_SERVICE.write_text(text, encoding="utf-8")
    print("Applied entity key hotfix v3")
    print(f"- wrote {CANONICAL_REGISTRY}")
    print(f"- wrote {VALUE_SEMANTIC}")
    print(f"- patched {IMPORT_SERVICE}")
    print(f"- backup at {backup}")

if __name__ == "__main__":
    main()
