from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import json
import threading
from urllib import request as urlrequest
from urllib.error import URLError, HTTPError
from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError

from ecom_v51.db.models import (
    DimDate,
    DimSku,
    ExternalDataSourceConfig,
    FactAdsDaily,
    FactOrdersDaily,
    FactReviewsDaily,
    FactSkuExtDaily,
    ImportBatch,
    PushDeliveryLog,
    SyncRunLog,
)
from ecom_v51.db.session import get_engine, get_session
from ecom_v51.services.import_service import ImportService


DOMAIN_SCOPES: list[dict[str, Any]] = [
    {
        'key': 'product_catalog',
        'label': '商品与上品中台',
        'permissions': ['Product', 'Product read-only', 'Description Category', 'Brand', 'Barcode', 'Certification', 'Pricing strategy'],
        'api_path': '/v2/product/list',
    },
    {
        'key': 'orders_fulfillment',
        'label': '订单与履约中台',
        'permissions': ['Posting FBO', 'Posting FBS', 'FBP', 'Supply order', 'Warehouse'],
        'api_path': '/v3/posting/fbs/list',
    },
    {
        'key': 'promotion_pricing',
        'label': '促销与价格中台',
        'permissions': ['Actions', 'Want discount', 'Pricing strategy'],
        'api_path': '/v1/actions/list',
    },
    {
        'key': 'service_after_sales',
        'label': '服务与售后中台',
        'permissions': ['Review', 'Rating', 'Question', 'Chat', 'Returns', 'Cancelation'],
        'api_path': '/v1/review/list',
    },
    {
        'key': 'reporting_analytics',
        'label': '报表与经营分析中台',
        'permissions': ['Report', 'Company'],
        'api_path': '/v1/report/info',
    },
]

_TABLES_READY = False
_TABLES_LOCK = threading.Lock()


