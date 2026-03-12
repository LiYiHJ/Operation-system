# 全系统设计报告（交付版）

## 1. 架构总览
- 前端：React + Ant Design + React Query。
- 后端：Flask API + Service 层。
- 存储：SQLAlchemy 模型与事实/维度表。

## 2. 核心业务链路
1. 数据导入：`ImportService.parse_import_file -> confirm_import`
2. 事实沉淀：SKU/订单/库存/广告/评价等事实表
3. 专题分析：ABC/Price/Funnel/Inventory/Ads
4. 策略沉淀：push-action-to-strategy -> `StrategyTask`
5. 决策执行：decision preview/confirm -> `ExecutionLog`
6. 回看追踪：Dashboard recent changes / Reminder execution_writeback

## 3. 认证与权限
- 轻量账号体系（user_account）+ hash 密码校验。
- 角色：operator/admin/viewer。
- 前端通过 login/me/logout 与路由守卫实现访问控制。

## 4. 提醒系统
- 聚合分类：新订单、新评价、系统告警、待确认动作、执行回写、导入异常。
- 未读状态按用户持久化（reminder_read_state）。

## 5. 执行留痕
- 独立执行日志：`ExecutionLog`。
- 关键字段：strategyTaskId/sourcePage/actionBefore/actionAfter/operator/confirmedAt/resultSummary/statusBefore/statusAfter。

## 6. 前端产品层级规范（现状）
- 首屏优先：标题、结论、关键指标、核心动作。
- 深度信息下沉：Tabs/Collapse/紧凑表格内部滚动。
- 维持高密度信息，不通过删模块减负。

## 7. 当前已知简化点
- 认证方案为轻量 token，不是企业级 IAM。
- Profit 的 SKU 级智能参数自动回填未做深度建模。
- 某些页面的深度区仍可继续做性能分块（后续优化项）。
