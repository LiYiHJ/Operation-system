# 最终交付文档（P4.3）

## 1. 启动说明

### 后端
```bash
PYTHONPATH=src python -m ecom_v51.api.app
```

### 前端
```bash
cd frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

## 2. 样本数据初始化

```bash
python scripts/seed_operational_demo.py
```

初始化后会写入统一样本链路（SKU、订单、库存、广告、评价、策略任务、执行日志、告警/提醒来源）。

## 3. 默认登录账号

- operator / 123456（运营）
- admin / admin123（管理员）
- viewer / viewer123（只读）

## 4. 页面-数据源-动作链路

- Dashboard：`FactSkuDaily`、`FactProfitSnapshot`、`FactReviewsDaily`、`AlertEvent`、`StrategyTask`、`ExecutionLog` 聚合。
- Price / ABC / Funnel / Inventory / Ads：统一读取 `AnalysisService` 聚合结果，源自同一批事实表数据。
- Strategy：读取 `StrategyTask` + `ExecutionLog` + 决策快照；展示来源、状态与执行结果。
- Decision：读取 `StrategyTaskService.decision_preview`，执行确认写入 `ExecutionLog`。
- Reminder：聚合订单、评价、告警、待确认动作、执行回写、导入异常。

链路：
`Import -> Fact tables -> Analysis pages -> push to Strategy -> Decision confirm -> ExecutionLog -> Dashboard/Reminder 回看`

## 5. 已知轻量限制项

- 认证仍为轻量 token（itsdangerous），非完整 OAuth/RBAC。
- Profit 求解默认参数来自前端首屏默认值 + profile；非按 SKU 自动回填。
- 仍有 bundle 体积偏大告警（vite chunk > 500k）。

## 6. 最终改动文件清单（本轮）

- `frontend/src/layout/Layout.tsx`
- `frontend/src/pages/ProfitCalculator.tsx`
- `frontend/src/pages/DecisionEngine.tsx`

## 7. 最终验收摘要

- 顶栏标题已居中且稳定。
- Profit 首屏纵向占用进一步收敛。
- Decision 首屏（智能推荐/P0/执行队列）进一步紧凑。
- 核心数据链路和页面功能未删减，动作闭环保持可用。
