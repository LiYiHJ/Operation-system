from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
from collections import Counter

import pandas as pd
from sqlalchemy import inspect, select

from ecom_v51.config.settings import settings
from ecom_v51.db.base import Base
from ecom_v51.db.ingest_models import BatchAuditEvent, IngestBatch
from ecom_v51.db.models import DimPlatform, DimShop, DimSku
from ecom_v51.db.object_models import EntityIdentityMap, OrderHeader, OrderLine, SkuIdentityBridge
from ecom_v51.db.session import get_engine, get_session
from ecom_v51.services.batch_service import BatchService
from ecom_v51.services.import_batch_workspace import ImportBatchWorkspaceService
from ecom_v51.services.import_service import ImportService


class ObjectAssemblyService:
    CONTRACT_VERSION = 'p2b.v1'
    FACT_PRESET_FIELDS = {
        'economics_v1': [
            'factDate',
            'shopId',
            'skuId',
            'canonicalSku',
            'currencyCode',
            'providerCode',
            'orderedQty',
            'deliveredQty',
            'returnedQty',
            'cancelledQtyEstimated',
            'orderedAmount',
            'deliveredAmountEstimated',
            'discountAmount',
            'refundAmount',
            'platformFeeAmount',
            'fulfillmentFeeAmount',
            'netSalesAmount',
            'factReady',
        ],
        'ops_review_v1': [
            'factDate',
            'shopId',
            'skuId',
            'canonicalSku',
            'providerCode',
            'currencyCode',
            'factReady',
            'unresolvedReason',
            'identityConfidenceBucket',
            'identityConfidence',
            'orderHeaderCount',
            'orderLineCount',
            'orderedQty',
            'deliveredQty',
            'returnedQty',
            'netSalesAmount',
        ],
        'debug_full': [],
    }

    def __init__(
        self,
        root_dir: Path,
        *,
        batch_service: BatchService | None = None,
        import_service: ImportService | None = None,
        workspace_service: ImportBatchWorkspaceService | None = None,
    ) -> None:
        self.root_dir = Path(root_dir)
        self.batch_service = batch_service or BatchService(self.root_dir)
        self.import_service = import_service or ImportService()
        self.workspace_service = workspace_service or ImportBatchWorkspaceService(self.root_dir)

    @staticmethod
    def _clean_str(value: Any, default: str = '') -> str:
        text = str(value or '').strip()
        return text or default

    @staticmethod
    def _to_float(value: Any, default: float = 0.0) -> float:
        if value in (None, ''):
            return default
        try:
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _maybe_datetime(value: Any) -> datetime | None:
        if value in (None, ''):
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        text = str(value).strip()
        if not text:
            return None
        text = text.replace('Z', '+00:00')
        try:
            parsed = datetime.fromisoformat(text)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except Exception:
            return None

    def _ensure_schema(self) -> None:
        from ecom_v51.db import ingest_models  # noqa: F401
        from ecom_v51.db import models  # noqa: F401
        from ecom_v51.db import object_models  # noqa: F401

        engine = get_engine()
        Base.metadata.create_all(bind=engine)

    def _table_names(self) -> set[str]:
        return set(inspect(get_engine()).get_table_names())

    def _candidate_source_paths(self, detail: Dict[str, Any]) -> list[Path]:
        candidates: list[Path] = []
        for source in detail.get('sourceObjects') or []:
            file_path = str(source.get('filePath') or '').strip()
            if file_path:
                candidates.append(Path(file_path).expanduser())
            meta_path = str((source.get('contentMeta') or {}).get('sourcePath') or '').strip()
            if meta_path:
                candidates.append(Path(meta_path).expanduser())
        for raw_record in detail.get('rawRecords') or []:
            payload = dict(raw_record.get('payload') or {})
            file_path = str(payload.get('sourcePath') or payload.get('filePath') or '').strip()
            if file_path:
                candidates.append(Path(file_path).expanduser())
        workspace_batch_id = str(detail.get('workspaceBatchId') or '').strip()
        if workspace_batch_id:
            persisted = self.workspace_service.get_batch_by_workspace_id(workspace_batch_id) or {}
            workspace_path = str(persisted.get('filePath') or '').strip()
            if workspace_path:
                candidates.append(Path(workspace_path).expanduser())
        return candidates

    def _resolve_source_path(self, detail: Dict[str, Any]) -> Path | None:
        for candidate in self._candidate_source_paths(detail):
            try:
                resolved = candidate.resolve()
            except Exception:
                resolved = candidate
            if resolved.exists() and resolved.is_file():
                return resolved
        return None

    def _manual_overrides_from_detail(self, detail: Dict[str, Any]) -> list[dict]:
        out: list[dict] = []
        for item in detail.get('manualOverrides') or []:
            if not isinstance(item, dict):
                continue
            payload = item.get('payload')
            if isinstance(payload, dict):
                out.append(dict(payload))
        return out

    def _load_order_dataframe(self, detail: Dict[str, Any], *, operator: str) -> tuple[pd.DataFrame, Path | None, int]:
        source_path = self._resolve_source_path(detail)
        if source_path is None:
            raise FileNotFoundError('object_assembly_source_not_found')
        shop_id = int(detail.get('shopId') or 1)
        parse_result = self.import_service.parse_import_file(str(source_path), shop_id=shop_id, operator=operator)
        session_id = int(parse_result.get('sessionId') or 0)
        if not session_id:
            raise ValueError('object_assembly_session_missing')
        manual_overrides = self._manual_overrides_from_detail(detail)
        if manual_overrides:
            self.import_service.confirm_import(
                session_id=session_id,
                shop_id=shop_id,
                manual_overrides=manual_overrides,
                operator=operator,
            )
        if source_path.suffix.lower() in {'.csv', '.txt'}:
            df = pd.read_csv(source_path)
        else:
            df = pd.read_excel(source_path)
        if df is None or df.empty:
            raise ValueError('object_assembly_dataframe_missing')
        return df.copy(), source_path, session_id

    def _ensure_platform(self, session, provider_code: str) -> DimPlatform:
        provider_code = self._clean_str(provider_code, 'generic')
        platform = session.execute(select(DimPlatform).where(DimPlatform.platform_code == provider_code)).scalar_one_or_none()
        if platform is None:
            platform = DimPlatform(platform_code=provider_code, platform_name=provider_code.upper(), is_active=True)
            session.add(platform)
            session.flush()
        return platform

    def _ensure_shop(self, session, *, shop_id: int, provider_code: str) -> DimShop:
        row = session.get(DimShop, int(shop_id))
        if row is not None:
            return row
        platform = self._ensure_platform(session, provider_code)
        row = DimShop(
            id=int(shop_id),
            platform_id=platform.id,
            shop_code=f'shop-{shop_id}',
            shop_name=f'Shop {shop_id}',
            currency_code=settings.DEFAULT_CURRENCY,
            timezone=settings.TIMEZONE,
            status='active',
        )
        session.add(row)
        session.flush()
        return row

    @staticmethod
    def _row_value(row: Dict[str, Any], *keys: str) -> Any:
        for key in keys:
            if key in row and row.get(key) not in (None, ''):
                return row.get(key)
        return None

    def _canonical_sku_from_row(self, row: Dict[str, Any], batch_id: int, row_index: int) -> tuple[str, str]:
        for key in ('sku', 'platform_sku', 'seller_sku', 'offer_id', 'product_id'):
            value = self._clean_str(row.get(key))
            if value:
                return value, key
        return f'batch-{batch_id}-row-{row_index}', 'surrogate'

    def _ensure_dim_sku(self, session, *, shop_id: int, canonical_sku: str, row: Dict[str, Any]) -> DimSku:
        sku = session.execute(select(DimSku).where(DimSku.shop_id == shop_id, DimSku.sku == canonical_sku)).scalar_one_or_none()
        if sku is None:
            sku = DimSku(
                shop_id=shop_id,
                sku=canonical_sku,
                offer_id=self._clean_str(row.get('offer_id')) or None,
                seller_sku=self._clean_str(row.get('seller_sku')) or None,
                external_sku=self._clean_str(row.get('platform_sku')) or None,
                sku_name=self._clean_str(row.get('product_name')) or None,
                status='active',
                is_active=True,
            )
            session.add(sku)
            session.flush()
            return sku
        changed = False
        for attr, source_key in [('offer_id', 'offer_id'), ('seller_sku', 'seller_sku'), ('external_sku', 'platform_sku')]:
            candidate = self._clean_str(row.get(source_key)) or None
            if candidate and getattr(sku, attr) != candidate:
                setattr(sku, attr, candidate)
                changed = True
        if changed:
            session.flush()
        return sku

    def _upsert_identity_maps(
        self,
        session,
        *,
        canonical_sku: str,
        sku_id: int,
        provider_code: str,
        shop_id: int,
        batch_id: int,
        row: Dict[str, Any],
        primary_source_key: str,
    ) -> None:
        bridge = session.execute(
            select(SkuIdentityBridge).where(
                SkuIdentityBridge.shop_id == shop_id,
                SkuIdentityBridge.canonical_sku == canonical_sku,
            )
        ).scalar_one_or_none()
        source_meta = {
            'primarySourceKey': primary_source_key,
            'offerId': self._clean_str(row.get('offer_id')) or None,
            'sellerSku': self._clean_str(row.get('seller_sku')) or None,
            'platformSku': self._clean_str(row.get('platform_sku')) or None,
        }
        if bridge is None:
            bridge = SkuIdentityBridge(
                shop_id=shop_id,
                sku_id=sku_id,
                canonical_sku=canonical_sku,
                primary_source_key=primary_source_key,
                provider_code=provider_code,
                match_method='batch_object_assembly',
                match_confidence=1.0 if primary_source_key != 'surrogate' else 0.55,
                source_batch_id=batch_id,
                source_meta=source_meta,
            )
            session.add(bridge)
        else:
            bridge.sku_id = sku_id
            bridge.primary_source_key = primary_source_key
            bridge.provider_code = provider_code
            bridge.source_batch_id = batch_id
            bridge.source_meta = source_meta

        candidate_keys = {
            'sku': canonical_sku,
            'platform_sku': self._clean_str(row.get('platform_sku')) or None,
            'seller_sku': self._clean_str(row.get('seller_sku')) or None,
            'offer_id': self._clean_str(row.get('offer_id')) or None,
            'product_id': self._clean_str(row.get('product_id')) or None,
        }
        for source_key_type, source_key_value in candidate_keys.items():
            if not source_key_value:
                continue
            mapping = session.execute(
                select(EntityIdentityMap).where(
                    EntityIdentityMap.entity_type == 'sku',
                    EntityIdentityMap.provider_code == provider_code,
                    EntityIdentityMap.source_key_type == source_key_type,
                    EntityIdentityMap.source_key_value == source_key_value,
                )
            ).scalar_one_or_none()
            payload = {'shopId': shop_id, 'skuId': sku_id, 'sourceBatchId': batch_id}
            if mapping is None:
                mapping = EntityIdentityMap(
                    entity_type='sku',
                    canonical_entity_id=canonical_sku,
                    provider_code=provider_code,
                    source_key_type=source_key_type,
                    source_key_value=source_key_value,
                    match_method='batch_object_assembly',
                    match_confidence=1.0 if source_key_type != 'surrogate' else 0.55,
                    is_active=True,
                    source_batch_id=batch_id,
                    payload=payload,
                )
                session.add(mapping)
            else:
                mapping.canonical_entity_id = canonical_sku
                mapping.match_method = 'batch_object_assembly'
                mapping.match_confidence = 1.0 if source_key_type != 'surrogate' else 0.55
                mapping.is_active = True
                mapping.source_batch_id = batch_id
                mapping.payload = payload

    def _upsert_order_objects(
        self,
        session,
        *,
        batch_id: int,
        provider_code: str,
        shop_id: int,
        row_index: int,
        row: Dict[str, Any],
        canonical_sku: str,
        sku_id: int | None,
        batch_created_at: datetime | None,
    ) -> tuple[int, int]:
        external_order_no = self._clean_str(
            self._row_value(row, 'order_id', 'platform_order_id', 'external_order_no')
        ) or f'batch-{batch_id}-row-{row_index}'
        platform_order_id = self._clean_str(self._row_value(row, 'order_id', 'platform_order_id')) or None
        ordered_at = self._maybe_datetime(self._row_value(row, 'ordered_at', 'created_at', 'date')) or batch_created_at
        currency_code = self._clean_str(self._row_value(row, 'currency_code', 'currency'), settings.DEFAULT_CURRENCY)
        header = session.execute(
            select(OrderHeader).where(
                OrderHeader.shop_id == shop_id,
                OrderHeader.external_order_no == external_order_no,
            )
        ).scalar_one_or_none()
        header_payload = {'canonicalSku': canonical_sku, 'sourceRowIndex': row_index, 'providerCode': provider_code}
        if header is None:
            header = OrderHeader(
                shop_id=shop_id,
                platform_order_id=platform_order_id,
                external_order_no=external_order_no,
                order_status_normalized=self._clean_str(self._row_value(row, 'order_status_normalized'), 'reported'),
                currency_code=currency_code,
                ordered_at=ordered_at,
                provider_code=provider_code,
                source_batch_id=batch_id,
                source_row_index=row_index,
                payload=header_payload,
            )
            session.add(header)
            session.flush()
        else:
            header.platform_order_id = platform_order_id or header.platform_order_id
            header.order_status_normalized = self._clean_str(self._row_value(row, 'order_status_normalized'), header.order_status_normalized or 'reported')
            header.currency_code = currency_code or header.currency_code
            header.ordered_at = ordered_at or header.ordered_at
            header.provider_code = provider_code
            header.source_batch_id = batch_id
            header.source_row_index = row_index
            header.payload = header_payload
            session.flush()

        line = session.execute(select(OrderLine).where(OrderLine.order_id == header.id, OrderLine.line_no == 1)).scalar_one_or_none()
        ordered_qty = self._to_float(self._row_value(row, 'orders', 'items_ordered', 'quantity'), 1.0)
        line_payload = {
            'row': row,
            'canonicalSku': canonical_sku,
            'providerCode': provider_code,
        }
        if line is None:
            line = OrderLine(
                order_id=header.id,
                line_no=1,
                sku_id=sku_id,
                canonical_sku=canonical_sku,
                platform_line_id=self._clean_str(self._row_value(row, 'platform_line_id')) or None,
                qty_ordered=ordered_qty,
                qty_delivered=self._to_float(self._row_value(row, 'delivered_qty', 'quantity'), ordered_qty),
                qty_returned=self._to_float(self._row_value(row, 'returned_qty'), 0.0),
                sales_amount=self._to_float(self._row_value(row, 'order_amount', 'price')),
                discount_amount=self._to_float(self._row_value(row, 'discount_amount')),
                platform_fee_amount=self._to_float(self._row_value(row, 'platform_fee_amount')),
                fulfillment_fee_amount=self._to_float(self._row_value(row, 'fulfillment_fee_amount')),
                refund_amount=self._to_float(self._row_value(row, 'refund_amount')),
                currency_code=currency_code,
                source_batch_id=batch_id,
                source_row_index=row_index,
                payload=line_payload,
            )
            session.add(line)
            session.flush()
        else:
            line.sku_id = sku_id
            line.canonical_sku = canonical_sku
            line.platform_line_id = self._clean_str(self._row_value(row, 'platform_line_id')) or line.platform_line_id
            line.qty_ordered = ordered_qty
            line.qty_delivered = self._to_float(self._row_value(row, 'delivered_qty', 'quantity'), ordered_qty)
            line.qty_returned = self._to_float(self._row_value(row, 'returned_qty'), 0.0)
            line.sales_amount = self._to_float(self._row_value(row, 'order_amount', 'price'))
            line.discount_amount = self._to_float(self._row_value(row, 'discount_amount'))
            line.platform_fee_amount = self._to_float(self._row_value(row, 'platform_fee_amount'))
            line.fulfillment_fee_amount = self._to_float(self._row_value(row, 'fulfillment_fee_amount'))
            line.refund_amount = self._to_float(self._row_value(row, 'refund_amount'))
            line.currency_code = currency_code
            line.source_batch_id = batch_id
            line.source_row_index = row_index
            line.payload = line_payload
            session.flush()
        return header.id, line.id

    def assemble_batch(self, batch_ref: str, *, operator: str = 'system') -> Dict[str, Any]:
        detail = self.batch_service.get_batch_detail(batch_ref)
        if not detail:
            raise ValueError('batch_not_found')
        if self._clean_str(detail.get('datasetKind')).lower() != 'orders':
            raise ValueError('object_assembly_dataset_not_supported')

        self._ensure_schema()
        df, source_path, session_id = self._load_order_dataframe(detail, operator=operator)
        batch_id = int(detail.get('batchId') or 0)
        shop_id = int(detail.get('shopId') or 1)
        provider_code = self._clean_str(detail.get('platform'), 'generic')
        batch_created_at = self._maybe_datetime(detail.get('createdAt')) or datetime.now(timezone.utc)

        order_header_ids: set[int] = set()
        order_line_ids: set[int] = set()
        sku_ids: set[int] = set()
        identity_keys: set[tuple[str, str]] = set()

        with get_session() as session:
            self._ensure_shop(session, shop_id=shop_id, provider_code=provider_code)
            for row_index, row_data in enumerate(df.to_dict('records'), start=1):
                row = {str(k): v for k, v in dict(row_data or {}).items()}
                canonical_sku, primary_source_key = self._canonical_sku_from_row(row, batch_id, row_index)
                sku = self._ensure_dim_sku(session, shop_id=shop_id, canonical_sku=canonical_sku, row=row)
                sku_ids.add(int(sku.id))
                self._upsert_identity_maps(
                    session,
                    canonical_sku=canonical_sku,
                    sku_id=int(sku.id),
                    provider_code=provider_code,
                    shop_id=shop_id,
                    batch_id=batch_id,
                    row=row,
                    primary_source_key=primary_source_key,
                )
                for key_type in ('sku', 'platform_sku', 'seller_sku', 'offer_id', 'product_id'):
                    value = self._clean_str(row.get(key_type))
                    if value:
                        identity_keys.add((key_type, value))
                header_id, line_id = self._upsert_order_objects(
                    session,
                    batch_id=batch_id,
                    provider_code=provider_code,
                    shop_id=shop_id,
                    row_index=row_index,
                    row=row,
                    canonical_sku=canonical_sku,
                    sku_id=int(sku.id),
                    batch_created_at=batch_created_at,
                )
                order_header_ids.add(header_id)
                order_line_ids.add(line_id)

            session.add(
                BatchAuditEvent(
                    batch_id=batch_id,
                    event_type='object_assembly',
                    event_status='completed',
                    payload={
                        'eventType': 'object_assembly',
                        'contractVersion': self.CONTRACT_VERSION,
                        'datasetKind': 'orders',
                        'assembledAt': datetime.now(timezone.utc).isoformat(),
                        'operator': operator,
                        'sourcePath': str(source_path) if source_path else None,
                        'sessionId': session_id,
                        'rowsAssembled': int(len(df)),
                        'orderHeaderCount': len(order_header_ids),
                        'orderLineCount': len(order_line_ids),
                        'skuCount': len(sku_ids),
                        'identityCount': len(identity_keys),
                    },
                )
            )

        return self.get_batch_object_summary(batch_ref) or {
            'batchId': batch_id,
            'contractVersion': self.CONTRACT_VERSION,
            'datasetKind': 'orders',
            'status': 'completed',
        }

    def _load_batch_object_state(self, batch_ref: str) -> Optional[Dict[str, Any]]:
        detail = self.batch_service.get_batch_detail(batch_ref)
        if not detail:
            return None
        batch_id = int(detail.get('batchId') or 0)
        if batch_id <= 0:
            return None
        self._ensure_schema()
        with get_session() as session:
            order_headers = session.execute(select(OrderHeader).where(OrderHeader.source_batch_id == batch_id)).scalars().all()
            order_lines = session.execute(select(OrderLine).where(OrderLine.source_batch_id == batch_id)).scalars().all()
            bridges = session.execute(select(SkuIdentityBridge).where(SkuIdentityBridge.source_batch_id == batch_id)).scalars().all()
            identities = session.execute(select(EntityIdentityMap).where(EntityIdentityMap.source_batch_id == batch_id)).scalars().all()
            events = session.execute(
                select(BatchAuditEvent).where(BatchAuditEvent.batch_id == batch_id, BatchAuditEvent.event_type == 'object_assembly').order_by(BatchAuditEvent.id.desc())
            ).scalars().all()
        return {
            'detail': detail,
            'batchId': batch_id,
            'orderHeaders': order_headers,
            'orderLines': order_lines,
            'bridges': bridges,
            'identities': identities,
            'events': events,
        }

    def _build_identity_diagnostics(self, state: Dict[str, Any]) -> Dict[str, Any]:
        identities = list(state.get('identities') or [])
        bridges = list(state.get('bridges') or [])
        order_lines = list(state.get('orderLines') or [])
        key_counter = Counter()
        provider_counter = Counter()
        surrogate_identity_count = 0
        low_confidence_count = 0
        for row in identities:
            key_counter[str(row.source_key_type or 'unknown')] += 1
            provider_counter[str(row.provider_code or 'generic')] += 1
            if float(row.match_confidence or 0.0) < 0.8:
                low_confidence_count += 1
            canonical = self._clean_str(row.canonical_entity_id)
            if canonical.startswith('batch-') and '-row-' in canonical:
                surrogate_identity_count += 1
        surrogate_bridge_count = sum(1 for row in bridges if self._clean_str(row.primary_source_key) == 'surrogate')
        unresolved_lines: list[dict[str, Any]] = []
        for row in order_lines:
            canonical = self._clean_str(row.canonical_sku)
            if (not row.sku_id) or canonical.startswith('batch-'):
                payload = dict(row.payload or {})
                unresolved_lines.append({
                    'orderLineId': row.id,
                    'orderId': row.order_id,
                    'canonicalSku': canonical or None,
                    'reason': 'surrogate_canonical_sku' if canonical.startswith('batch-') else 'missing_sku_identity',
                    'sourceRowIndex': row.source_row_index,
                    'providerCode': self._clean_str(payload.get('providerCode')) or None,
                })
        return {
            'identityCount': len(identities),
            'identityBySourceKeyType': dict(sorted(key_counter.items())),
            'identityByProvider': dict(sorted(provider_counter.items())),
            'surrogateIdentityCount': surrogate_identity_count,
            'surrogateBridgeCount': surrogate_bridge_count,
            'lowConfidenceIdentityCount': low_confidence_count,
            'unresolvedLineCount': len(unresolved_lines),
            'unresolvedLineSamples': unresolved_lines[:20],
        }

    def _build_aggregate_metrics(self, state: Dict[str, Any]) -> Dict[str, Any]:
        order_lines = list(state.get('orderLines') or [])
        return {
            'orderHeaderCount': len(state.get('orderHeaders') or []),
            'orderLineCount': len(order_lines),
            'skuCount': len({bridge.sku_id for bridge in (state.get('bridges') or []) if bridge.sku_id}),
            'identityCount': len(state.get('identities') or []),
            'qtyOrderedTotal': round(sum(float(row.qty_ordered or 0.0) for row in order_lines), 4),
            'qtyDeliveredTotal': round(sum(float(row.qty_delivered or 0.0) for row in order_lines), 4),
            'salesAmountTotal': round(sum(float(row.sales_amount or 0.0) for row in order_lines), 4),
            'discountAmountTotal': round(sum(float(row.discount_amount or 0.0) for row in order_lines), 4),
            'refundAmountTotal': round(sum(float(row.refund_amount or 0.0) for row in order_lines), 4),
            'platformFeeAmountTotal': round(sum(float(row.platform_fee_amount or 0.0) for row in order_lines), 4),
            'fulfillmentFeeAmountTotal': round(sum(float(row.fulfillment_fee_amount or 0.0) for row in order_lines), 4),
            'netSalesAmountTotal': round(sum(float((row.sales_amount or 0.0) - (row.discount_amount or 0.0) - (row.refund_amount or 0.0)) for row in order_lines), 4),
        }

    def _build_event_history(self, events: list[BatchAuditEvent]) -> list[Dict[str, Any]]:
        out: list[Dict[str, Any]] = []
        for event in events[:10]:
            out.append({
                'eventId': event.id,
                'eventStatus': event.event_status,
                'createdAt': event.created_at.isoformat() if event.created_at else None,
                'payload': event.payload or {},
            })
        return out

    @staticmethod
    def _confidence_bucket(confidence: float) -> str:
        if confidence >= 0.95:
            return 'high'
        if confidence >= 0.8:
            return 'medium'
        return 'low'

    def _serialize_order_header(self, row: OrderHeader) -> Dict[str, Any]:
        payload = dict(row.payload or {})
        return {
            'orderHeaderId': row.id,
            'shopId': row.shop_id,
            'externalOrderNo': row.external_order_no,
            'platformOrderId': row.platform_order_id,
            'orderStatusNormalized': row.order_status_normalized,
            'currencyCode': row.currency_code,
            'orderedAt': row.ordered_at.isoformat() if row.ordered_at else None,
            'providerCode': row.provider_code,
            'sourceBatchId': row.source_batch_id,
            'sourceRowIndex': row.source_row_index,
            'payload': payload,
        }

    def _serialize_order_line(self, row: OrderLine) -> Dict[str, Any]:
        payload = dict(row.payload or {})
        canonical_sku = self._clean_str(row.canonical_sku) or None
        unresolved_reason = None
        if canonical_sku and canonical_sku.startswith('batch-'):
            unresolved_reason = 'surrogate_canonical_sku'
        elif not row.sku_id:
            unresolved_reason = 'missing_sku_identity'
        return {
            'orderLineId': row.id,
            'orderId': row.order_id,
            'lineNo': row.line_no,
            'skuId': row.sku_id,
            'canonicalSku': canonical_sku,
            'platformLineId': row.platform_line_id,
            'qtyOrdered': row.qty_ordered,
            'qtyDelivered': row.qty_delivered,
            'qtyReturned': row.qty_returned,
            'salesAmount': row.sales_amount,
            'discountAmount': row.discount_amount,
            'platformFeeAmount': row.platform_fee_amount,
            'fulfillmentFeeAmount': row.fulfillment_fee_amount,
            'refundAmount': row.refund_amount,
            'currencyCode': row.currency_code,
            'sourceBatchId': row.source_batch_id,
            'sourceRowIndex': row.source_row_index,
            'providerCode': self._clean_str(payload.get('providerCode')) or None,
            'unresolvedReason': unresolved_reason,
            'payload': payload,
        }

    def _serialize_identity(self, row: EntityIdentityMap) -> Dict[str, Any]:
        return {
            'identityId': row.id,
            'entityType': row.entity_type,
            'canonicalEntityId': row.canonical_entity_id,
            'providerCode': row.provider_code,
            'sourceKeyType': row.source_key_type,
            'sourceKeyValue': row.source_key_value,
            'matchMethod': row.match_method,
            'matchConfidence': row.match_confidence,
            'isActive': row.is_active,
            'sourceBatchId': row.source_batch_id,
            'payload': dict(row.payload or {}),
        }

    def _serialize_bridge(self, row: SkuIdentityBridge) -> Dict[str, Any]:
        return {
            'bridgeId': row.id,
            'shopId': row.shop_id,
            'skuId': row.sku_id,
            'canonicalSku': row.canonical_sku,
            'primarySourceKey': row.primary_source_key,
            'providerCode': row.provider_code,
            'matchMethod': row.match_method,
            'matchConfidence': row.match_confidence,
            'sourceBatchId': row.source_batch_id,
            'sourceMeta': dict(row.source_meta or {}),
        }

    def _paginate_rows(self, rows: list[Any], *, offset: int, limit: int) -> tuple[list[Any], dict[str, Any]]:
        total = len(rows)
        page = rows[offset: offset + limit]
        return page, {
            'offset': offset,
            'limit': limit,
            'returned': len(page),
            'total': total,
            'hasMore': offset + len(page) < total,
        }

    def get_batch_object_summary(self, batch_ref: str) -> Optional[Dict[str, Any]]:
        state = self._load_batch_object_state(batch_ref)
        if not state:
            return None
        detail = dict(state['detail'])
        events = list(state['events'])
        aggregate_metrics = self._build_aggregate_metrics(state)
        order_headers = list(state['orderHeaders'])
        order_lines = list(state['orderLines'])
        return {
            'batchId': state['batchId'],
            'datasetKind': detail.get('datasetKind'),
            'contractVersion': self.CONTRACT_VERSION,
            'status': 'completed' if events else 'pending',
            'rowsAssembled': len(order_lines),
            'orderHeaderCount': aggregate_metrics['orderHeaderCount'],
            'orderLineCount': aggregate_metrics['orderLineCount'],
            'skuCount': aggregate_metrics['skuCount'],
            'identityCount': aggregate_metrics['identityCount'],
            'aggregateMetrics': aggregate_metrics,
            'lastAssemblyEvent': {
                'eventStatus': events[0].event_status,
                'payload': events[0].payload or {},
                'createdAt': events[0].created_at.isoformat() if events and events[0].created_at else None,
            } if events else None,
            'items': {
                'orderHeaders': [self._serialize_order_header(row) for row in order_headers[:20]],
                'orderLines': [self._serialize_order_line(row) for row in order_lines[:20]],
            },
        }

    def get_batch_object_details(
        self,
        batch_ref: str,
        *,
        section: str = 'orderLines',
        limit: int = 50,
        offset: int = 0,
    ) -> Optional[Dict[str, Any]]:
        state = self._load_batch_object_state(batch_ref)
        if not state:
            return None
        detail = dict(state['detail'])
        aggregate_metrics = self._build_aggregate_metrics(state)
        identity_diagnostics = self._build_identity_diagnostics(state)
        section_key = self._clean_str(section, 'orderLines') or 'orderLines'
        normalized = {
            'headers': 'orderHeaders',
            'orderheaders': 'orderHeaders',
            'orderHeaders': 'orderHeaders',
            'lines': 'orderLines',
            'orderlines': 'orderLines',
            'orderLines': 'orderLines',
            'identities': 'identities',
            'identity': 'identities',
            'bridges': 'bridges',
            'bridge': 'bridges',
        }.get(section_key, section_key)

        rows: list[Any]
        serializer = None
        if normalized == 'orderHeaders':
            rows = list(state.get('orderHeaders') or [])
            serializer = self._serialize_order_header
        elif normalized == 'orderLines':
            rows = list(state.get('orderLines') or [])
            serializer = self._serialize_order_line
        elif normalized == 'identities':
            rows = list(state.get('identities') or [])
            serializer = self._serialize_identity
        elif normalized == 'bridges':
            rows = list(state.get('bridges') or [])
            serializer = self._serialize_bridge
        else:
            raise ValueError('unsupported_object_section')

        safe_offset = max(int(offset or 0), 0)
        safe_limit = min(max(int(limit or 50), 1), 200)
        page, page_info = self._paginate_rows(rows, offset=safe_offset, limit=safe_limit)
        return {
            'batchId': state['batchId'],
            'datasetKind': detail.get('datasetKind'),
            'contractVersion': self.CONTRACT_VERSION,
            'status': 'completed' if list(state.get('events') or []) else 'pending',
            'section': normalized,
            'pagination': page_info,
            'aggregateMetrics': aggregate_metrics,
            'identityDiagnostics': identity_diagnostics,
            'items': [serializer(row) for row in page],
        }

    def _build_rollups(self, state: Dict[str, Any]) -> Dict[str, Any]:
        order_headers = list(state.get('orderHeaders') or [])
        order_lines = list(state.get('orderLines') or [])
        identities = list(state.get('identities') or [])
        bridges = list(state.get('bridges') or [])

        status_rows: dict[str, dict[str, Any]] = {}
        for header in order_headers:
            status = self._clean_str(header.order_status_normalized, 'unknown')
            bucket = status_rows.setdefault(
                status,
                {
                    'orderStatusNormalized': status,
                    'orderHeaderCount': 0,
                    'orderLineCount': 0,
                    'salesAmountTotal': 0.0,
                    'discountAmountTotal': 0.0,
                    'refundAmountTotal': 0.0,
                },
            )
            bucket['orderHeaderCount'] += 1
        header_ids = {row.id: self._clean_str(row.order_status_normalized, 'unknown') for row in order_headers}
        for line in order_lines:
            status = header_ids.get(int(line.order_id or 0), 'unknown')
            bucket = status_rows.setdefault(
                status,
                {
                    'orderStatusNormalized': status,
                    'orderHeaderCount': 0,
                    'orderLineCount': 0,
                    'salesAmountTotal': 0.0,
                    'discountAmountTotal': 0.0,
                    'refundAmountTotal': 0.0,
                },
            )
            bucket['orderLineCount'] += 1
            bucket['salesAmountTotal'] = round(bucket['salesAmountTotal'] + float(line.sales_amount or 0.0), 4)
            bucket['discountAmountTotal'] = round(bucket['discountAmountTotal'] + float(line.discount_amount or 0.0), 4)
            bucket['refundAmountTotal'] = round(bucket['refundAmountTotal'] + float(line.refund_amount or 0.0), 4)
        order_status_buckets = sorted(status_rows.values(), key=lambda item: item['orderStatusNormalized'])

        currency_rows: dict[str, dict[str, Any]] = {}
        for line in order_lines:
            currency = self._clean_str(line.currency_code, settings.DEFAULT_CURRENCY)
            bucket = currency_rows.setdefault(
                currency,
                {
                    'currencyCode': currency,
                    'orderLineCount': 0,
                    'salesAmountTotal': 0.0,
                    'discountAmountTotal': 0.0,
                    'refundAmountTotal': 0.0,
                    'netSalesAmountTotal': 0.0,
                },
            )
            sales = float(line.sales_amount or 0.0)
            discount = float(line.discount_amount or 0.0)
            refund = float(line.refund_amount or 0.0)
            bucket['orderLineCount'] += 1
            bucket['salesAmountTotal'] = round(bucket['salesAmountTotal'] + sales, 4)
            bucket['discountAmountTotal'] = round(bucket['discountAmountTotal'] + discount, 4)
            bucket['refundAmountTotal'] = round(bucket['refundAmountTotal'] + refund, 4)
            bucket['netSalesAmountTotal'] = round(bucket['netSalesAmountTotal'] + sales - discount - refund, 4)
        currency_buckets = sorted(currency_rows.values(), key=lambda item: item['currencyCode'])

        provider_rows: dict[str, dict[str, Any]] = {}
        for header in order_headers:
            provider = self._clean_str(header.provider_code, 'generic')
            bucket = provider_rows.setdefault(
                provider,
                {
                    'providerCode': provider,
                    'orderHeaderCount': 0,
                    'orderLineCount': 0,
                    'identityCount': 0,
                    'bridgeCount': 0,
                    'unresolvedLineCount': 0,
                },
            )
            bucket['orderHeaderCount'] += 1
        for line in order_lines:
            payload = dict(line.payload or {})
            provider = self._clean_str(payload.get('providerCode'), 'generic')
            bucket = provider_rows.setdefault(
                provider,
                {
                    'providerCode': provider,
                    'orderHeaderCount': 0,
                    'orderLineCount': 0,
                    'identityCount': 0,
                    'bridgeCount': 0,
                    'unresolvedLineCount': 0,
                },
            )
            bucket['orderLineCount'] += 1
            canonical = self._clean_str(line.canonical_sku)
            if (not line.sku_id) or canonical.startswith('batch-'):
                bucket['unresolvedLineCount'] += 1
        for row in identities:
            provider = self._clean_str(row.provider_code, 'generic')
            provider_rows.setdefault(
                provider,
                {
                    'providerCode': provider,
                    'orderHeaderCount': 0,
                    'orderLineCount': 0,
                    'identityCount': 0,
                    'bridgeCount': 0,
                    'unresolvedLineCount': 0,
                },
            )['identityCount'] += 1
        for row in bridges:
            provider = self._clean_str(row.provider_code, 'generic')
            provider_rows.setdefault(
                provider,
                {
                    'providerCode': provider,
                    'orderHeaderCount': 0,
                    'orderLineCount': 0,
                    'identityCount': 0,
                    'bridgeCount': 0,
                    'unresolvedLineCount': 0,
                },
            )['bridgeCount'] += 1
        provider_buckets = sorted(provider_rows.values(), key=lambda item: item['providerCode'])

        unresolved_rows: dict[str, dict[str, Any]] = {}
        for line in order_lines:
            canonical = self._clean_str(line.canonical_sku)
            if canonical.startswith('batch-'):
                reason = 'surrogate_canonical_sku'
            elif not line.sku_id:
                reason = 'missing_sku_identity'
            else:
                reason = 'resolved'
            bucket = unresolved_rows.setdefault(reason, {'reason': reason, 'lineCount': 0})
            bucket['lineCount'] += 1
        unresolved_reason_buckets = [
            unresolved_rows[key] for key in ['resolved', 'surrogate_canonical_sku', 'missing_sku_identity'] if key in unresolved_rows
        ]

        confidence_rows = {'high': 0, 'medium': 0, 'low': 0}
        for row in identities:
            confidence = float(row.match_confidence or 0.0)
            if confidence >= 0.95:
                confidence_rows['high'] += 1
            elif confidence >= 0.8:
                confidence_rows['medium'] += 1
            else:
                confidence_rows['low'] += 1
        identity_confidence_buckets = [
            {'bucket': bucket, 'identityCount': count} for bucket, count in confidence_rows.items()
        ]

        source_key_rows = Counter()
        for row in identities:
            source_key_rows[self._clean_str(row.source_key_type, 'unknown')] += 1
        source_key_type_buckets = [
            {'sourceKeyType': key, 'identityCount': count} for key, count in sorted(source_key_rows.items(), key=lambda item: item[0])
        ]

        return {
            'orderStatusBuckets': order_status_buckets,
            'currencyBuckets': currency_buckets,
            'providerBuckets': provider_buckets,
            'unresolvedReasonBuckets': unresolved_reason_buckets,
            'identityConfidenceBuckets': identity_confidence_buckets,
            'sourceKeyTypeBuckets': source_key_type_buckets,
        }

    def _normalize_fact_view(self, view: str | None) -> str:
        normalized = self._clean_str(view, 'all').lower() or 'all'
        aliases = {
            'all': 'all',
            'ready': 'ready',
            'ready_only': 'ready',
            'readyonly': 'ready',
            'issues': 'issues',
            'issue': 'issues',
            'unresolved': 'issues',
        }
        resolved = aliases.get(normalized)
        if not resolved:
            raise ValueError('unsupported_fact_view')
        return resolved

    def _normalize_fact_preset(self, preset: str | None) -> str:
        normalized = self._clean_str(preset, 'debug_full').lower() or 'debug_full'
        aliases = {
            'economics_v1': 'economics_v1',
            'economics': 'economics_v1',
            'ops_review_v1': 'ops_review_v1',
            'ops_review': 'ops_review_v1',
            'debug_full': 'debug_full',
            'debug': 'debug_full',
            'full': 'debug_full',
        }
        resolved = aliases.get(normalized)
        if not resolved:
            raise ValueError('unsupported_fact_preset')
        return resolved

    def _build_fact_contract(self, batch_id: int) -> Dict[str, Any]:
        preset_specs = []
        for preset_name in ('economics_v1', 'ops_review_v1', 'debug_full'):
            fields = list(self.FACT_PRESET_FIELDS.get(preset_name) or [])
            preset_specs.append({
                'preset': preset_name,
                'fieldCount': len(fields) if fields else None,
                'fields': fields or None,
                'isDebug': preset_name == 'debug_full',
            })
        return {
            'contractName': 'order_object_fact_read_model',
            'contractVersion': self.CONTRACT_VERSION,
            'defaultView': 'all',
            'defaultPreset': 'debug_full',
            'recommendedConsumerPreset': 'economics_v1',
            'readinessField': 'factReady',
            'primaryKeyFields': ['factDate', 'shopId', 'canonicalSku', 'currencyCode', 'providerCode', 'unresolvedReason'],
            'partitionFields': ['factDate', 'shopId', 'providerCode'],
            'availableViews': ['all', 'ready', 'issues'],
            'availablePresets': preset_specs,
            'fieldGroups': {
                'dimensions': ['factDate', 'shopId', 'skuId', 'canonicalSku', 'currencyCode', 'providerCode'],
                'measures': [
                    'orderedQty',
                    'deliveredQty',
                    'returnedQty',
                    'cancelledQtyEstimated',
                    'orderedAmount',
                    'deliveredAmountEstimated',
                    'discountAmount',
                    'refundAmount',
                    'platformFeeAmount',
                    'fulfillmentFeeAmount',
                    'netSalesAmount',
                ],
                'quality': ['factReady', 'unresolvedReason', 'identityConfidenceBucket', 'identityConfidence'],
            },
            'exportFileStem': f'batch_{batch_id}_object_facts',
        }

    def _filter_fact_rows(self, rows: list[Dict[str, Any]], *, view: str) -> list[Dict[str, Any]]:
        if view == 'ready':
            return [dict(row) for row in rows if row.get('factReady') is True]
        if view == 'issues':
            return [dict(row) for row in rows if row.get('factReady') is False]
        return [dict(row) for row in rows]

    def _project_fact_rows(self, rows: list[Dict[str, Any]], *, preset: str) -> tuple[list[Dict[str, Any]], list[str] | None]:
        fields = list(self.FACT_PRESET_FIELDS.get(preset) or [])
        if not fields:
            return [dict(row) for row in rows], None
        return ([{field: row.get(field) for field in fields} for row in rows], fields)

    def _build_fact_read_model(self, state: Dict[str, Any]) -> Dict[str, Any]:
        order_headers = list(state.get('orderHeaders') or [])
        order_lines = list(state.get('orderLines') or [])
        identities = list(state.get('identities') or [])

        headers_by_id = {int(row.id): row for row in order_headers}
        confidence_by_canonical: dict[str, float] = {}
        for row in identities:
            canonical = self._clean_str(row.canonical_entity_id)
            if not canonical:
                continue
            current = confidence_by_canonical.get(canonical)
            confidence = float(row.match_confidence or 0.0)
            if current is None or confidence > current:
                confidence_by_canonical[canonical] = confidence

        fact_rows: dict[tuple[Any, ...], Dict[str, Any]] = {}
        for line in order_lines:
            header = headers_by_id.get(int(line.order_id or 0))
            payload = dict(line.payload or {})
            canonical_sku = self._clean_str(line.canonical_sku) or None
            provider_code = self._clean_str(payload.get('providerCode') or (header.provider_code if header else None), 'generic')
            currency_code = self._clean_str(line.currency_code or (header.currency_code if header else None), settings.DEFAULT_CURRENCY)
            fact_date = None
            if header and header.ordered_at:
                fact_date = header.ordered_at.date().isoformat()
            confidence = float(confidence_by_canonical.get(canonical_sku or '', 0.55 if canonical_sku and canonical_sku.startswith('batch-') else 1.0))
            unresolved_reason = None
            if canonical_sku and canonical_sku.startswith('batch-'):
                unresolved_reason = 'surrogate_canonical_sku'
            elif not line.sku_id:
                unresolved_reason = 'missing_sku_identity'
            key = (
                fact_date,
                int(header.shop_id if header else 0),
                int(line.sku_id or 0),
                canonical_sku or '',
                currency_code,
                provider_code,
                unresolved_reason or 'resolved',
            )
            bucket = fact_rows.setdefault(
                key,
                {
                    'factDate': fact_date,
                    'shopId': int(header.shop_id if header else 0),
                    'skuId': int(line.sku_id) if line.sku_id else None,
                    'canonicalSku': canonical_sku,
                    'currencyCode': currency_code,
                    'providerCode': provider_code,
                    'identityConfidenceBucket': self._confidence_bucket(confidence),
                    'identityConfidence': round(confidence, 4),
                    'orderHeaderCount': 0,
                    'orderLineCount': 0,
                    'orderedQty': 0.0,
                    'deliveredQty': 0.0,
                    'returnedQty': 0.0,
                    'cancelledQtyEstimated': 0.0,
                    'orderedAmount': 0.0,
                    'deliveredAmountEstimated': 0.0,
                    'discountAmount': 0.0,
                    'refundAmount': 0.0,
                    'platformFeeAmount': 0.0,
                    'fulfillmentFeeAmount': 0.0,
                    'netSalesAmount': 0.0,
                    'factReady': unresolved_reason is None,
                    'unresolvedReason': unresolved_reason,
                },
            )
            bucket['orderLineCount'] += 1
            if header is not None:
                bucket.setdefault('_header_ids', set()).add(int(header.id))
            ordered_qty = float(line.qty_ordered or 0.0)
            delivered_qty = float(line.qty_delivered or 0.0)
            returned_qty = float(line.qty_returned or 0.0)
            sales_amount = float(line.sales_amount or 0.0)
            discount_amount = float(line.discount_amount or 0.0)
            refund_amount = float(line.refund_amount or 0.0)
            platform_fee_amount = float(line.platform_fee_amount or 0.0)
            fulfillment_fee_amount = float(line.fulfillment_fee_amount or 0.0)
            cancelled_qty = max(ordered_qty - delivered_qty, 0.0)
            delivered_amount_est = sales_amount if delivered_qty > 0 else 0.0
            bucket['orderedQty'] = round(bucket['orderedQty'] + ordered_qty, 4)
            bucket['deliveredQty'] = round(bucket['deliveredQty'] + delivered_qty, 4)
            bucket['returnedQty'] = round(bucket['returnedQty'] + returned_qty, 4)
            bucket['cancelledQtyEstimated'] = round(bucket['cancelledQtyEstimated'] + cancelled_qty, 4)
            bucket['orderedAmount'] = round(bucket['orderedAmount'] + sales_amount, 4)
            bucket['deliveredAmountEstimated'] = round(bucket['deliveredAmountEstimated'] + delivered_amount_est, 4)
            bucket['discountAmount'] = round(bucket['discountAmount'] + discount_amount, 4)
            bucket['refundAmount'] = round(bucket['refundAmount'] + refund_amount, 4)
            bucket['platformFeeAmount'] = round(bucket['platformFeeAmount'] + platform_fee_amount, 4)
            bucket['fulfillmentFeeAmount'] = round(bucket['fulfillmentFeeAmount'] + fulfillment_fee_amount, 4)
            bucket['netSalesAmount'] = round(bucket['netSalesAmount'] + sales_amount - discount_amount - refund_amount, 4)
            if not bucket['factReady']:
                bucket['identityConfidenceBucket'] = 'low'
                bucket['identityConfidence'] = min(bucket['identityConfidence'], confidence)

        rows = []
        for row in fact_rows.values():
            row['orderHeaderCount'] = len(row.pop('_header_ids', set()))
            rows.append(row)
        rows.sort(key=lambda item: (item['factDate'] or '', item['canonicalSku'] or '', item['providerCode'] or ''))

        readiness = {
            'factRowCount': len(rows),
            'factReadyRowCount': sum(1 for row in rows if row['factReady']),
            'unresolvedFactRowCount': sum(1 for row in rows if not row['factReady']),
            'distinctFactDateCount': len({row['factDate'] for row in rows if row['factDate']}),
            'distinctCanonicalSkuCount': len({row['canonicalSku'] for row in rows if row['canonicalSku']}),
            'distinctCurrencyCount': len({row['currencyCode'] for row in rows if row['currencyCode']}),
        }
        readiness['factReadyRate'] = round(
            (readiness['factReadyRowCount'] / readiness['factRowCount']) if readiness['factRowCount'] else 0.0,
            4,
        )
        return {'rows': rows, 'readiness': readiness}

    def get_batch_object_facts(
        self,
        batch_ref: str,
        *,
        limit: int = 50,
        offset: int = 0,
        view: str = 'all',
        preset: str = 'debug_full',
    ) -> Optional[Dict[str, Any]]:
        state = self._load_batch_object_state(batch_ref)
        if not state:
            return None
        detail = dict(state['detail'])
        events = list(state['events'])
        aggregate_metrics = self._build_aggregate_metrics(state)
        identity_diagnostics = self._build_identity_diagnostics(state)
        fact_model = self._build_fact_read_model(state)
        normalized_view = self._normalize_fact_view(view)
        normalized_preset = self._normalize_fact_preset(preset)
        filtered_rows = self._filter_fact_rows(fact_model['rows'], view=normalized_view)
        safe_offset = max(int(offset or 0), 0)
        safe_limit = min(max(int(limit or 50), 1), 200)
        page, page_info = self._paginate_rows(filtered_rows, offset=safe_offset, limit=safe_limit)
        projected_page, column_order = self._project_fact_rows(page, preset=normalized_preset)
        contract = self._build_fact_contract(state['batchId'])
        return {
            'batchId': state['batchId'],
            'datasetKind': detail.get('datasetKind'),
            'contractVersion': self.CONTRACT_VERSION,
            'status': 'completed' if events else 'pending',
            'view': normalized_view,
            'preset': normalized_preset,
            'columnOrder': column_order,
            'pagination': page_info,
            'aggregateMetrics': aggregate_metrics,
            'identityDiagnostics': identity_diagnostics,
            'factReadiness': fact_model['readiness'],
            'exportSpec': {
                'fileStem': contract['exportFileStem'],
                'suggestedFileName': f"{contract['exportFileStem']}_{normalized_preset}_{normalized_view}.json",
                'selectedColumns': column_order,
            },
            'items': projected_page,
        }

    def get_batch_object_fact_contract(self, batch_ref: str) -> Optional[Dict[str, Any]]:
        state = self._load_batch_object_state(batch_ref)
        if not state:
            return None
        detail = dict(state['detail'])
        events = list(state['events'])
        aggregate_metrics = self._build_aggregate_metrics(state)
        identity_diagnostics = self._build_identity_diagnostics(state)
        fact_model = self._build_fact_read_model(state)
        return {
            'batchId': state['batchId'],
            'datasetKind': detail.get('datasetKind'),
            'contractVersion': self.CONTRACT_VERSION,
            'status': 'completed' if events else 'pending',
            'aggregateMetrics': aggregate_metrics,
            'identityDiagnostics': identity_diagnostics,
            'factReadiness': fact_model['readiness'],
            'consumerContract': self._build_fact_contract(state['batchId']),
        }

    def get_batch_object_diagnostics(self, batch_ref: str) -> Optional[Dict[str, Any]]:
        state = self._load_batch_object_state(batch_ref)
        if not state:
            return None
        detail = dict(state['detail'])
        events = list(state['events'])
        aggregate_metrics = self._build_aggregate_metrics(state)
        identity_diagnostics = self._build_identity_diagnostics(state)
        return {
            'batchId': state['batchId'],
            'datasetKind': detail.get('datasetKind'),
            'contractVersion': self.CONTRACT_VERSION,
            'status': 'completed' if events else 'pending',
            'aggregateMetrics': aggregate_metrics,
            'identityDiagnostics': identity_diagnostics,
            'assemblyEventHistory': self._build_event_history(events),
        }

    def get_batch_object_rollups(self, batch_ref: str) -> Optional[Dict[str, Any]]:
        state = self._load_batch_object_state(batch_ref)
        if not state:
            return None
        detail = dict(state['detail'])
        events = list(state['events'])
        aggregate_metrics = self._build_aggregate_metrics(state)
        identity_diagnostics = self._build_identity_diagnostics(state)
        return {
            'batchId': state['batchId'],
            'datasetKind': detail.get('datasetKind'),
            'contractVersion': self.CONTRACT_VERSION,
            'status': 'completed' if events else 'pending',
            'aggregateMetrics': aggregate_metrics,
            'identityDiagnostics': identity_diagnostics,
            'rollups': self._build_rollups(state),
        }
