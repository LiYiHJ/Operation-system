# Future Capabilities（未完全消费数据的潜力）

当前样本/API中尚未完全被页面消费的字段，可进一步支撑：

1. 搜索位置趋势
- 字段：`search_catalog_position_avg`
- 能力：关键词位次波动、掉位告警、排名恢复建议。

2. 价格竞争评分
- 字段：`price_index_status`, `discount_pct`
- 能力：SKU 价格竞争分、分层调价策略。

3. 活动疲劳判断
- 字段：`promo_days_count`, `order_amount_share`
- 能力：活动边际收益下滑检测、停促建议。

4. 售后风险评分
- 字段：`items_returned`, `items_canceled`, `rating_value`
- 能力：退货风险评分、品类售后画像。

5. 客服负荷监控
- 字段：`review_count`, `recommendation_text`
- 能力：客服排班建议、高风险 SKU 工单预警。

6. 动态调价建议
- 字段：`avg_sale_price`, `impression_to_click_cvr`, `cart_to_order_cvr`
- 能力：按漏斗与毛利联合优化出价区间。

7. 平台建议驱动待办系统
- 字段：`recommendation_text` + 策略状态
- 能力：建议拆单、责任人、闭环 SLA 跟踪。
