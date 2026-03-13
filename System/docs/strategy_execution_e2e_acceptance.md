# 策略/决策/执行闭环真实打通验收表

## 1. 现状诊断（只读核查结论）

### 已证实真实可用
- `strategy_task` 可承载策略候选，`decision_confirm` 之后状态可进入 `in_progress/completed`，并附带操作人。 
- `execution_log` 在 confirm 时落库，包含 `status_before/status_after/operator/confirmed_at`，并在推送后回写 `pushResult`。 
- `push_delivery_log` 在 `push_to_sales_backend` 时真实写入，并记录 payload/response/error。 
- `report_snapshot` 同时记录 `decision_confirm` 和 `strategy_execution` 两类快照。
- API 链路可串通：`preview -> confirm -> push -> push-logs`（见 `strategy_execution_api_samples.json`）。

### 仅兼容层打通
- `/api/strategy/generate/:sku`、`/api/strategy/batch`、`/api/strategy/decision` 为兼容端点，业务上已接入真实 service，但语义仍偏“桥接层”。

### 历史断点（已最小修复）
- `decision_confirm` 原实现在 DB 事务内直接调用 `push_to_sales_backend`，在 SQLite 下易触发 `database is locked`，形成“接口 success 但状态/日志不完整”的假闭环风险。

### 当前最大结构性风险
- 批量重试仍以“单次接口触发”为主，尚未形成独立后台任务队列；大批量 confirm/push 场景会受请求超时影响。

## 2. 最小修复方案（已落地）

### P0
1. `StrategyTaskService.decision_confirm`
   - 事务阶段仅做：任务置 `in_progress`、写 `execution_log`、写 `decision_confirm` 快照。
   - 事务外做：逐条 push，随后回写 task/execution/report_snapshot。
   - 增加 `traceId`、`idempotencyKey` 贯穿 payload 和日志。
2. `IntegrationService.push_to_sales_backend/list_push_logs`
   - 响应与日志补充 `traceId/idempotencyKey/operator/payload`，便于串链追踪。
3. 页面“假动作”收口
   - `StrategyList` 的“开始”按钮改为真实 `updateTaskStatus`。
   - `DecisionEngine` 状态更新优先写后端；自动执行后刷新 preview。

### P1（建议下一步）
1. 增加“失败重试批次 API”（基于 traceId/taskIds）。
2. 增加任务并发阈值与分页推送，降低批量执行超时概率。

## 3. 4层证据

### DB 层证据
- 见 `strategy_execution_db_samples.json`：
  - 表计数：`strategy_task/execution_log/push_delivery_log/report_snapshot` 非零。
  - `latestTraceId` 可跨 `execution_log.extra_json.pushResult`、`push_delivery_log.payload_json`、`report_snapshot.content_json` 串联。

### Service 层证据
- `decision_preview` 现已返回 `riskLevel/evidence/status`。
- `decision_confirm` 产出 `traceId`、`executionLogs`，并按 push 结果更新状态。
- `push_to_sales_backend` 返回 `status/pushId/traceId/idempotencyKey`。

### API 层证据
- 见 `strategy_execution_api_samples.json`：
  - `/api/strategy/list`
  - `/api/strategy/decision/preview`
  - `/api/strategy/decision/confirm`
  - `/api/integration/push-sales`
  - `/api/integration/push-logs`
  - 兼容层 `/api/strategy/generate/:sku`、`/api/strategy/batch`、`/api/strategy/decision`

### 页面层证据
- 策略页链路截图：
  - `strategy_page_chain.png`
  - `decision_page_chain.png`
  - `settings_push_logs_chain.png`
- network 样例：`strategy_decision_network_samples.json`

## 4. 一条完整 trace 示例
1. 在策略/分析入口生成建议（兼容端点可触发任务创建）。
2. `decision_preview` 返回任务 + 证据 + 风险等级。
3. `decision_confirm` 返回 `traceId` 与逐条 `executionLogs`。
4. `push-sales` 成功/失败均进入 `push_delivery_log`。
5. `push-logs` 可按时间看到同一 `traceId` 的记录。
6. `strategy_task.status` 与 `execution_log.status_after` 与推送结果一致。


## 5. 截图修正说明（非空白）
- 重新通过登录态抓取页面截图，避免未登录重定向造成空白截图。
- 非空白截图产物：
  - `strategy_page_chain_nonblank.png`
  - `decision_page_chain_nonblank.png`
  - `settings_push_logs_chain_nonblank.png`
- 对应 network 抓包样例：`strategy_decision_network_samples_nonblank.json`。
