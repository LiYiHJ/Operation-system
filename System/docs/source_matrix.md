# Source Matrix（来源矩阵）

| canonical_field | primary_source | secondary_source | source_priority |
|---|---|---|---|
| abc_class | file | api | file > api > manual |
| order_amount | file | api | file > api > manual |
| order_amount_share | file | - | file > manual |
| avg_sale_price | file | api | file > api > manual |
| impressions_total | file | api | file > api |
| impressions_search_catalog | file | - | file |
| impression_to_click_cvr | file | api | file > api |
| search_catalog_position_avg | file | - | file |
| search_catalog_to_card_cvr | file | - | file |
| product_card_visits | file | api | file > api |
| add_to_cart_from_search_catalog | file | - | file |
| search_catalog_to_cart_cvr | file | - | file |
| add_to_cart_from_card | file | api | file > api |
| card_to_cart_cvr | file | api | file > api |
| add_to_cart_total | file | api | file > api |
| add_to_cart_cvr_total | file | api | file > api |
| cart_to_order_cvr | file | api | file > api |
| order_to_purchase_cvr | file | api | file > api |
| items_ordered | api | file | api > file |
| items_delivered | api | file | api > file |
| items_purchased | api | file | api > file |
| items_canceled | api | file | api > file |
| items_returned | api | file | api > file |
| discount_pct | file | api | file > api |
| price_index_status | file | api | file > api |
| promo_days_count | file | api | file > api |
| ad_revenue_rate | file | api | file > api |
| ppc_days_count | file | api | file > api |
| review_count | api | file | api > file |
| rating_value | api | file | api > file |
| recommendation_text | file | api | file > api > manual |

备注：
- 模板/手工主来源：采购成本、包材人工、固定成本、履约成本模板、店铺默认参数、SKU 覆盖参数。
