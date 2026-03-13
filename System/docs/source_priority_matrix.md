# API / 文件双主源优先级矩阵（收口版）

## 1) 统一策略

- 写库统一入口：
  - 文件链路：`ImportService._upsert_daily_facts`（canonical 优先 + 旧键回退）。
  - API 链路：`IntegrationService._upsert_api_rows_to_facts`（同一 fact 模型）。
- 冲突策略：`source_priority = file > api > manual_default`（同日同 SKU 发生冲突时，文件导入覆盖 API 同字段；API用于补齐文件缺失字段）。

## 2) 高价值字段双源状态

| 字段 | primary_source | secondary_source | 写入事实表 | 状态 |
|---|---|---|---|---|
| `order_amount` | file (`Revenue`) | api (`order_amount`/`revenue`) | `fact_sku_daily.revenue_ordered` + `fact_orders_daily.ordered_amount` | ✅ 双源统一 |
| `items_ordered` | file (`Orders`) | api (`items_ordered`/`orders`) | `fact_sku_daily.orders_count` + `fact_orders_daily.ordered_qty` | ✅ 双源统一 |
| `review_count` | file (`Reviews`) | api (`review_count`/`reviews`) | `fact_reviews_daily.new_reviews_count` | ✅ 双源统一 |
| `rating_value` | file (`Rating`) | api (`rating_value`/`rating`) | `fact_reviews_daily.rating_avg` | ✅ 双源统一 |
| `items_returned` | file (`Returns`) | api (`items_returned`/`returns`) | `fact_sku_daily.returned_count` + `fact_orders_daily.returned_qty` | ✅ 双源统一 |
| `items_canceled` | api | file(若存在 `items_canceled`) | `fact_sku_daily.cancelled_count` + `fact_orders_daily.cancelled_qty` | ✅ 双源统一（当前样本偏 API） |
| `promo_days_count` | api | file(若模板有列) | 当前兼容写入 `fact_ads_daily.ad_orders` 占位 | ⚠️ 已入仓但需专列 |
| `ad_revenue_rate` | api / derivation | file(若有 `ad_revenue_rate`) | `fact_ads_daily.roas` | ✅ 双源统一 |

## 3) 仍未完成双源统一的字段（33口径）

- `price_index_status`：需要外部市场比价 API 或专用文件列。
- `ppc_days_count`：需要广告活动日历源。
- `items_purchased` / `items_delivered`：需履约 API 持续回流或文件新增列。
