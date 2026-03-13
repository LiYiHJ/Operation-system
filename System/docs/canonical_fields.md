# Canonical Fields（标准字段层）

本系统统一以标准字段作为页面消费层，API/文件原始字段仅在导入阶段存在。

## 业务域与字段
- 销售结构域：`abc_class`, `order_amount`, `order_amount_share`, `avg_sale_price`
- 流量曝光域：`impressions_total`, `impressions_search_catalog`, `impression_to_click_cvr`, `search_catalog_position_avg`, `search_catalog_to_card_cvr`
- 漏斗转化域：`product_card_visits`, `add_to_cart_from_search_catalog`, `search_catalog_to_cart_cvr`, `add_to_cart_from_card`, `card_to_cart_cvr`, `add_to_cart_total`, `add_to_cart_cvr_total`, `cart_to_order_cvr`, `order_to_purchase_cvr`
- 履约售后域：`items_ordered`, `items_delivered`, `items_purchased`, `items_canceled`, `items_returned`
- 价格促销域：`discount_pct`, `price_index_status`, `promo_days_count`
- 广告域：`ad_revenue_rate`, `ppc_days_count`
- 评价建议域：`review_count`, `rating_value`, `recommendation_text`

## 落地原则
1. 页面不依赖原始表头；统一读标准字段。
2. API 数据与文件数据进入同一标准字段层，再写入事实模型。
3. 不同平台/语言通过别名字典归一。
