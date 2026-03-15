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
    re.compile(r"(?i)\b[A-Z0-9]{2,}[\-_][A-Z0-9\-_]{2,}\b"),
    re.compile(r"\b\d{8,14}\b"),
]

def _norm(value: object) -> str:
    text = str(value or "").strip()
    text = text.replace("　", " ")
    text = re.sub(r"\s+", " ", text)
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
