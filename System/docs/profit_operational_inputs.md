# ProfitCalculator 运营字段真实消费说明（收口验收）

## 当前已真实消费

| 运营字段 | 进入方式 | 在利润页作用 |
|---|---|---|
| `sale_price` / `list_price` | 自动回填（pricing autofill + 快照） | 当前利润、建议售价、盈亏平衡折扣 |
| `commission_rate`（映射到 variable_rate_total） | 导入写入快照费率 | 影响净利率与建议售价 |
| `items_returned` | 通过 `return_loss_cost`/售后损耗参数体现 | 风险提示（售后损耗） |
| `items_canceled` | 通过 `cancel_loss_cost` 参数体现 | 风险提示（取消损耗） |
| `ad_revenue_rate` / `ad_spend` | 通过 `ads_rate` 与投放成本参数体现 | 影响净利润与调价敏感度 |

## 当前部分消费（页面可见，但仍是参数化间接）

| 字段 | 现状 | 结论 |
|---|---|---|
| `rating_value` / `review_count` | 在提醒/质量风险链路已消费，利润页未直接做评分惩罚项 | 需下一步把评价质量映射为费率惩罚 |
| `discount_pct` | 由 `sale_price/list_price` 可计算，已用于折扣敏感度表 | 建议固化为显示字段 |
| `price_index_status` | 价格页有“竞争性”判断，但利润页无直接状态标签 | 需后续补齐 |
| `promo_days_count` | API已入仓（临时占位到 ads 事实），利润页未直接显示 | 需后续专列/专卡片 |

## 利润页结论（本轮真实状态）

- 已达到：可用运营字段（价格、费率、广告/售后损耗）驱动利润求解，不再仅手工裸参数。
- 未完全达到：评价、活动天数、价格状态尚未形成“可解释的直接字段卡片”。