class IntegrationService:
    def __init__(self, shop_id: int = 1, ensure_tables: bool = True):
        self.shop_id = shop_id
        if ensure_tables:
            self._ensure_tables()

    @staticmethod
    def _ensure_tables() -> None:
        global _TABLES_READY

        if _TABLES_READY:
            return

        with _TABLES_LOCK:
            if _TABLES_READY:
                return

            engine = get_engine()
            models = [
                ExternalDataSourceConfig,
                SyncRunLog,
                PushDeliveryLog,
                FactSkuExtDaily,
            ]

            for model in models:
                try:
                    model.__table__.create(bind=engine, checkfirst=True)
                except OperationalError as exc:
                    if "already exists" not in str(exc).lower():
                        raise

            _TABLES_READY = True

    def list_domain_scopes(self) -> list[dict[str, Any]]:
        return DOMAIN_SCOPES

    def get_data_source_config(self, provider: str = 'ozon') -> dict[str, Any]:
        with get_session() as session:
            row = session.query(ExternalDataSourceConfig).filter(
                ExternalDataSourceConfig.shop_id == self.shop_id,
                ExternalDataSourceConfig.provider == provider,
            ).order_by(ExternalDataSourceConfig.id.desc()).first()
            if not row:
                return {
                    'provider': provider,
                    'enabled': False,
                    'autoSyncEnabled': False,
                    'syncFrequency': 'manual',
                    'credentials': {},
                    'settings': {},
                    'lastSyncAt': None,
                    'lastSyncStatus': None,
                    'lastSyncError': None,
                }
            return {
                'provider': row.provider,
                'enabled': row.enabled,
                'autoSyncEnabled': row.auto_sync_enabled,
                'syncFrequency': row.sync_frequency,
                'credentials': row.credentials_json or {},
                'settings': row.settings_json or {},
                'lastSyncAt': row.last_sync_at.isoformat() if row.last_sync_at else None,
                'lastSyncStatus': row.last_sync_status,
                'lastSyncError': row.last_sync_error,
            }

    def save_data_source_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        provider = payload.get('provider', 'ozon')
        with get_session() as session:
            row = session.query(ExternalDataSourceConfig).filter(
                ExternalDataSourceConfig.shop_id == self.shop_id,
                ExternalDataSourceConfig.provider == provider,
            ).order_by(ExternalDataSourceConfig.id.desc()).first()
            if not row:
                row = ExternalDataSourceConfig(shop_id=self.shop_id, provider=provider)
                session.add(row)
            row.enabled = bool(payload.get('enabled', True))
            row.auto_sync_enabled = bool(payload.get('autoSyncEnabled', False))
            row.sync_frequency = str(payload.get('syncFrequency', 'manual'))
            row.credentials_json = payload.get('credentials') or {}
            row.settings_json = payload.get('settings') or {}
            session.flush()
        return self.get_data_source_config(provider=provider)

    def check_permissions(self, provider: str = 'ozon') -> dict[str, Any]:
        cfg = self.get_data_source_config(provider=provider)
        creds = cfg.get('credentials') or {}
        read_token_ok = bool(creds.get('apiKey') or creds.get('readToken'))
        action_token_ok = bool(creds.get('actionToken') or creds.get('apiKey'))
        domain_status = []
        for scope in DOMAIN_SCOPES:
            domain_status.append({
                'scope': scope['key'],
                'label': scope['label'],
                'permissionCount': len(scope['permissions']),
                'status': 'ok' if read_token_ok else 'missing_token',
            })
        return {
            'provider': provider,
            'readTokenReady': read_token_ok,
            'actionTokenReady': action_token_ok,
            'domains': domain_status,
            'checkedAt': datetime.utcnow().isoformat(),
        }

    @staticmethod
    def _latest_source_file() -> Path | None:
        candidates = []
        for folder in [Path('data'), Path('src/uploads')]:
            if folder.exists():
                candidates.extend(list(folder.glob('*.xlsx')))
                candidates.extend(list(folder.glob('*.xls')))
                candidates.extend(list(folder.glob('*.csv')))
        if not candidates:
            return None
        return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[0]

    @staticmethod
    def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None, timeout: int = 12) -> dict[str, Any]:
        req = urlrequest.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json', **(headers or {})},
            method='POST',
        )
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode('utf-8') if resp else ''
            return json.loads(raw) if raw else {'status': resp.status}

    def _fetch_scope_data(self, scope: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        creds = config.get('credentials') or {}
        settings = config.get('settings') or {}
        base_url = (settings.get('ozon_base_url') or 'https://api-seller.ozon.ru').rstrip('/')
        use_mock = bool(settings.get('useMockOzon', False))
        endpoint = scope.get('api_path') or '/v1/ping'
        payload = {'shop_id': self.shop_id, 'scope': scope['key'], 'limit': 200}
        if use_mock:
            target = f"http://127.0.0.1:5000/api/integration/mock/ozon/{scope['key']}"
            return self._post_json(target, payload)
        headers = {
            'Client-Id': str(creds.get('clientId') or creds.get('sellerId') or ''),
            'Api-Key': str(creds.get('apiKey') or creds.get('readToken') or ''),
        }
        try:
            return self._post_json(f"{base_url}{endpoint}", payload, headers=headers)
        except Exception as ex:
            return {'status': 'failed', 'error': str(ex), 'rows': []}

    def _extract_pricing_autofill(self, scope_results: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        settings = config.get('settings') or {}
        existing = settings.get('latest_autofill') or {}
        return {
            'list_price': float(existing.get('list_price') or 139),
            'sale_price': float(existing.get('sale_price') or 119),
            'shop_campaign_price': float(existing.get('shop_campaign_price') or 112),
            'platform_campaign_price': float(existing.get('platform_campaign_price') or 105),
            'coupon_final_price': float(existing.get('coupon_final_price') or 101),
            'platform_commission_rate': float(existing.get('platform_commission_rate') or 0.16),
            'ads_rate': float(existing.get('ads_rate') or 0.07),
            'after_sales_loss_rate': float(existing.get('after_sales_loss_rate') or 0.015),
            'cancel_loss_cost': float(existing.get('cancel_loss_cost') or 1.1),
            'return_loss_cost': float(existing.get('return_loss_cost') or 1.6),
            'source': 'ozon_api_sync' if scope_results else 'default_template',
            'updatedAt': datetime.utcnow().isoformat(),
        }



    def _upsert_api_rows_to_facts(self, scope_results: dict[str, Any]) -> int:
        """最小 API 闭环：将高价值字段写入事实层（review/rating/returns/cancel/ad_rate）"""
        merged_rows: list[dict[str, Any]] = []
        for payload in scope_results.values():
            rows = payload.get('rows') if isinstance(payload, dict) else None
            if isinstance(rows, list):
                merged_rows.extend([x for x in rows if isinstance(x, dict)])
        if not merged_rows:
            return 0

        updated = 0
        with get_session() as session:
            today = datetime.utcnow().date()
            date_obj = session.query(DimDate).filter(DimDate.date_value == today).one_or_none()
            if date_obj is None:
                date_obj = DimDate(
                    date_value=today,
                    year=today.year,
                    month=today.month,
                    day=today.day,
                    week_of_year=today.isocalendar().week,
                )
                session.add(date_obj)
                session.flush()

            for row in merged_rows:
                sku_code = str(row.get('sku') or row.get('seller_sku') or row.get('offer_id') or '').strip()
                if not sku_code:
                    continue
                sku = session.query(DimSku).filter(DimSku.shop_id == self.shop_id, DimSku.sku == sku_code).one_or_none()
                if sku is None:
                    continue

                rating_value = row.get('rating_value', row.get('rating'))
                review_count = row.get('review_count', row.get('reviews'))
                items_returned = row.get('items_returned', row.get('returns'))
                items_canceled = row.get('items_canceled', row.get('cancelled'))
                items_ordered = row.get('items_ordered', row.get('orders'))
                order_amount = row.get('order_amount', row.get('revenue'))
                ad_revenue_rate = row.get('ad_revenue_rate')
                promo_days_count = row.get('promo_days_count')
                discount_pct = row.get('discount_pct', row.get('discount'))
                price_index_status = row.get('price_index_status', row.get('price_index'))
                items_purchased = row.get('items_purchased', row.get('purchased'))

                reviews = session.query(FactReviewsDaily).filter(
                    FactReviewsDaily.date_id == date_obj.id,
                    FactReviewsDaily.shop_id == self.shop_id,
                    FactReviewsDaily.sku_id == sku.id,
                ).one_or_none()
                if reviews is None:
                    reviews = FactReviewsDaily(date_id=date_obj.id, shop_id=self.shop_id, sku_id=sku.id, batch_id=1)
                    session.add(reviews)
                if rating_value is not None:
                    reviews.rating_avg = float(rating_value)
                    reviews.quality_risk_score = max(0.0, 5.0 - float(rating_value))
                if review_count is not None:
                    reviews.new_reviews_count = int(review_count)

                orders = session.query(FactOrdersDaily).filter(
                    FactOrdersDaily.date_id == date_obj.id,
                    FactOrdersDaily.shop_id == self.shop_id,
                    FactOrdersDaily.sku_id == sku.id,
                ).one_or_none()
                if orders is None:
                    orders = FactOrdersDaily(date_id=date_obj.id, shop_id=self.shop_id, sku_id=sku.id, batch_id=1)
                    session.add(orders)
                if items_ordered is not None:
                    orders.ordered_qty = int(items_ordered)
                if order_amount is not None:
                    orders.ordered_amount = float(order_amount)
                if items_returned is not None:
                    orders.returned_qty = int(items_returned)
                if items_canceled is not None:
                    orders.cancelled_qty = int(items_canceled)

                ads = session.query(FactAdsDaily).filter(
                    FactAdsDaily.date_id == date_obj.id,
                    FactAdsDaily.shop_id == self.shop_id,
                    FactAdsDaily.sku_id == sku.id,
                ).one_or_none()
                if ads is None:
                    ads = FactAdsDaily(date_id=date_obj.id, shop_id=self.shop_id, sku_id=sku.id, campaign_id=None, batch_id=1)
                    session.add(ads)
                if ad_revenue_rate is not None and float(ad_revenue_rate) > 0:
                    ads.roas = float(ad_revenue_rate)
                if promo_days_count is not None and int(promo_days_count) > 0 and ads.ad_orders <= 0:
                    ads.ad_orders = int(promo_days_count)

                ext = session.query(FactSkuExtDaily).filter(
                    FactSkuExtDaily.date_id == date_obj.id,
                    FactSkuExtDaily.shop_id == self.shop_id,
                    FactSkuExtDaily.sku_id == sku.id,
                ).one_or_none()
                if ext is None:
                    ext = FactSkuExtDaily(date_id=date_obj.id, shop_id=self.shop_id, sku_id=sku.id, batch_id=1)
                    session.add(ext)
                if items_purchased is not None:
                    ext.items_purchased = int(items_purchased)
                if promo_days_count is not None:
                    ext.promo_days_count = int(promo_days_count)
                if discount_pct is not None:
                    ext.discount_pct = float(discount_pct)
                if price_index_status not in [None, '']:
                    ext.price_index_status = str(price_index_status).strip()

                updated += 1
        return updated

    def run_sync_once(self, provider: str = 'ozon', trigger_mode: str = 'manual', scopes: list[str] | None = None) -> dict[str, Any]:
        started = datetime.utcnow()
        scope_keys = scopes or [x['key'] for x in DOMAIN_SCOPES]

        with get_session() as session:
            run = SyncRunLog(
                shop_id=self.shop_id,
                provider=provider,
                trigger_mode=trigger_mode,
                status='running',
                started_at=started,
                message=f'准备同步 scopes={len(scope_keys)}',
            )
            session.add(run)
            session.flush()
            run_id = run.id

        try:
            cfg = self.get_data_source_config(provider=provider)
            scope_results: dict[str, Any] = {}
            pulled_rows = 0
            for scope in DOMAIN_SCOPES:
                if scope['key'] not in scope_keys:
                    continue
                data = self._fetch_scope_data(scope, cfg)
                scope_results[scope['key']] = data
                rows = data.get('rows') if isinstance(data, dict) else None
                if isinstance(rows, list):
                    pulled_rows += len(rows)

            api_fact_updates = self._upsert_api_rows_to_facts(scope_results)

            source_file = self._latest_source_file()
            imported_rows = 0
            batch_id = None
            if source_file:
                svc = ImportService()
                parsed = svc.parse_import_file(str(source_file), shop_id=self.shop_id, operator=f'{provider}_sync')
                confirmed = svc.confirm_import(
                    session_id=int(parsed['sessionId']),
                    shop_id=self.shop_id,
                    manual_overrides=[],
                    operator=f'{provider}_sync',
                )
                imported_rows = int(confirmed.get('importedRows') or 0)
                batch_id = int(confirmed.get('batchId') or 0)

            autofill = self._extract_pricing_autofill(scope_results, cfg)

            with get_session() as session:
                run = session.query(SyncRunLog).filter(SyncRunLog.id == run_id).one()
                run.status = 'success'
                run.finished_at = datetime.utcnow()
                run.imported_rows = imported_rows
                run.batch_id = batch_id
                run.message = f"api_rows={pulled_rows} api_fact_updates={api_fact_updates} imported={imported_rows} scopes={','.join(scope_keys)}"

                row = session.query(ExternalDataSourceConfig).filter(
                    ExternalDataSourceConfig.shop_id == self.shop_id,
                    ExternalDataSourceConfig.provider == provider,
                ).order_by(ExternalDataSourceConfig.id.desc()).first()
                if row:
                    settings_json = row.settings_json or {}
                    settings_json['latest_scope_results'] = scope_results
                    settings_json['latest_autofill'] = autofill
                    settings_json['latest_scopes'] = scope_keys
                    row.settings_json = settings_json
                    row.last_sync_at = datetime.utcnow()
                    row.last_sync_status = 'success'
                    row.last_sync_error = None

            return {
                'status': 'success',
                'provider': provider,
                'runId': run_id,
                'scopes': scope_keys,
                'apiRows': pulled_rows,
                'importedRows': imported_rows,
                'apiFactUpdates': api_fact_updates,
                'batchId': batch_id,
                'autofill': autofill,
            }
        except Exception as ex:
            with get_session() as session:
                run = session.query(SyncRunLog).filter(SyncRunLog.id == run_id).one()
                run.status = 'failed'
                run.finished_at = datetime.utcnow()
                run.message = str(ex)
                cfg = session.query(ExternalDataSourceConfig).filter(
                    ExternalDataSourceConfig.shop_id == self.shop_id,
                    ExternalDataSourceConfig.provider == provider,
                ).order_by(ExternalDataSourceConfig.id.desc()).first()
                if cfg:
                    cfg.last_sync_at = datetime.utcnow()
                    cfg.last_sync_status = 'failed'
                    cfg.last_sync_error = str(ex)
            return {'status': 'failed', 'provider': provider, 'runId': run_id, 'error': str(ex)}

    def get_pricing_autofill(self, provider: str = 'ozon') -> dict[str, Any]:
        cfg = self.get_data_source_config(provider=provider)
        settings = cfg.get('settings') or {}
        return settings.get('latest_autofill') or self._extract_pricing_autofill({}, cfg)

    def list_sync_logs(self, limit: int = 20) -> list[dict[str, Any]]:
        with get_session() as session:
            rows = session.query(SyncRunLog).filter(SyncRunLog.shop_id == self.shop_id).order_by(SyncRunLog.id.desc()).limit(limit).all()
            return [{
                'id': r.id,
                'provider': r.provider,
                'triggerMode': r.trigger_mode,
                'status': r.status,
                'startedAt': r.started_at.isoformat() if r.started_at else None,
                'finishedAt': r.finished_at.isoformat() if r.finished_at else None,
                'importedRows': r.imported_rows,
                'batchId': r.batch_id,
                'message': r.message,
            } for r in rows]

    def list_import_logs(self, limit: int = 20) -> list[dict[str, Any]]:
        with get_session() as session:
            rows = session.query(ImportBatch).order_by(ImportBatch.id.desc()).limit(limit).all()
            return [{
                'batchId': r.id,
                'sourceType': r.source_type,
                'platformCode': r.platform_code,
                'status': r.status,
                'successCount': r.success_count,
                'errorCount': r.error_count,
                'startedAt': r.started_at.isoformat() if r.started_at else None,
                'finishedAt': r.finished_at.isoformat() if r.finished_at else None,
                'message': r.message,
            } for r in rows]

    def push_to_sales_backend(self, payload: dict[str, Any], target_url: str | None = None, strategy_task_id: int | None = None, execution_log_id: int | None = None) -> dict[str, Any]:
        config = self.get_data_source_config('ozon')
        default_url = (config.get('settings') or {}).get('sales_push_url') or 'http://127.0.0.1:5000/api/integration/mock/sales-backend'
        url = target_url or default_url
        now = datetime.utcnow()

        status = 'failed'
        http_status = None
        response_json: dict[str, Any] = {}
        error_message = None

        try:
            req = urlrequest.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST',
            )
            with urlrequest.urlopen(req, timeout=8) as resp:
                http_status = resp.status
                raw = resp.read().decode('utf-8') if resp else ''
                try:
                    response_json = json.loads(raw) if raw else {}
                except Exception:
                    response_json = {'raw': raw[:500]}
                status = 'success' if 200 <= http_status < 300 else 'failed'
                if status != 'success':
                    error_message = f'HTTP {http_status}'
        except HTTPError as ex:
            http_status = ex.code
            error_message = f'HTTP {ex.code}'
            try:
                response_json = json.loads(ex.read().decode('utf-8'))
            except Exception:
                response_json = {'raw': str(ex)}
        except URLError as ex:
            error_message = str(ex)
        except Exception as ex:
            error_message = str(ex)

        with get_session() as session:
            log = PushDeliveryLog(
                strategy_task_id=strategy_task_id,
                execution_log_id=execution_log_id,
                target_system='sales_backend',
                payload_json=payload,
                response_json=response_json,
                status=status,
                http_status=http_status,
                error_message=error_message,
                pushed_at=now,
            )
            session.add(log)
            session.flush()
            log_id = log.id

        return {
            'pushId': log_id,
            'status': status,
            'httpStatus': http_status,
            'targetUrl': url,
            'response': response_json,
            'error': error_message,
            'retryable': status != 'success',
            'traceId': payload.get('traceId'),
            'idempotencyKey': payload.get('idempotencyKey'),
            'pushedAt': now.isoformat(),
        }

    def list_push_logs(self, limit: int = 20) -> list[dict[str, Any]]:
        with get_session() as session:
            rows = session.query(PushDeliveryLog).order_by(PushDeliveryLog.id.desc()).limit(limit).all()
            return [{
                'pushId': r.id,
                'strategyTaskId': r.strategy_task_id,
                'executionLogId': r.execution_log_id,
                'status': r.status,
                'httpStatus': r.http_status,
                'error': r.error_message,
                'pushedAt': r.pushed_at.isoformat() if r.pushed_at else None,
                'targetSystem': r.target_system,
                'traceId': (r.payload_json or {}).get('traceId'),
                'idempotencyKey': (r.payload_json or {}).get('idempotencyKey'),
                'operator': (r.payload_json or {}).get('operator'),
                'payload': r.payload_json,
                'response': r.response_json,
            } for r in rows]
