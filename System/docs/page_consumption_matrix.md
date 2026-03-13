# Page Consumption Matrix

| Page | Canonical fields |
|---|---|
| Dashboard | `order_amount`, `items_ordered`, `impressions_total`, `rating_value`, `recommendation_text` |
| ABCAnalysis | `abc_class`, `order_amount`, `order_amount_share`, `avg_sale_price` |
| FunnelAnalysis | `impressions_total`, `product_card_visits`, `add_to_cart_total`, `cart_to_order_cvr`, `order_to_purchase_cvr` |
| PriceCompetitiveness | `discount_pct`, `price_index_status`, `promo_days_count`, `avg_sale_price` |
| AdsManagement | `ad_revenue_rate`, `ppc_days_count`, `impressions_total`, `impression_to_click_cvr` |
| ProfitCalculator | `order_amount`, `discount_pct`, `ad_revenue_rate` + 成本模板字段 |
| Reminder / Strategy | `recommendation_text`, `items_canceled`, `items_returned`, `price_index_status` |

## 接线说明
- 导入服务先将原始列映射到 canonical 字段（`field_aliases_zh_ru_en.yaml`）。
- 导入确认写入事实表后，上述页面继续通过既有 API 读取聚合数据。
