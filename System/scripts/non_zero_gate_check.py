#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
from sqlalchemy import create_engine, text

DB_PATH = Path(__file__).resolve().parents[1] / 'data' / 'ecom_v51.db'
engine = create_engine(f'sqlite:///{DB_PATH}')

tables = [
    'fact_sku_daily','fact_orders_daily','fact_reviews_daily','fact_ads_daily','fact_inventory_daily',
    'fact_profit_snapshot','fact_sku_ext_daily','strategy_task','execution_log','push_delivery_log'
]
with engine.connect() as conn:
    counts = {}
    for t in tables:
        try:
            counts[t] = conn.execute(text(f'SELECT COUNT(*) FROM {t}')).scalar()
        except Exception:
            counts[t] = 0
    gate = {t: (counts[t] > 0) for t in tables}
    output = {
        'db': str(DB_PATH),
        'counts': counts,
        'gatePassByTable': gate,
        'allPass': all(gate.values())
    }

print(json.dumps(output, ensure_ascii=False, indent=2))
