# 字段 -> 事实表 -> 页面对照矩阵（最终收口）

> 口径：以 `sample_data/p4_demo_import.csv` 的 17 个已映射字段为基线；写库口径来自 `ImportService._upsert_daily_facts`（canonical 优先，旧键兼容）。

## A. 17 个已映射字段全链路

| 导入字段（样本列） | canonical/兼容键 | 事实表落点 | 页面/分析消费 |
|---|---|---|---|
| SKU | `sku` | `dim_sku.sku` | 全页面通过 SKU 维度聚合（Dashboard/ABC/Funnel/Price/Ads/Strategy） |
| Name | `name` | `dim_sku.sku_name` | 页面展示 SKU 名称（策略、分析列表） |
| Impressions | `impressions_total` \\| `impressions` | `fact_sku_daily.impressions_total` | Dashboard 总曝光、Funnel CTR、Ads CTR 口径 |
| Card visits | `product_card_visits` \\| `card_visits` \\| `visits` | `fact_sku_daily.card_visits` | Dashboard totalClicks/avgCtr、Funnel cardVisits |
| Add to Cart | `add_to_cart_total` \\| `add_to_cart` | `fact_sku_daily.add_to_cart_total` | Funnel addToCart/addRate |
| Orders | `items_ordered` \\| `orders` | `fact_sku_daily.orders_count`、`fact_orders_daily.ordered_qty` | Dashboard totalOrders、Funnel orders、ABC orders |
| Revenue | `order_amount` \\| `revenue` | `fact_sku_daily.revenue_ordered`、`fact_orders_daily.ordered_amount` | Dashboard totalRevenue/avgOrderValue、ABC revenue |
| Rating | `rating_value` \\| `rating` | `fact_reviews_daily.rating_avg` | Dashboard avgRating、ABC rating、Reminder质量风险 |
| Reviews | `review_count` \\| `reviews` | `fact_reviews_daily.new_reviews_count` | Reminder 新评价、质量相关分析 |
| Returns | `items_returned` \\| `returns` | `fact_sku_daily.returned_count`、`fact_orders_daily.returned_qty` | ABC returnRate、Reminder 售后风险 |
| Stock | `stock_total` \\| `stock` | `fact_inventory_daily.stock_total` | Inventory / Dashboard 衍生库存风险 |
| Ad spend | `ad_spend` | `fact_ads_daily.ad_spend` | Ads totalSpend、Price/Ads ROAS |
| Ad orders | `ad_orders` | `fact_ads_daily.ad_orders` | Ads 订单贡献口径 |
| sale_price | `sale_price` | `fact_profit_snapshot.sale_price` | PriceCompetitiveness/ProfitCalculator |
| list_price | `list_price` | `fact_profit_snapshot.list_price` | PriceCompetitiveness/ProfitCalculator |
| cost_price | `cost_price` | `fact_profit_snapshot.fixed_cost_total`（兼容落点） | ProfitCalculator 成本基线 |
| commission_rate | `commission_rate` | `fact_profit_snapshot.variable_rate_total`（兼容落点） | ProfitCalculator 费率基线 |

## B. 页面关键卡片 -> canonical -> fact 字段

| 页面 | 关键卡片/模块 | canonical 字段 | fact 字段 |
|---|---|---|---|
| Dashboard | 总营收 | `order_amount` | `fact_sku_daily.revenue_ordered` |
| Dashboard | 订单总数 | `items_ordered` | `fact_sku_daily.orders_count` |
| Dashboard | 客单价 | `order_amount`,`items_ordered` | `revenue_ordered / orders_count` |
| Dashboard | 平均毛利率 | （利润快照衍生） | `fact_profit_snapshot.net_profit` + `fact_sku_daily.revenue_ordered` |
| ABCAnalysis | 营收/订单/毛利/ABC | `order_amount`,`items_ordered`,`abc_class`(衍生) | `fact_sku_daily.revenue_ordered`,`orders_count`,`fact_profit_snapshot.net_margin` |
| FunnelAnalysis | 展示-访问-加购-下单 | `impressions_total`,`product_card_visits`,`add_to_cart_total`,`items_ordered` | `fact_sku_daily.impressions_total`,`card_visits`,`add_to_cart_total`,`orders_count` |
| PriceCompetitiveness | 我方价/市场价/价差/毛利/ROAS | `sale_price`,`list_price`,`ad_revenue_rate`(兼容ROAS) | `fact_profit_snapshot.sale_price/list_price/net_margin`,`fact_ads_daily.roas` |
| AdsManagement | 总花费/广告收入/ROAS | `ad_spend`,`ad_revenue_rate` | `fact_ads_daily.ad_spend/ad_revenue/roas` |
| ProfitCalculator | 自动回填参数 | `sale_price`,`list_price`,`commission_rate` 等 | `integrationApi.getPricingAutofill` + `fact_profit_snapshot` 快照回放 |
| Reminder/Strategy | 评价/退货/取消风险与动作 | `review_count`,`rating_value`,`items_returned`,`items_canceled` | `fact_reviews_daily`,`fact_orders_daily`,`strategy_task` |
