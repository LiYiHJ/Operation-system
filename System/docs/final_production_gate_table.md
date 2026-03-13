# 最终生产门禁表

| 项目 | 当前状态 | 风险等级 | 当前证据 | 缺口 | 最小修复动作 | 是否阻塞正式使用前确认 |
|---|---|---|---|---|---|---|
| 环境与部署稳定性 | 有条件通过 | P1 | API 路由健康检查均 200（`final_readiness_live_checks.json`） | 依赖告警（flask-cors）、缺统一一键启动验收脚本 | 固化 `.env.example` + `start_check.sh` | 否 |
| 数据库与事实层主库基线 | 不通过 | P0 | 主库事实/闭环表 count 为 0（`final_readiness_live_checks.json.mainDbCounts`） | 当前环境无可验收业务基线数据 | 增加“上线前标准回放包”并设 non-zero gate | 是 |
| 导入链路 demo | 通过 | P2 | demo parse+confirm success（`final_readiness_import_checks.json`） | 无 | 保持回归测试 | 否 |
| 导入链路真实报表 A/B | 不通过 | P0 | parse 可映射但 confirm failed（errorRows=1505） | 真实报表 confirm 稳定性不足 | 补报表型 confirm 失败分层策略 + 错误聚合输出 | 是 |
| 集成配置与接口可用性 | 有条件通过 | P1 | data-source/save/get、permission-check、sync-once、push-sales、push-logs 均有样例（`final_readiness_integration_checks.json`） | 真实外部凭证环境未完成验收 | 增加真实凭证 smoke checklist | 是（真实上线前） |
| 页面/API/Service 全站回归 | 有条件通过 | P1 | 页面对应 API 路由存在且 200 | 主库空数据导致“空态可用但非业务可用” | 建立 UAT 基线数据集后全站回归 | 是 |
| 策略/决策/推送闭环 | 通过（测试环境） | P1 | `strategy_ui_closure_*`、`strategy_execution_*` 证据链齐全 | 生产环境压测与批量失败恢复证据不足 | 增加批量失败重试和回放演练 | 是（生产前） |
| 批量与异常恢复 | 不通过 | P0 | 仅单链路证据较完整，批量恢复证据不足 | 无系统化重试/回放门禁 | 增加 retry API + trace 检索 + 失败队列 | 是 |
| 权限与审计 | 有条件通过 | P1 | operator/traceId/idempotencyKey 已写入日志样例 | RBAC 粒度不足，viewer/operator 边界不完整 | 先落地最小 RBAC + 审计事件 | 是（生产前） |
