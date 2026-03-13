# 最终生产就绪验收报告

> 范围约束：本轮仅做“最终生产就绪验收（只读核查 + 最小必要修复建议）”，不扩展新功能、不做大重构。

## 核查执行摘要
- 已执行关键 API 路由连通性核查（dashboard/analysis/ads/reminders/strategy/integration），均返回 200。证据见 `final_readiness_live_checks.json.endpointChecks`。
- 已执行主库关键表计数核查：当前主库事实表与闭环表均为 0（空环境），不满足“可直接作为生产验收数据基线”。
- 已执行导入链路 A/B/demo 三样本复核（在隔离临时库）：
  - demo 可 parse + confirm success；
  - 两个 Ozon 报表样本 parse 可映射，但 confirm 失败（errorRows=1505）。
- 已执行集成接口能力核查（隔离临时库）：data-source 保存/读取、permission-check、sync-once、pricing-autofill、push-sales、push-logs 均可返回结构化结果。

---

## 1) 环境与部署
### 验收目标
启动流程稳定、依赖明确、环境变量清晰、可重复启动。

### 必查项
- 后端启动稳定
- 前端启动稳定
- DB 初始化稳定（建表 + 基础字典）
- 有清晰启动顺序
- 无明显 nohup/路径耦合

### 通过标准
- 前后端启动命令可重复执行；
- `init_db` 能稳定创建表并 seed 平台字典。

### 失败信号
- 启动报端口冲突、依赖缺失导致核心路由不可用；
- 需要人工临时补丁才能运行。

### 证据要求
- 启动命令输出日志；
- `final_readiness_live_checks.json` 中 API 200 覆盖。

### 若失败，最小修复建议
- 增加统一 `runbook`（一条命令初始化 + 一条命令启动）；
- 固化 `.env.example` 并在启动前校验关键变量。

### 当前结论
- **有条件通过**：开发/测试环境可启动并跑通 API，但仍存在依赖提示（如 flask-cors 缺失警告），不建议直接视为生产启动基线。

---

## 2) 数据库与事实层
### 验收目标
关键事实表存在、字段语义正确、可追踪、可 join。

### 必查项
- 关键事实表存在性
- 非零数据检查
- 扩展事实层 join key 稳定
- 高影响字段可追踪
- 无语义挪用

### 通过标准
- 主库中核心事实表有持续非零数据；
- 高影响字段在正确表中且可被服务消费。

### 失败信号
- 主库全零或空库；
- 字段只存在 schema 不存在有效数据；
- join key 不能稳定关联。

### 证据要求
- 主库 count；
- schema 字段存在性；
- 至少一条 join 成功样例。

### 若失败，最小修复建议
- 增加“上线前标准回放包”（导入 + 同步）把主库填充到可验收基线；
- 加入 `fact non-zero gate` 脚本，作为上线前门禁。

### 当前结论
- **不通过（阻塞正式确认）**：当前主库事实层计数为 0（空环境），不满足“生产前最终验收”的数据基线。

---

## 3) 导入链路
### 验收目标
真实报表/样本稳定 parse + confirm，统计口径一致，落库真实。

### 必查项
- demo + 真实 A/B 文件 parse
- mapping stats 一致
- confirm_import 成功率
- confirm 后事实表写入
- 无“UI 显示成功但落库失败”假成功

### 通过标准
- demo 与真实报表均可 confirm success；
- 映射统计和 confirm 结果一致。

### 失败信号
- parse 成功但 confirm 失败；
- importedRows 与事实表变化不一致。

### 证据要求
- `final_readiness_import_checks.json`（A/B/demo 三份结果 + fact counts）。

### 若失败，最小修复建议
- 补充“报表型模板专用校验降级策略”（允许部分字段缺失但不全量失败）；
- 对 confirm 失败原因出具按字段聚合错误报告，避免黑盒失败。

### 当前结论
- **有条件通过 / 偏风险**：demo 可通过；真实 A/B 报表 parse 可映射，但 confirm 失败（errorRows 高），该项仍需 P0 收口。

---

## 4) API 集成与外部联通
### 验收目标
integration 配置可保存读取，权限检查/同步/推送/日志可用，具备真实联通前置条件。

