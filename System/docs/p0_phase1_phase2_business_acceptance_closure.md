# P0 Phase 1/2 业务验收收口（仅本轮 4 项）

> 范围：只做 Phase 1/2 收口，不进入 Phase 3/4。

## 1) 下单数自动映射修复
- canonical 落点：`orders`（`fact_orders_daily.ordered_qty`）。
- alias 规则：新增/强化 `下单数 / 订单数 / 已订购商品 / Заказы / orders`。
- 之前未命中原因：registry 缺少 `orders` canonical，且 `已订购商品` 被 `items_ordered` 占用，导致核心字段检查视角下 `orders` 命中缺失。

## 2) 库存自动映射修复
- canonical 落点：`stock_total`（`fact_inventory_daily.stock_total`）。
- alias 规则：新增/强化 `库存数量 / 当前库存 / 可售库存 / 结余库存 / Остаток на конец периода / stock_qty`。
- 之前未命中原因：旧验收脚本仅看中文 xlsx，该文件本身不含库存列；同时补齐库存别名覆盖真实 csv/俄文列头变体。

## 3) staging 错误分类实证
- 已输出分布：`docs/p0_phase1_phase2_business_closure.json`。
- 包含：
  - row status 分布（`loaded / fact_error` 等）
  - error class 分布（来自 `import_error_log.error_type`）
  - `auto_fixed / quarantined / fatal` 汇总
  - 样例行（含 `row_no / status / row_error_summary_json`）

## 4) 浏览器真实链路复验
- 浏览器链路证据（upload + confirm）
  - 截图：`browser:/tmp/codex_browser_invocations/06dece3855ae7fb4/artifacts/artifacts/p0_phase12_browser_chain.png`
  - network：`browser:/tmp/codex_browser_invocations/06dece3855ae7fb4/artifacts/artifacts/p0_phase12_browser_network.json`
- 核验项：
  - `upload` JSON 含 parse 统计
  - `confirm` JSON 含 `stagingRows / factLoadErrors / errorRows`
  - 证明浏览器链路已落在新 Phase 1/2 管线

## 当前结论
- Phase 1/2 底座改造有效，且本轮 4 项收口已提交实证。
- 仍不将导入整体标记为“已通过”（中文真实样本仍存在 quarantined 行，属于未关闭数据质量项）。
