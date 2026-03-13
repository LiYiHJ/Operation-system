# 价格页真实打通验收表（DB → Service → API → 页面）

## 1) 数据库层证据

### 1.1 扩展事实表高影响字段非零
- 表：`fact_sku_ext_daily`
- 聚合结果（实测）：
  - 总行数：1511
  - `items_purchased != 0`：244
  - `promo_days_count != 0`：2
  - `discount_pct != 0`：2
  - `price_index_status` 非空：3

### 1.2 与价格分析主事实表的 join key 一致性
- 价格分析主事实：`fact_profit_snapshot`
- 扩展事实：`fact_sku_ext_daily`
- join key：`shop_id + sku_id + date_id`
- join 命中：1511 / 1511（100%）
- 平台口径：通过 `fact_* -> dim_shop(platform_id) -> dim_platform(platform_code)` 可溯源到 `ozon`。

## 2) Service 层证据

### 2.1 是否真实读取新字段
`AnalysisService.price_cockpit` 已真实 join 并读取：
- `items_purchased`
- `promo_days_count`
- `discount_pct`
- `price_index_status`

### 2.2 这些字段参与的计算（非仅透传）
- 分组规则：
  - `traffic`：排除 `price_index_status == RED`
  - `standard_margin`：要求 `promo_days_count <= 3`
  - `high_margin`：要求 `discount_pct <= 0.1`
  - `clearance`：额外约束 `items_purchased <= 5`
  - `campaign`：要求 `promo_days_count > 0`
- 推荐逻辑：
  - `campaign` 视图下结合 `promo_days_count` 与 `margin`
  - `promo` 视图下结合 `discount_pct`
  - 日常视图下结合 `price_index_status + priceGap`
- summary 指标：新增
  - `avgDiscountPct`
  - `avgPromoDays`
  - `redPriceIndexCount`

## 3) API 层证据

### 3.1 `/api/analysis/price-cockpit` 真实样例
见：`System/docs/price_cockpit_api_sample.json`

关键结果（非占位）：
- `summary.totalSku = 200`
- `summary.avgMargin = 0.784`
- `summary.avgDiscountPct = 0.001`
- `summary.avgPromoDays = 0.04`
- `groupedStrategies` 非默认全 0（`standard_margin=196`, `high_margin=4`）
- `batchRecommendations` 非空且包含新字段（`itemsPurchased/promoDaysCount/discountPct/priceIndexStatus`）

### 3.2 为什么此前会出现“顶部 4 指标为 0，但图表有分区”
根因是价格服务 SQL 在过滤前先 `limit(200)`，截到大量“全零行”，导致 summary 接近 0；
但图表分区仍会按规则把这些行归到某个组（例如 `clearance`），于是出现“指标近 0 + 分区有图形”的视觉冲突。

本次最小修复：
- 先全量取数并在服务层剔除“核心指标全零”的脏行，再截断到 200；
- 让 summary/grouping/rows 使用同一批有效样本。

## 4) 页面层证据

- Network 抓包样例：
  - `browser:/tmp/codex_browser_invocations/396e0006c443c1b9/artifacts/artifacts/price_page_network_sample.json`
- 页面截图：
  - `browser:/tmp/codex_browser_invocations/396e0006c443c1b9/artifacts/artifacts/price_page_real_pipeline.png`

页面绑定核查结论：
- 顶部卡片绑定 `data.summary`；
- 分区图绑定 `rows` 和 `groupedStrategies`；
- 当前已收敛为同一批有效数据，避免“summary 与图表口径分裂”。
