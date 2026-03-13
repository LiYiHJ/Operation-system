from __future__ import annotations

import json
import uuid
from datetime import date, datetime
from typing import List, Dict, Any

from sqlalchemy import inspect

from ecom_v51.db.session import get_session, get_engine
from ecom_v51.db.models import DimSku, ExecutionLog, StrategyTask, ReportSnapshot
from ecom_v51.strategy import StrategyEngine
from ecom_v51.models import SkuSnapshot
from ecom_v51.war_room import WarRoomService
from ecom_v51.services.integration_service import IntegrationService


SOURCE_SCHEMA_VERSION = 'v1'


def build_action_source(*, source_page: str, source_reason: str, source_module: str = 'analysis', extra: dict[str, object] | None = None) -> dict[str, object]:
    payload = {
        'version': SOURCE_SCHEMA_VERSION,
        'sourcePage': source_page,
        'sourceReason': source_reason,
        'sourceModule': source_module,
        'pushedAt': datetime.utcnow().isoformat(),
    }
    if extra:
        payload.update(extra)
    return payload


class StrategyTaskService:
    """策略任务服务 - 使用真实引擎和数据库"""

    def __init__(self):
        self.engine = StrategyEngine()
        self.war_room = WarRoomService()
        self._ensure_execution_table()

    @staticmethod
    def _ensure_execution_table() -> None:
        engine = get_engine()
        if 'execution_log' not in inspect(engine).get_table_names():
            ExecutionLog.metadata.create_all(bind=engine, tables=[ExecutionLog.__table__])

    @staticmethod
    def _source_from_task(task: StrategyTask) -> dict[str, str]:
        source_page = 'system'
        source_reason = task.trigger_rule or task.issue_summary
        if task.trigger_rule and ':' in task.trigger_rule:
            source_page = task.trigger_rule.split(':')[0]

        if task.risk_note:
            try:
                parsed = json.loads(task.risk_note)
                source_page = str(parsed.get('sourcePage', source_page))
                source_reason = str(parsed.get('sourceReason', source_reason))
            except Exception:
                pass

        return {
            'sourcePage': source_page,
            'sourceReason': source_reason,
        }

    @staticmethod
    def _extract_task_history(task: StrategyTask, execution_logs: list[ExecutionLog], snapshots: list[ReportSnapshot]) -> tuple[str | None, dict[str, object] | None]:
        decision_at = None
        last_execution = None

        for snap in snapshots:
            content = snap.content_json or {}
            if snap.report_type == 'decision_confirm' and task.id in content.get('selected_task_ids', []):
                decision_at = snap.generated_at.isoformat() if snap.generated_at else decision_at

        for log in execution_logs:
            if log.strategy_task_id != task.id:
                continue
            last_execution = {
                'executionId': log.id,
                'executedAt': log.confirmed_at.isoformat() if log.confirmed_at else None,
                'operator': log.operator,
                'beforeStatus': log.status_before,
                'afterStatus': log.status_after,
                'resultSummary': log.result_summary,
            }
            break

        return decision_at, last_execution


    @staticmethod
    def _build_sku_map(session, tasks: list[StrategyTask]) -> dict[int, str]:
        sku_ids = sorted({int(t.sku_id) for t in tasks if t.sku_id})
        if not sku_ids:
            return {}
        rows = session.query(DimSku.id, DimSku.sku).filter(DimSku.id.in_(sku_ids)).all()
        return {int(r.id): str(r.sku) for r in rows}

    def list_tasks(self, priority: str = "", status: str = "") -> dict[str, object]:
        with get_session() as session:
            query = session.query(StrategyTask)
            if priority:
                query = query.filter(StrategyTask.priority == priority)
            if status:
                query = query.filter(StrategyTask.status == status)

            tasks = query.order_by(StrategyTask.priority, StrategyTask.created_at.desc()).limit(200).all()
            snapshots = (
                session.query(ReportSnapshot)
                .filter(ReportSnapshot.report_type == 'decision_confirm')
                .order_by(ReportSnapshot.generated_at.desc())
                .limit(400)
                .all()
            )
            execution_logs = (
                session.query(ExecutionLog)
                .order_by(ExecutionLog.confirmed_at.desc())
                .limit(400)
                .all()
            )

            sku_map = self._build_sku_map(session, tasks)
            normalized = []
            for task in tasks:
                source_info = self._source_from_task(task)
                last_decision_at, last_execution = self._extract_task_history(task, execution_logs, snapshots)
                normalized.append({
                    'id': str(task.id),
                    'priority': task.priority,
                    'status': task.status,
                    'strategyType': task.strategy_type,
                    'sku': sku_map.get(int(task.sku_id), str(task.sku_id or '-')) if task.sku_id else '-',
                    'triggerRule': task.trigger_rule,
                    'issueSummary': task.issue_summary,
                    'recommendedAction': task.recommended_action,
                    'observationMetrics': task.observation_metrics_json,
                    'assignee': task.owner,
                    'dueDate': task.due_date.isoformat() if task.due_date else None,
                    'createdAt': task.created_at.isoformat() if task.created_at else None,
                    'sourcePage': source_info['sourcePage'],
                    'sourceReason': source_info['sourceReason'],
                    'lastDecisionAt': last_decision_at,
                    'lastExecution': last_execution,
                    'impact': 7,
                    'urgency': 7,
                })

            return {
                'tasks': normalized,
                'summary': {
                    'total': len(normalized),
                    'pending': len([t for t in normalized if t['status'] == 'pending']),
                    'in_progress': len([t for t in normalized if t['status'] == 'in_progress']),
                    'completed': len([t for t in normalized if t['status'] == 'completed']),
                },
            }

    def generate_for_sku(self, sku_snapshot: SkuSnapshot) -> List[Dict[str, Any]]:
        tasks = self.engine.generate_for_sku(
            ctr=sku_snapshot.card_visits / sku_snapshot.impressions if sku_snapshot.impressions else 0,
            add_to_cart_rate=sku_snapshot.add_to_cart / sku_snapshot.card_visits if sku_snapshot.card_visits else 0,
            order_rate=sku_snapshot.orders / sku_snapshot.add_to_cart if sku_snapshot.add_to_cart else 0,
            net_margin=0,
            roas=sku_snapshot.ad_revenue / sku_snapshot.ad_spend if sku_snapshot.ad_spend else 0,
            days_of_supply=sku_snapshot.days_of_supply,
            return_rate=sku_snapshot.return_rate,
            rating=sku_snapshot.rating,
        )

        return [
            {
                'strategy_type': task.strategy_type,
                'priority': task.priority,
                'issue_summary': task.issue_summary,
                'recommended_action': task.recommended_action,
                'observation_metrics': task.observation_metrics,
            }
            for task in tasks
        ]

    def decision_preview(self, scope: str = 'all') -> dict[str, object]:
        with get_session() as session:
            query = session.query(StrategyTask).filter(StrategyTask.status.in_(['pending', 'in_progress', 'completed']))
            if scope == 'high_priority':
                query = query.filter(StrategyTask.priority.in_(['P0', 'P1']))
            tasks = query.order_by(StrategyTask.priority, StrategyTask.created_at.desc()).limit(200).all()

            snapshots = (
                session.query(ReportSnapshot)
                .filter(ReportSnapshot.report_type == 'decision_confirm')
                .order_by(ReportSnapshot.generated_at.desc())
                .limit(400)
                .all()
            )
            execution_logs = (
                session.query(ExecutionLog)
                .order_by(ExecutionLog.confirmed_at.desc())
                .limit(400)
                .all()
            )

            sku_map = self._build_sku_map(session, tasks)
            decisions = []
            for idx, task in enumerate(tasks):
                impact = max(1, 100 - idx)
                source_info = self._source_from_task(task)
                last_decision_at, last_execution = self._extract_task_history(task, execution_logs, snapshots)
                decisions.append({
                    'taskId': task.id,
                    'priority': task.priority,
                    'strategyType': task.strategy_type,
                    'status': task.status,
                    'issueSummary': task.issue_summary,
                    'sku': sku_map.get(int(task.sku_id), str(task.sku_id or '-')) if task.sku_id else '-',
                    'recommendedAction': task.recommended_action,
                    'expectedImpact': impact,
                    'confidence': 0.85 if task.priority in ['P0', 'P1'] else 0.7,
                    'riskLevel': 'high' if task.priority == 'P0' else ('medium' if task.priority == 'P1' else 'low'),
                    'evidence': {
                        'triggerRule': task.trigger_rule,
                        'observationMetrics': task.observation_metrics_json or [],
                        'riskNote': task.risk_note,
                    },
                    'sourcePage': source_info['sourcePage'],
                    'sourceReason': source_info['sourceReason'],
                    'lastDecisionAt': last_decision_at,
                    'writebackStatus': '已回写' if last_execution else '未回写',
                    'executionResult': (last_execution or {}).get('resultSummary'),
                })

            summary = {
                'P0': len([x for x in decisions if x['priority'] == 'P0']),
                'P1': len([x for x in decisions if x['priority'] == 'P1']),
                'P2': len([x for x in decisions if x['priority'] == 'P2']),
                'P3': len([x for x in decisions if x['priority'] == 'P3']),
            }
            return {
                'scope': scope,
                'total': len(decisions),
                'decisions': decisions,
                'summary': summary,
                'recommendations': self._build_recommendations(decisions, summary),
            }

    def decision_confirm(self, selected_task_ids: list[int], operator: str = 'planner') -> dict[str, object]:
        # 避免在事务中触发DDL导致sqlite锁冲突
        IntegrationService(shop_id=1, ensure_tables=True)

        now = datetime.utcnow()
        trace_id = f"decision-{now.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
        pending_pushes: list[dict[str, object]] = []

        with get_session() as session:
            tasks = session.query(StrategyTask).filter(StrategyTask.id.in_(selected_task_ids)).all()
            sku_map = self._build_sku_map(session, tasks)

            for task in tasks:
                source_info = self._source_from_task(task)
                before_status = task.status
                task.owner = operator
                task.status = 'in_progress'
                idempotency_key = f"task-{task.id}-{int(now.timestamp())}"

                execution = ExecutionLog(
                    strategy_task_id=task.id,
                    source_page=source_info['sourcePage'],
                    action_before=task.issue_summary,
                    action_after=task.recommended_action,
                    operator=operator,
                    confirmed_at=now,
                    result_summary='待推送执行',
                    status_before=before_status,
                    status_after=task.status,
                    extra_json={
                        'sourceReason': source_info['sourceReason'],
                        'traceId': trace_id,
                        'idempotencyKey': idempotency_key,
                    },
                )
                session.add(execution)
                session.flush()

                pending_pushes.append({
                    'taskId': task.id,
                    'shopId': task.shop_id,
                    'executionId': execution.id,
                    'beforeStatus': before_status,
                    'sourcePage': source_info['sourcePage'],
                    'sourceReason': source_info['sourceReason'],
                    'action': task.recommended_action,
                    'sku': sku_map.get(int(task.sku_id), str(task.sku_id or '-')) if task.sku_id else '-',
                    'strategyType': task.strategy_type,
                    'issueSummary': task.issue_summary,
                    'idempotencyKey': idempotency_key,
                })

            decision_snapshot = ReportSnapshot(
                shop_id=tasks[0].shop_id if tasks else 1,
                report_type='decision_confirm',
                report_date=date.today(),
                content_md='Decision confirmed',
                content_json={
                    'traceId': trace_id,
                    'operator': operator,
                    'selected_task_ids': selected_task_ids,
                    'count': len(tasks),
                    'confirmedAt': now.isoformat(),
                },
                generated_at=now,
            )
            session.add(decision_snapshot)
            session.flush()
            decision_snapshot_id = decision_snapshot.id

        results = []
        for item in pending_pushes:
            push_result = IntegrationService(shop_id=int(item['shopId']), ensure_tables=False).push_to_sales_backend(
                strategy_task_id=int(item['taskId']),
                execution_log_id=int(item['executionId']),
                payload={
                    'traceId': trace_id,
                    'idempotencyKey': item['idempotencyKey'],
                    'sku': item['sku'],
                    'actionType': item['strategyType'],
                    'actionBefore': item['issueSummary'],
                    'actionAfter': item['action'],
                    'sourcePage': item['sourcePage'],
                    'sourceReason': item['sourceReason'],
                    'operator': operator,
                    'confirmedAt': now.isoformat(),
                },
            )
            after_status = 'completed' if push_result.get('status') == 'success' else 'in_progress'
            result_summary = f"已执行：{str(item['action'])[:80]} | 推送:{push_result.get('status')}"

            with get_session() as session:
                task = session.query(StrategyTask).filter(StrategyTask.id == int(item['taskId'])).one_or_none()
                execution = session.query(ExecutionLog).filter(ExecutionLog.id == int(item['executionId'])).one_or_none()
                if task:
                    task.status = after_status
                    task.owner = operator
                if execution:
                    execution.status_after = after_status
                    execution.result_summary = result_summary
                    execution.extra_json = {**(execution.extra_json or {}), 'pushResult': push_result}

                execution_payload = {
                    'traceId': trace_id,
                    'idempotencyKey': item['idempotencyKey'],
                    'taskId': item['taskId'],
                    'operator': operator,
                    'executedAt': now.isoformat(),
                    'beforeStatus': item['beforeStatus'],
                    'afterStatus': after_status,
                    'action': item['action'],
                    'resultSummary': result_summary,
                    'sourcePage': item['sourcePage'],
                    'pushStatus': push_result.get('status'),
                    'pushId': push_result.get('pushId'),
                }
                session.add(ReportSnapshot(
                    shop_id=int(item['shopId']),
                    report_type='strategy_execution',
                    report_date=date.today(),
                    content_md=result_summary,
                    content_json=execution_payload,
                    generated_at=now,
                ))

            results.append(execution_payload)

        return {
            'traceId': trace_id,
            'confirmedCount': len(pending_pushes),
            'status': 'success',
            'reportSnapshotId': decision_snapshot_id,
            'executionLogs': results,
        }

    @staticmethod
    def _build_recommendations(decisions: list[dict[str, object]], summary: dict[str, int]) -> list[dict[str, str]]:
        recommendations: list[dict[str, str]] = []
        if summary.get('P0', 0) > 0:
            recommendations.append({
                'type': 'auto_execute',
                'title': '一键修复 P0 问题',
                'description': f"系统检测到 {summary['P0']} 个 P0 问题建议优先执行",
                'action': '立即自动执行',
            })
        top = decisions[0] if decisions else None
        if top:
            recommendations.append({
                'type': 'priority',
                'title': '优先级建议',
                'description': f"建议先处理 SKU {top.get('sku')}：{top.get('issueSummary')}",
                'action': '查看详情',
            })
        if summary.get('P1', 0) > 0 or summary.get('P2', 0) > 0:
            recommendations.append({
                'type': 'trend',
                'title': '趋势预警',
                'description': f"当前待处理任务 {len(decisions)} 个，建议滚动复盘任务执行进度",
                'action': '查看趋势',
            })
        return recommendations