### 必查项
- data-source save/get
- permission-check
- sync-once
- pricing-autofill
- push-sales / push-logs
- traceId/idempotencyKey/失败日志

### 通过标准
- 上述 API 可调用且响应含关键字段；
- push 日志可回查 trace/idempotency。

### 失败信号
- 仅 mock 成功、无法切真实 URL；
- 日志字段缺失无法排障。

### 证据要求
- `final_readiness_integration_checks.json`
- strategy/push 样例链路 JSON。

### 若失败，最小修复建议
- 增加“真实 Ozon 凭证 smoke 模式”（只拉取最小 scope）；
- 增加推送失败自动重试策略（指数退避 + 人工重试入口）。

### 当前结论
- **有条件通过**：接口层能力可用，但真实外部环境（真实 Ozon 凭证、真实销售后台）证据不足，不能判定正式生产通过。

---

## 5) 页面/API/Service 全站回归
### 验收目标
关键页面都由真实 API + service + fact 支撑，无空壳假动作。

### 必查项（页面）
- Dashboard / ABC / Funnel / Price / Ads / Reminder / Strategy / Decision / Settings

### 通过标准
- 页面调用 API 均存在且 200；
- 关键交互会写库并回显状态变化。

### 失败信号
- 页面仅静态占位；
- 200 但无业务值。

### 证据要求
- API 连通检查 + 页面链路截图 + network 样例。

### 若失败，最小修复建议
- 对“空态页面”增加明确提示（无数据而非成功）；
- 对假动作按钮统一改成写库动作。

### 当前结论
- **有条件通过**：路由/API 连通良好，但主库空数据导致部分页面只能空态展示，不可作为最终生产回归证据。

---

## 6) 策略/决策/执行闭环
### 验收目标
preview→confirm→task status→push→logs 全链路可追踪。

### 必查项
- preview 证据字段/风险等级
- confirm 写库
- strategy list 可见任务
- status update 驱动 UI
- push-sales 写 push_delivery_log
- push-logs 页面可见
- traceId/idempotencyKey 贯穿

### 通过标准
- 至少一条完整 trace 链成立。

### 失败信号
- 接口 200 但无 execution_log/push_delivery_log；
- task 状态不回写。

### 证据要求
- `strategy_ui_closure_*` 与 `strategy_execution_*` 样例。

### 若失败，最小修复建议
- 为 confirm/push 增加强一致回写校验（写库失败即返回失败）；
- 增加 traceId 检索页。

### 当前结论
- **通过（测试环境）**：闭环链路在测试环境已可形成完整证据。

---

## 7) 批量处理与异常恢复
### 验收目标
批量生成/确认/推送可执行，部分失败可重试与追踪。

### 必查项
- 批量 strategy task 生成
- 批量 confirm/push
- 部分失败处理
- 重试与人工兜底
- 按 traceId/syncRunId/pushLogId 可追踪

### 通过标准
- 批量路径有明确成功/失败策略；
- 失败后可重放。

### 失败信号
- 仅支持单条手工；
- 失败后无法重试。

### 证据要求
- 批量 API 样例 + 失败样例 + 重试记录。

### 若失败，最小修复建议
- 增加“批次重试 API”与“失败队列视图”；
- 推送执行分批分页，避免大批量超时。

### 当前结论
- **不通过（阻塞正式确认）**：批量失败恢复和重放机制证据不足。

---

## 8) 权限、安全、日志与可审计性
### 验收目标
角色权限清晰、关键操作可审计、日志可定位、避免假成功。

### 必查项
- admin/operator/viewer 差异
- operator 留痕
- traceId/idempotencyKey/batchId
- 错误日志可定位
- 200 假成功检测

### 通过标准
- 关键动作都可追踪到操作者和链路 ID。

### 失败信号
- 角色权限未隔离；
- operator 丢失；
- 无法定位失败。

### 证据要求
- execution_log/push_delivery_log 示例 + 页面操作链证据。

### 若失败，最小修复建议
- 先落地最小 RBAC（viewer 禁写）；
- 增加审计事件表（关键动作统一写审计）。

### 当前结论
- **有条件通过**：日志可追踪基础具备，但权限体系仍偏轻量，不建议直接进入正式生产。
