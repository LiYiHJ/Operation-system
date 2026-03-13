# 最终系统收口验收报告（本轮）

## 1. 17 个已映射字段：字段 -> 事实表 -> 页面

- 详表见：`docs/field_to_fact_to_page_matrix.md`。
- 结论：17 个已映射字段已打通写库；其中 9 个属于 33 标准字段口径，8 个为兼容/成本/广告辅助字段。

## 2. 33 字段口径剩余未映射清单与上线影响

执行：`PYTHONPATH=src python scripts/check_field_coverage.py`

- 样本表头：17
- 33口径已映射：9
- 未映射：24

高影响（建议上线前至少补 API 或衍生口径）：
- `items_purchased`
- `price_index_status`
- `promo_days_count`

中影响（可先试运行，需在后续收口迭代补齐）：
- `abc_class`, `order_amount_share`, `avg_sale_price`
- `impression_to_click_cvr`, `search_catalog_position_avg`, `search_catalog_to_card_cvr`
- `order_to_purchase_cvr`, `items_delivered`, `items_canceled`, `ad_revenue_rate`, `recommendation_text` 等

结论：当前系统可“试运行”，但未达到“最终完全好用”。

## 3. 本机 ecom_v51_prod 真实导入验收（非 sqlite）

> 当前容器环境未提供 `ecom_v51_prod` 连接信息，因此本轮无法直接在生产库执行写入验收。

请在目标机器执行以下命令（原样可跑）：

```bash
cd /workspace/Operation-system/System
export DATABASE_URL='postgresql+psycopg2://<user>:<pass>@<host>:5432/ecom_v51_prod'
PYTHONPATH=src python -m ecom_v51.db.init_db
PYTHONPATH=src python scripts/check_field_coverage.py
PYTHONPATH=src python scripts/run_business_scenarios.py
```

并做生产库 SQL 对账：

```sql
-- 导入后事实表非零校验
select sum(impressions_total), sum(orders_count), sum(revenue_ordered) from fact_sku_daily;
select sum(ordered_qty), sum(returned_qty), sum(cancelled_qty), sum(ordered_amount) from fact_orders_daily;
select avg(rating_avg), sum(new_reviews_count) from fact_reviews_daily;
select sum(ad_spend), avg(roas) from fact_ads_daily;
select avg(sale_price), avg(list_price), avg(net_margin) from fact_profit_snapshot;
```

## 4. 利润页 / 策略页对新标准字段真实消费

### ProfitCalculator
- 已真实进入：`sale_price`, `list_price`, `commission_rate`（映射到费率）、广告/售后损耗相关字段。
- 部分间接：`items_returned`, `items_canceled`, `ad_revenue_rate` 通过损耗/广告参数影响利润与建议价。
- 未直接字段化展示：`rating_value`, `review_count`, `price_index_status`, `promo_days_count`。

### Strategy / Reminder
- 已消费：`review_count`, `rating_value`, `items_returned`, `items_canceled`（提醒与任务优先级/风险来源）。
- 结论：策略链路可生成动作与回写日志，但部分 33 字段仍未在策略解释层显式呈现。

## 5. 当前判定

- **可试运行**：是（导入->入库->页面/分析->动作建议链路成立）。
- **接近最终系统**：部分接近，但仍需补齐 33 字段中的高影响缺口，尤其是 `price_index_status` / `promo_days_count` / `items_purchased` 的稳定来源与页面解释。
