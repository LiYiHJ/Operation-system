# 导入统计口径与契约 P0 收口记录

## 1) 导入页统计口径统一

### 历史问题（截图反馈）
- 候选字段 47
- 已映射 9
- 未映射 0
- 覆盖率 55.3%

上述四项不能同时成立，根因是前端“已映射/未映射/覆盖率”在不同分支使用了不同分母与过滤口径。

### 新口径（统一）
- candidateColumns = 排除 ignored/dynamic 后的字段数
- mappedCount = candidate 中 standardField 非空且不为 `unmapped`
- unmappedCount = candidateColumns - mappedCount
- mappingCoverage = mappedCount / candidateColumns
- mappedConfidence = 已映射字段的平均置信度

## 2) 后端/前端一致性样例

样例文件：
- `System/src/uploads/20260308_142700_analytics_report_2026-03-06_03_58.xlsx`
- `System/sample_data/p4_demo_import.csv`

已写入：`System/docs/import_stats_consistency_samples.json`

关键结果：
- real file: candidate=47, mapped=26, unmapped=21, coverage=0.553
- regression sample: candidate=17, mapped=17, unmapped=0, coverage=1.0

## 3) API 契约兼容 P0（最小改动）
- dashboard 兼容别名：
  - `/api/dashboard/top-skus`
  - `/api/dashboard/alerts`
  - `/api/dashboard/trends`
  - `/api/dashboard/shop-health`
- analysis 兼容：
  - `/api/analysis/price` -> 复用 `price-cockpit`
- ads 兼容：
  - `/api/ads/campaigns`
  - `/api/ads/campaign/<id>`
- strategy 兼容：
  - `/api/strategy/generate/<sku>`
  - `/api/strategy/batch`
  - `/api/strategy/decision`
  - `/api/strategy/task/<id>/status`

接口样例输出：`System/docs/api_contract_p0_samples.json`

## 4) 高影响字段闭环（P0/P1 最小落点）
新增 `fact_sku_ext_daily`（扩展事实表）承接：
- `items_purchased`
- `promo_days_count`
- `discount_pct`
- `price_index_status`

当前写入链路：
- 导入 confirm 入库写入扩展事实表
- integration API 同步写入扩展事实表
- analysis/price(-cockpit) 输出扩展字段（用于页面追踪）

## 5) 页面追踪
- 导入页：统计口径说明卡片与顶部指标统一
- 价格页：批量推荐表新增 `购买件数/活动天数/折扣率/价格指数状态`
