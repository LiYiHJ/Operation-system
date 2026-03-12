# 多页面与数据样本联调测试报告（补充）

## 1. 数据样本初始化
执行：

```bash
PYTHONPATH=src python scripts/seed_operational_demo.py
```

结果摘要：
- SKU: 6
- FactSkuDaily: 42
- FactProfitSnapshot: 42
- FactInventoryDaily: 42
- FactAdsDaily: 42
- FactOrdersDaily: 42
- FactReviewsDaily: 42
- StrategyTask: 5
- ExecutionLog: 2
- Alerts: 3

## 2. 数据库样本计数校验
通过 SQLAlchemy 对关键表计数，确认导入与样本链路生效：
- ImportBatch / DimSku / FactSkuDaily / FactProfitSnapshot / FactInventoryDaily
- FactAdsDaily / FactOrdersDaily / FactReviewsDaily
- StrategyTask / ExecutionLog / AlertEvent

## 3. API 多页面联调（含数据返回结构）
测试端点（均返回 200）：
- `/api/dashboard/overview`
- `/api/analysis/price-cockpit?shopId=1&days=7&view=daily`
- `/api/profit/profiles`
- `/api/profit/solve`
- `/api/analysis/inventory?shopId=1&days=7`
- `/api/analysis/funnel?shopId=1&days=7`
- `/api/analysis/ads?shopId=1&days=7`
- `/api/analysis/abc?shopId=1&days=7`
- `/api/strategy/list`
- `/api/strategy/decision/preview`
- `/api/reminders/list?shopId=1`

## 4. 页面可视化联调截图
已完成登录后多页面首屏截图留证：
- Dashboard
- Profit
- Decision
- Inventory
- Funnel
- Ads
- ABC
- Price
- Strategy
- Import
- Reminder Drawer

## 5. 结论
本轮补充验证覆盖了“样本数据 -> 数据库写入 -> API返回 -> 页面可视化”的完整链路，
用于证明不仅单页可用，核心运营页面均可在样本数据下完成联调展示。
