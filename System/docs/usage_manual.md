# 运营系统详细使用说明报告（上线前验收版）

> 项目路径：`C:\Operation-system\System`
>
> 本文档用于**本机最终验收**与**日常操作**，重点覆盖 4 条闭环：
>
> 1. 真实库闭环
> 2. 真实文件导入闭环
> 3. 真实 Ozon API 同步闭环
> 4. 真实销售后台推送闭环

---

## 1. 系统概览

系统为前后端分离架构：

- 前端：React + Ant Design + React Query
- 后端：Flask API + Service 层
- 数据：PostgreSQL（生产建议 `ecom_v51_prod`）
- 主链路：Import → Fact Tables → Analysis → Strategy → Decision → ExecutionLog

---

## 2. 启动方式（真实库）

### 2.1 后端启动

PowerShell：

```powershell
cd C:\Operation-system\System
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "$PWD\src"
$env:DATABASE_URL = "postgresql+psycopg://ecom_user:strong_password@127.0.0.1:5432/ecom_v51_prod"
python -m ecom_v51.api.app
```

### 2.2 前端启动

```powershell
cd C:\Operation-system\System\frontend
npm install
npm run dev
```

浏览器：`http://127.0.0.1:5173`

---

## 3. 登录与导航

1. 打开登录页，输入账号密码登录。
2. 主要导航建议顺序：
   - 运营总览
   - 系统设置（数据接入中心）
   - 利润定价工作台
   - 策略/决策页面

---

## 4. 系统设置：数据接入中心（主入口）

路径：`系统设置 -> 数据接入中心`

### 4.1 平台连接区

字段说明：

- Provider（固定 Ozon）
- 启用数据源
- 自动拉取
- 同步频率（manual/hourly/daily）
- Client ID / Seller ID
- 只读采集 Token（read token）
- 动作执行 Token（action token）
- 销售后台推送 URL
- Mock Ozon 开关（仅联调）

操作顺序：

1. 填写并保存配置
2. 点击“权限校验”
3. 查看提示：`readTokenReady / actionTokenReady`

### 4.2 同步范围区（按业务域）

支持勾选业务域后手动同步：

1. 商品与上品中台
2. 订单与履约中台
3. 促销与价格中台
4. 服务与售后中台
5. 报表与经营分析中台

操作：

1. 勾选 scope
2. 点击“立即同步一次”
3. 查看“最近同步记录”与“最近导入记录”

### 4.3 文件导入区（兜底）

路径：`系统设置 -> 文件导入`

用于 API 不可用或补录场景。

---

## 5. 闭环 1：真实库验收步骤

### 5.1 命令验证

```powershell
curl http://127.0.0.1:5000/api/health
curl http://127.0.0.1:5000/api/dashboard/overview
curl "http://127.0.0.1:5000/api/reminders/list?shopId=1"
```

### 5.2 SQL 验证（psql）

```sql
SELECT current_database();

SELECT to_regclass('public.import_batch') AS import_batch,
       to_regclass('public.sync_run_log') AS sync_run_log,
       to_regclass('public.push_delivery_log') AS push_delivery_log;
```

### 5.3 通过标准

- `health` 返回 200；
- 空库时 `dashboard/overview` 和 `reminders/list` 不 500；
- 当前连接库为 `ecom_v51_prod`。

---

## 6. 闭环 2：真实文件导入验收步骤

### 6.1 准备

测试文件目录：`C:\Operation-system\System\data`

### 6.2 页面操作

1. 进入 `系统设置 -> 文件导入`
2. 选择 xlsx/csv/json 文件
3. 点击开始解析
4. 完成字段映射
5. 点击确认导入

### 6.3 浏览器验证点（必须）

在 Network 中确认出现：

- `POST /api/import/upload`
- `POST /api/import/confirm`

### 6.4 SQL 验证

```sql
-- 最近导入批次
SELECT id, source_type, platform_code, status, success_count, error_count, started_at, finished_at
FROM import_batch
ORDER BY id DESC
LIMIT 10;

-- 导入文件记录
SELECT id, batch_id, file_name, status, created_at
FROM import_batch_file
ORDER BY id DESC
LIMIT 20;

-- 导入异常（若有）
SELECT id, batch_file_id, row_no, column_name, error_type, error_message, created_at
FROM import_error_log
ORDER BY id DESC
LIMIT 20;

-- 事实表增量（示例）
SELECT COUNT(*) AS fact_sku_daily_cnt FROM fact_sku_daily;
SELECT COUNT(*) AS fact_orders_daily_cnt FROM fact_orders_daily;
SELECT COUNT(*) AS fact_profit_snapshot_cnt FROM fact_profit_snapshot;
```

### 6.5 页面出数验证

至少确认一个页面展示导入后数据：

- Dashboard
- ABC 分析
- 价格竞争力
- 库存预警

### 6.6 通过标准

- 上传+确认请求真实发出；
- `import_batch` 出现成功批次；
- 至少一个事实表数据有新增；
- 至少一个页面真实出数。

---

## 7. 闭环 3：真实 Ozon API 同步验收步骤

### 7.1 页面操作

