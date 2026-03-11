from __future__ import annotations


class ReportService:
    def list_reports(self, report_type: str = "") -> list[dict[str, object]]:
        rows = [
            {
                "id": 1,
                "report_type": "daily",
                "report_date": "2026-03-06",
                "title": "日报：利润与广告波动",
                "summary": "净利润环比下降 5%，SKU-002 亏损扩大。",
            },
            {
                "id": 2,
                "report_type": "weekly",
                "report_date": "2026-03-03",
                "title": "周报：库存风险与策略执行",
                "summary": "P0/P1 任务完成率 62%，库存风险下降。",
            },
        ]
        if report_type:
            return [r for r in rows if r["report_type"] == report_type]
        return rows

    def get_report(self, report_id: int) -> dict[str, object]:
        if report_id == 1:
            return {
                "id": 1,
                "content_md": "# 日报\n\n- 销售额：...\n- 净利润：...\n- 亏损SKU池：SKU-002",
                "content_json": {"loss_pool": ["SKU-002"], "p0": 1, "p1": 2},
            }
        return {
            "id": 2,
            "content_md": "# 周报\n\n- 广告效率改善\n- 库存风险下降",
            "content_json": {"strategy_done_rate": 0.62},
        }
