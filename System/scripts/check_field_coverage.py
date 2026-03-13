#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path

from ecom_v51.services.import_service import ImportService

CANONICAL_33 = [
    'sku', 'name',
    'abc_class', 'order_amount', 'order_amount_share', 'avg_sale_price',
    'impressions_total', 'impressions_search_catalog', 'impression_to_click_cvr', 'search_catalog_position_avg', 'search_catalog_to_card_cvr',
    'product_card_visits', 'add_to_cart_from_search_catalog', 'search_catalog_to_cart_cvr', 'add_to_cart_from_card', 'card_to_cart_cvr',
    'add_to_cart_total', 'add_to_cart_cvr_total', 'cart_to_order_cvr', 'order_to_purchase_cvr',
    'items_ordered', 'items_delivered', 'items_purchased', 'items_canceled', 'items_returned',
    'discount_pct', 'price_index_status', 'promo_days_count',
    'ad_revenue_rate', 'ppc_days_count',
    'review_count', 'rating_value', 'recommendation_text',
]

REASONS = {
    'abc_class': 'analysis_derived',
    'order_amount_share': 'analysis_derived',
    'avg_sale_price': 'analysis_derived_or_missing_source_col',
    'impressions_search_catalog': 'missing_source_col',
    'impression_to_click_cvr': 'analysis_derived',
    'search_catalog_position_avg': 'missing_source_col',
    'search_catalog_to_card_cvr': 'analysis_derived',
    'add_to_cart_from_search_catalog': 'missing_source_col',
    'search_catalog_to_cart_cvr': 'analysis_derived',
    'add_to_cart_from_card': 'missing_source_col',
    'card_to_cart_cvr': 'analysis_derived',
    'add_to_cart_cvr_total': 'analysis_derived',
    'cart_to_order_cvr': 'analysis_derived',
    'order_to_purchase_cvr': 'analysis_derived_or_missing_items_purchased',
    'items_delivered': 'missing_source_col_or_api_only',
    'items_purchased': 'missing_source_col_or_api_only',
    'items_canceled': 'api_or_manual_source_needed',
    'discount_pct': 'derived_from_sale_and_list_if_present',
    'price_index_status': 'api_or_external_source_needed',
    'promo_days_count': 'api_or_campaign_source_needed',
    'ad_revenue_rate': 'derived_from_ad_revenue_and_ad_spend_or_api',
    'ppc_days_count': 'api_or_campaign_source_needed',
    'recommendation_text': 'analysis_or_api_generated',
}


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    sample = root / 'sample_data' / 'p4_demo_import.csv'

    with sample.open('r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)

    svc = ImportService()
    parsed = svc.parse_import_file(str(sample), shop_id=1, operator='coverage')
    mapped = {x['standardField'] for x in parsed['fieldMappings'] if x.get('standardField')}

    mapped_in_33 = sorted([x for x in CANONICAL_33 if x in mapped])
    unmapped = sorted([x for x in CANONICAL_33 if x not in mapped])

    out = {
        'sample_file': str(sample),
        'sample_header_count': len(headers),
        'mappedCount_from_parser': parsed.get('mappedCount'),
        'canonical_33_total': len(CANONICAL_33),
        'mapped_in_canonical_33': mapped_in_33,
        'mapped_in_canonical_33_count': len(mapped_in_33),
        'unmapped_in_canonical_33_count': len(unmapped),
        'unmapped_in_canonical_33': [
            {
                'field': f,
                'reason': REASONS.get(f, 'not_in_sample_or_not_wired_yet'),
                'impact_for_trial_launch': 'high' if f in {'price_index_status', 'promo_days_count', 'items_purchased'} else 'medium',
            }
            for f in unmapped
        ],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