1. 系统设置中填写真实 Ozon 凭证
2. 权限校验
3. 勾选至少一个业务域 scope
4. 点击“立即同步一次”
5. 查看最近同步记录

### 7.2 API 命令（可选）

```powershell
curl "http://127.0.0.1:5000/api/integration/domains?shopId=1"

curl -X POST "http://127.0.0.1:5000/api/integration/permission-check" `
  -H "Content-Type: application/json" `
  -d "{\"shopId\":1,\"provider\":\"ozon\"}"

curl -X POST "http://127.0.0.1:5000/api/integration/sync-once" `
  -H "Content-Type: application/json" `
  -d "{\"shopId\":1,\"provider\":\"ozon\",\"scopes\":[\"product_catalog\",\"promotion_pricing\"]}"
```

### 7.3 SQL 验证

```sql
SELECT id, provider, trigger_mode, status, imported_rows, batch_id, message, started_at, finished_at
FROM sync_run_log
ORDER BY id DESC
LIMIT 20;

SELECT id, provider, enabled, auto_sync_enabled, sync_frequency, last_sync_status, last_sync_error, last_sync_at
FROM external_data_source_config
ORDER BY id DESC
LIMIT 10;
```

### 7.4 通过标准

- 至少一个 scope 用真实凭证同步成功；
- `sync_run_log` 有新增成功记录；
- 同步后至少一个接口或页面能读取到结果。

> 注意：若仅使用 mock 同步，只能判定“机制通过”，不能判定“真实通过”。

---

## 8. 闭环 4：真实销售后台推送验收步骤

### 8.1 页面操作

路径：`系统设置 -> API 推送联调`（或策略确认执行触发）

### 8.2 请求字段检查

请求体至少包含：

- sku
- actionType
- actionBefore
- actionAfter
- sourcePage
- sourceReason
- operator
- confirmedAt

### 8.3 API 命令（真实地址优先）

```powershell
curl -X POST "http://127.0.0.1:5000/api/integration/push-sales" `
  -H "Content-Type: application/json" `
  -d "{
    \"shopId\":1,
    \"targetUrl\":\"<真实销售后台URL>\",
    \"payload\":{
      \"sku\":\"SKU-UAT-001\",
      \"actionType\":\"pricing\",
      \"actionBefore\":\"price=99\",
      \"actionAfter\":\"price=109\",
      \"sourcePage\":\"decision\",
      \"sourceReason\":\"uat\",
      \"operator\":\"operator\",
      \"confirmedAt\":\"2026-01-01T00:00:00Z\"
    }
  }"
```

### 8.4 SQL 验证

```sql
SELECT id, strategy_task_id, execution_log_id, status, http_status, error_message, pushed_at
FROM push_delivery_log
ORDER BY id DESC
LIMIT 20;

SELECT id, strategy_task_id, source_page, operator, result_summary, confirmed_at
FROM execution_log
ORDER BY id DESC
LIMIT 20;
```

### 8.5 通过标准

- 请求真实发出；
- 推送结果写入 `push_delivery_log`；
- 页面可见推送状态；
- 失败时有错误原因与可重试标记（retryable）。

---

## 9. 利润定价工作台操作要点

路径：`利润定价工作台`

### 9.1 顶层视图

- 定价决策
- 成本与规则

### 9.2 关键输入输出

- 输入：`sale_price`, `list_price`, 目标模式与目标值
- 自动汇总：`variable_rate_total`, `fixed_cost_total`
- 输出：建议售价、净利润、净利率、保本价、折扣模拟、多情景对比

### 9.3 运输成本引擎

按仓库/服务等级/重量体积/敏感货等计算后回填固定成本项，影响建议售价。

---

## 10. 常见故障排查

### 10.1 导入提示成功但页面无数据

1. 查 `import_batch` 是否成功；
2. 查事实表是否增量；
3. 查页面筛选条件（shopId/date）是否匹配。

### 10.2 Ozon 同步失败

1. 查权限校验结果（read/action）；
2. 查 `sync_run_log.message` 报错；
3. 判断是凭证问题、scope 权限问题、接口返回结构问题。

### 10.3 推送失败

1. 查目标 URL 网络可达性；
2. 查 `push_delivery_log.http_status/error_message`；
3. 校验请求字段是否满足对方协议。

---

## 11. 验收记录模板（建议）

```text
A 真实库闭环：pass/fail
- health:
- dashboard空库:
- reminders空库:

B 文件导入闭环：pass/fail
- 文件名:
- upload请求:
- confirm请求:
- import_batch新增:
- 事实表新增:
- 页面出数页面:

C Ozon同步闭环：real-pass / mock-only / fail
- 凭证:
- scope成功:
- scope失败:
- sync_run_log新增:

D 推送闭环：real-pass / mock-only / fail
- 目标地址:
- push_delivery_log新增:
- http_status:
- 页面状态可见:
```

---

## 12. 最终说明

上线判定必须基于真实证据，不以“代码支持”替代“验收通过”。

建议你在本机按照本文档 4 条闭环逐项执行并留档（命令输出、Network 截图、SQL 结果）。
