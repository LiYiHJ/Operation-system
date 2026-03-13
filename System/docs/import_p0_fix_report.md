# 导入模块 P0 最终验收表（统计口径 + 覆盖率 + 回归）

## 1) 映射统计口径统一说明

> 问题背景：页面出现过“总字段数 14、已映射 12、未映射 61、文件字段数 73”这类看起来矛盾的数字。

### 统一后定义

- **原始字段数（rawColumns）**：文件读入后、规范化前的列数。用于说明文件本体复杂度。
- **候选字段数（candidateColumns）**：参与映射统计的字段数（排除动态列如 `Динамика*`）。
- **已映射（mappedCount）**：候选字段中，已有 `standardField` 的数量。
- **未映射（unmappedCount）**：候选字段中，尚未映射的数量。
- **忽略列数（ignoredColumns）**：被判定为动态/趋势辅助列，不纳入映射覆盖统计。
- **映射覆盖率（mappingCoverage）**：`mappedCount / candidateColumns`。
- **映射置信度（mappedConfidence）**：仅对“已映射字段”取平均置信度。

### 为什么之前会误导

- 旧口径把“全字段平均置信度”当主指标（包含大量应忽略列），导致出现 14.3% 这类误导性低分。
- 新口径把“覆盖率”和“已映射置信度”分开展示，用户更容易理解当前可用程度。

---

## 2) 真实 Ozon 报表映射覆盖率提升（不破坏回归）

本轮针对 Ozon analytics 报表补充了高价值字段映射（不扩散到其他模块）：

- 订单金额/订单量：`order_amount`, `items_ordered`, `items_delivered`, `items_purchased`
- 售后/取消：`items_canceled`, `items_returned`
- 广告：`ad_spend`（`Общая ДРР`）
- 库存：`stock_total`
- 类目：`category`（1/2/3级）
- 价格与活动：`avg_sale_price`, `price_index_status`, `promo_days_count`
- 流量核心：`impressions_total`, `impressions_search_catalog`, `product_card_visits`, `add_to_cart_total`

并保持 `sample_data/p4_demo_import.csv` 指标不退化。

---

## 3) 修复前后映射对比

### 3.1 真实失败文件 A
文件：`20260308_142700_analytics_report_2026-03-06_03_58.xlsx`

| 指标 | 修复前（旧逻辑复算） | 修复后 |
|---|---:|---:|
| 原始字段数 | 73 | 73 |
| 规范化后字段数 | 73 | 73 |
| 候选字段数 | 73 | 47 |
| 忽略列数（动态列） | 0 | 26 |
| 已映射 | 2 | 26 |
| 未映射 | 71 | 21 |
| 映射覆盖率 | 2.7% | 55.3% |
| 置信度（旧：全字段均值） | 0.026 | - |
| 置信度（新：已映射字段均值） | - | 0.945 |
| Unnamed 列数 | 61 | 0 |
| headerRow | 10 | 10（与后端真实读取一致） |

### 3.2 真实文件 B（新增验证）
文件：`20260308_151026_analytics_report_2026-03-06_03_58.xlsx`

| 指标 | 修复前（旧逻辑复算） | 修复后 |
|---|---:|---:|
| 原始字段数 | 73 | 73 |
| 候选字段数 | 73 | 47 |
| 忽略列数（动态列） | 0 | 26 |
| 已映射 | 2 | 26 |
| 未映射 | 71 | 21 |
| 映射覆盖率 | 2.7% | 55.3% |
| 已映射字段平均置信度 | - | 0.945 |
| Unnamed 列数 | 61 | 0 |
| headerRow | 10 | 10 |

---

## 4) 被剔除字段/行清单

### 4.1 被剔除列
- `Unnamed:*` 占位列：在 parse 规范化阶段剔除。

### 4.2 被剔除行
- 说明行：2 行（报表字段解释行）。
- 汇总行：1 行（如 `Итого и среднее` / 总计和平均值）。

### 4.3 被忽略动态列
- `Динамика`, `Динамика_1`, `Динамика_2`, ...（共 26 列）
- 处理策略：保留在原始预览但不计入候选映射统计，避免干扰覆盖率。

---

## 5) 最终进入 confirm_import 的字段清单（示例）

本轮真实文件中可入库的关键标准字段（去重后 21 个）：

`ad_spend, add_to_cart_cvr_total, add_to_cart_total, avg_sale_price, category, impressions_search_catalog, impressions_total, items_canceled, items_delivered, items_ordered, items_purchased, items_returned, order_amount, price_index_status, product_card_visits, promo_days_count, rating_value, recommendation_text, review_count, sku, stock_total`

---

## 6) confirm_import 与事实表结果

- confirm_import：`status=success`, `importedRows=1505`, `errorRows=0`。
- 导入后 6 张事实表非零：
  - `fact_sku_daily`
  - `fact_orders_daily`
  - `fact_reviews_daily`
  - `fact_ads_daily`
  - `fact_inventory_daily`
  - `fact_profit_snapshot`

---

## 7) 回归样本结果（不得退化）

文件：`sample_data/p4_demo_import.csv`

| 指标 | 结果 |
|---|---:|
| mappedCount | 17 |
| unmappedCount | 0 |
| candidateColumns | 17 |
| ignoredColumns | 0 |
| mappingCoverage | 100% |
| mappedConfidence | 0.95 |
| headerRow | 1 |

---

## 8) 页面体验改动说明（导入页）

导入页已改为展示并解释：
- 候选字段数 / 已映射 / 未映射
- 映射覆盖率（主指标）
- 映射置信度（已映射字段）
- 原始字段数、规范化后字段数
- 剔除说明/汇总行数量、剔除占位列数量

这样可避免“14.3%”这类误导性指标让用户误判导入质量。
