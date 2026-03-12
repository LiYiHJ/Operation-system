# Production Readiness Validation（生产前整体验证）

> 说明：本报告严格区分“已验证证据”和“未完成前置条件”。
> 
> 验证环境：当前仓库 + 本次最小阻塞修复提交。

## 1. 结论

- 当前结论：**有条件可上线（Conditional Go-Live）**。
- 主要依据：
  - 前端可稳定构建。
  - 后端核心 API 可启动并通过基础 smoke。
  - 导入/同步/推送具备链路与日志表。
  - 已补齐两项关键生产阻塞：
    1) 生产环境不再默认 debug 启动；
    2) 生产环境默认不自动注入弱口令默认账号。
- 仍阻塞项：
  - 需在真实生产网络完成 `ecom_v51_prod` 连通验证。
  - 需完成至少一次真实 Ozon 凭证同步验收。
  - 需完成至少一次真实销售后台地址推送验收。

---

## 2. 验证维度结论

### A. 启动与部署

**已完成**
- 前端生产构建可用（`npm run build`）。
- 后端可启动并提供 `/api/health`。

**本次修复**
- 后端 `__main__` 启动从硬编码 `debug=True` 改为读取配置。
- 默认配置在 `APP_ENV=production` 下会默认 `APP_DEBUG=false`。

**仍需上线前落实**
- 生产 WSGI 托管（Waitress/Gunicorn）与反向代理。
- 服务托管（Windows Service/NSSM 或 Docker）。

### B. 真实数据闭环

- 代码链路具备导入闭环能力（上传->解析->确认->入库）。
- 真实库 `ecom_v51_prod` 的最终验收需在目标机器执行。

### C. 真实 Ozon API 拉取闭环

- 具备 scope 编排、权限校验、同步日志、自动回填输出。
- 真实凭证同步验收需在具备真实凭证和可访问 Ozon 网络的环境执行。

### D. 真实销售后台推送闭环

- 已具备真实 HTTP 推送 + 响应落库 + retryable 标记。
- 真实地址验收需在目标网络环境执行（非仅 mock）。

### E. 权限与安全

**本次修复**
- 生产环境默认关闭 seed 弱口令账号注入。
- 生产环境若 SECRET_KEY 仍为默认弱值，启动直接失败。

**仍需关注**
- 当前认证为轻量 token，非企业 IAM。
- 凭证轮换、最小权限、审计策略需纳入上线流程。

### F. 稳定性与容错

- 空态与失败路径具备基础兜底（同步失败、推送失败、日志记录）。
- 仍建议在目标环境补充 Redis/DB 短时故障演练。

### G. 日志、监控、审计

- 已有健康检查接口与同步/导入/推送/执行日志链路。
- 仍建议补充结构化文件日志与集中检索（例如 ELK/Loki）。

### H. 回滚、备份与恢复

**最小回滚路径**
- 应用回滚：`git checkout <last_stable_commit>` + 重启服务。
- DB 恢复：使用上线前备份 `pg_dump` 文件执行恢复。

**建议备份命令（上线前）**
```bash
pg_dump -h 127.0.0.1 -U ecom_user -d ecom_v51_prod -Fc -f backup_before_release.dump
```

**建议恢复命令（故障回滚）**
```bash
pg_restore -h 127.0.0.1 -U ecom_user -d ecom_v51_prod -c backup_before_release.dump
```

---

## 3. 本次最小阻塞修复清单

1. 生产环境 debug 风险修复
- 文件：`src/ecom_v51/api/app.py`
- 说明：启动 debug 改为读取配置；生产环境禁止默认弱 SECRET_KEY 启动。

2. 默认弱账号注入风险修复
- 文件：`src/ecom_v51/services/auth_service.py`
- 说明：仅在 `ALLOW_SEED_USERS=true` 时注入默认账号；生产默认关闭。

3. 生产默认配置修正
- 文件：`src/ecom_v51/config/settings.py`
- 说明：`APP_ENV=production` 时默认 `APP_DEBUG=false`，且默认禁用 seed users。

---

## 4. 上线前最小条件清单（必须满足）

- [ ] `APP_ENV=production`
- [ ] 配置强 SECRET_KEY（非默认值）
- [ ] `ALLOW_SEED_USERS=false`
- [ ] 后端通过生产托管启动（非 debug）
- [ ] 前端已构建并通过反向代理访问
- [ ] 完成真实库导入闭环验收（含页面出数）
- [ ] 完成至少一次真实 Ozon API scope 同步
- [ ] 完成至少一次真实销售后台地址推送验收
- [ ] 完成上线前 `pg_dump` 备份
- [ ] 具备一键回滚步骤与责任人

