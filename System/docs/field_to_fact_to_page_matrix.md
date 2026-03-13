# 字段 -> 事实表 -> 页面对照矩阵（自跑通验收版）

> 本表只写“真实代码已消费链路”，不写规划字段。

## 1) Dashboard

| 指标 | canonical 字段 | fact 字段 | 计算口径 | 来源优先级 |
|---|---|---|---|---|
| `totalRevenue` | `order_amount` | `fact_sku_daily.revenue_ordered` | `sum(revenue_ordered)` | file > api |
| `totalOrders` | `items_ordered` | `fact_sku_daily.orders_count` | `sum(orders_count)` | file > api |
| `avgRating` | `rating_value` | `fact_reviews_daily.rating_avg` | `avg(rating_avg)` | api/file |
| `avgCtr` | `impressions_total` + `product_card_visits` | `fact_sku_daily.impressions_total/card_visits` | `sum(card_visits)/sum(impressions_total)` | file |

## 2) FunnelAnalysis

| 指标 | canonical 字段 | fact 字段 | 计算口径 |
|---|---|---|---|
| `impressions` | `impressions_total` | `fact_sku_daily.impressions_total` | `sum(impressions_total)` |
| `cardVisits` | `product_card_visits` | `fact_sku_daily.card_visits` | `sum(card_visits)` |
| `addToCart` | `add_to_cart_total` | `fact_sku_daily.add_to_cart_total` | `sum(add_to_cart_total)` |
| `orders` | `items_ordered` | `fact_sku_daily.orders_count` | `sum(orders_count)` |

## 3) ABCAnalysis

| 指标 | canonical 字段 | fact 字段 | 计算口径 |
|---|---|---|---|
| `revenue` | `order_amount` | `fact_sku_daily.revenue_ordered` | `sum(revenue_ordered)` |
| `orders` | `items_ordered` | `fact_sku_daily.orders_count` | `sum(orders_count)` |
| `margin` | （利润快照衍生） | `fact_profit_snapshot.net_margin` | `avg(net_margin)` |
| `abcClass` | `abc_class`（分析衍生） | 基于 `revenue_ordered` 排序占比 | 累积营收占比 A/B/C |

## 4) PriceCompetitiveness

| 指标 | canonical 字段 | fact 字段 | 计算口径 |
|---|---|---|---|
| `ourPrice` | `sale_price` | `fact_profit_snapshot.sale_price` | `avg(sale_price)` |
| `marketPrice` | `list_price` | `fact_profit_snapshot.list_price` | `avg(list_price)` |
| `margin` | （利润衍生） | `fact_profit_snapshot.net_margin` | `avg(net_margin)` |
| `roas` | `ad_revenue_rate`（兼容） | `fact_ads_daily.roas` | `avg(roas)` |
| `promoMargin` | `discount_pct`（未直连） | 当前无专列 | **未闭环：由售价/原价间接估算** |

## 5) AdsManagement

| 指标 | canonical 字段 | fact 字段 | 计算口径 |
|---|---|---|---|
| `adSpend` | `ad_spend` | `fact_ads_daily.ad_spend` | `sum(ad_spend)` |
| `adRevenue` | （广告收入衍生） | `fact_ads_daily.ad_revenue` | `sum(ad_revenue)` |
| `roas` | `ad_revenue_rate`（兼容） | `fact_ads_daily.roas` | `avg(roas)` |

## 6) ProfitCalculator

| 页面项 | canonical 字段 | 事实/接口来源 | 当前状态 |
|---|---|---|---|
| 当前利润 | `sale_price/list_price/commission_rate/cost_price` | `fact_profit_snapshot` + `profit_api.solve` | 已接通 |
| 建议售价 | 同上 + 费率成本层 | `profit_api.solve` | 已接通 |
| 风险项 | `items_returned/items_canceled/ad_revenue_rate`（参数化） | 通过 `return_loss_cost/cancel_loss_cost/ads_rate` 进入求解 | 部分接通 |
| 自动回填项 | `sale_price/list_price` + 费率模板 | `integration/pricing-autofill` | 已接通 |
| 评价/活动风险 | `rating_value/review_count/promo_days_count/price_index_status` | 无直接卡片映射 | 未接通（不阻塞试运行） |

## 7) Reminder / Strategy

| 指标 | canonical 字段 | fact 字段 | 口径 |
|---|---|---|---|
| `new_orders` | `items_ordered` | `fact_orders_daily.ordered_qty` | `sum(ordered_qty)` |
| `new_reviews` | `review_count` | `fact_reviews_daily.new_reviews_count` | `sum(new_reviews_count)` |
| 风险/告警输入 | `rating_value/items_returned/items_canceled` + 业务事件 | `fact_reviews_daily` + `fact_orders_daily` + `alert_event` + `strategy_task` | 提醒与策略优先级 |

## 8) 17 已映射字段主链路（导入 -> fact）

`SKU`,`Name`,`Impressions`,`Card visits`,`Add to Cart`,`Orders`,`Revenue`,`Rating`,`Reviews`,`Returns`,`Stock`,`Ad spend`,`Ad orders`,`sale_price`,`list_price`,`cost_price`,`commission_rate`
均可在导入 confirm 后写入对应事实层（dim/fact）。
