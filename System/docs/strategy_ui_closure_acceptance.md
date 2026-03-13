# 页面级完整闭环验收（策略/决策/推送）

## 验收目标
仅验证 UI 可操作闭环：
1) 价格页触发策略建议；2) 打开 decision preview；3) confirm；4) 策略清单可见任务；5) 状态变化；6) push-sales；7) push/execution/task 日志可追踪。

## UI 证据链（本轮）
- Step1 价格页（非空）: `ui_chain_step1_price.png`
- Step1-After 触发推策略后: `ui_chain_step1_price_after_push.png`
- Step2 决策预览页: `ui_chain_step2_decision_preview.png`
- Step3 confirm后决策页: `ui_chain_step3_decision_after_confirm.png`
- Step4 策略清单（出现任务）: `ui_chain_step4_strategy_list.png`
- Step5 策略状态更新后: `ui_chain_step5_strategy_status_update.png`
- Step6 系统设置推送日志页: `ui_chain_step6_settings_push_logs.png`
- Step7 手动 push 后日志页: `ui_chain_step7_settings_after_manual_push.png`
- 浏览器 network 样例: `ui_chain_network_samples.json`

## API 样例（对应链路）
见 `strategy_ui_closure_api_samples.json`：
- `priceActionToStrategy`
- `decisionPreview`
- `decisionConfirm`
- `strategyList`
- `pushSales`
- `pushLogs`

## DB 样例（对应链路）
见 `strategy_ui_closure_db_samples.json`：
- `strategy_task`（任务落库）
- `execution_log`（confirm 与执行状态）
- `push_delivery_log`（推送结果）
- `traceChain`（按 traceId 关联 push/execution/task）

## 四个关键问题回答
1. **策略清单页为什么可能显示 0？**
   - 本轮复核结论：主要是环境初始数据为空或当次会话尚未触发“推策略/生成策略”，不是前端固定写死为 0。
   - 页面数据来源是 `/api/strategy/list`，只要先触发 `action-to-strategy` 或 `generate`，列表会出现记录。

2. **push 执行后的日志在哪个页面可见？**
   - 在「系统设置」页 Push 标签中的“推送结果日志”表格可见（对应 `/api/integration/push-logs`）。

3. **operator 在页面交互链里是否真实写入？**
   - 是。`decision_confirm` 传入 operator（如 `decision_ui/ui_acceptance`）后，`execution_log.operator` 与 push payload 中 `operator` 都可查到。

4. **task status update 是否驱动 UI 实时变化？**
   - 是。策略清单页“开始”按钮调用 `/api/strategy/task/<id>/status` 后触发 react-query invalidate，列表会刷新显示新状态；决策页也会刷新预览状态。

## 一条 traceId / idempotencyKey 证据链
- traceId：见 `strategy_ui_closure_db_samples.json.latestTraceId`
- 同 traceId 出现在：
  - `push_delivery_log.payload_json.traceId`
  - `execution_log.extra_json.traceId` 或 `extra_json.pushResult.traceId`
  - API `pushLogs.rows[*].traceId`
- idempotencyKey 出现在：
  - `push_delivery_log.payload_json.idempotencyKey`
  - API `pushSales.idempotencyKey` / `pushLogs.rows[*].idempotencyKey`
