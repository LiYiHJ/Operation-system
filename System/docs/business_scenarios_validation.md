# 高拟真业务场景验证结果

执行脚本：`PYTHONPATH=src python scripts/run_business_scenarios.py`

## 总览

- 场景数：6
- 检查项：7
- 通过：7
- 失败：0

## 场景逐条验收

| 场景 | 输入特征（关键） | 系统识别问题 | 系统动作建议 | 验收 |
|---|---|---|---|---|
| S1 高曝光低点击 | `impressions_total` 高，`card_visits` 低，CTR 低 | Funnel bottleneck = `CTR` | “围绕CTR优化主图/价格/履约” | ✅ |
| S2 高点击低加购 | `card_visits` 高，`add_to_cart_total` 低 | Funnel bottleneck = `加购率` | 详情页/价格/信任优化方向 | ✅ |
| S3 高加购低下单 | `add_to_cart_total` 高，`orders` 低 | Funnel bottleneck = `下单率` | 价格促销与转化优化 | ✅ |
| S4 下单可但取消/退货高 | `orders` 不低，`canceled/returned` 高 | ABC issue 非“结构健康” | 履约/售后风险处理优先 | ✅ |
| S5 销售可但广告效率差 | `order_amount` 高，`ad_spend` 高 | Ads spend 被识别且 ROAS 可见 | 控制低效投放结构 | ✅ |
| S6 营收高但毛利危险 | `order_amount` 高、`net_margin` 低 | Price 推荐命中低毛利 | “提价+优化费率” | ✅ |

## 核心样例输出（脚本原始结果摘要）

- Dashboard: `totalRevenue=62700.0`, `totalOrders=661`, `profitMargin=0.1006`
- Funnel 示例：`S1_HIGH_EXPOSURE_LOW_CLICK` -> `bottleneck=CTR`
- Price 示例：`S6_HIGH_REVENUE_LOW_MARGIN` -> `margin=0.03`, recommendation=`低价低毛利，建议提价3%-8%并优化费率`
- Ads summary: `totalSpend=12060.0`, `avgRoas=3.88`
