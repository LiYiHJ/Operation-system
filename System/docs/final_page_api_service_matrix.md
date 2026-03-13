# 页面 / API / Service / Fact 回归矩阵（最终验收复核）

| 页面 | 前端 API 调用 | 后端路由 | Service | 事实层依赖 | 当前判断 |
|---|---|---|---|---|---|
| Dashboard | `/dashboard/overview` `/dashboard/top-skus` `/dashboard/alerts` `/dashboard/trends` `/dashboard/shop-health` | `api/routes/dashboard.py` | `DashboardService` | `fact_*` 聚合 | 有条件通过（主库空导致空态） |
| ABC | `/analysis/abc` | `api/routes/analysis.py` | `AnalysisService` | `fact_orders_daily` 等 | 有条件通过 |
| Funnel | `/analysis/funnel` | `api/routes/analysis.py` | `AnalysisService` | `fact_sku_daily` | 有条件通过 |
| Price | `/analysis/price-cockpit`（兼容 `/analysis/price`）`/analysis/action-to-strategy` | `api/routes/analysis.py` | `AnalysisService` | `fact_sku_daily` + `fact_sku_ext_daily` | 有条件通过 |
| Ads | `/ads/campaigns` | `api/routes/ads.py` | `Analysis/Ads service` | `fact_ads_daily` | 有条件通过 |
| Reminder | `/reminders/list` | `api/routes/reminder.py` | `Reminder service` | 多事实聚合 | 有条件通过 |
| Strategy | `/strategy/list` `/strategy/task/:id/status` | `api/routes/strategy.py` | `StrategyTaskService` | `strategy_task` `execution_log` | 通过（测试环境） |
| Decision | `/strategy/decision/preview` `/strategy/decision/confirm` | `api/routes/strategy.py` | `StrategyTaskService` | `strategy_task` `execution_log` `report_snapshot` | 通过（测试环境） |
| Settings / Integration | `/integration/data-source` `/integration/permission-check` `/integration/sync-once` `/integration/push-sales` `/integration/push-logs` | `api/routes/integration.py` | `IntegrationService` | `external_data_source_config` `sync_run_log` `push_delivery_log` | 有条件通过（真实外部联通证据不足） |
