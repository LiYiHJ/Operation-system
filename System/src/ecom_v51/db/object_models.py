from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class EntityIdentityMap(Base, TimestampMixin):
    __tablename__ = 'entity_identity_map'
    __table_args__ = (
        UniqueConstraint(
            'entity_type',
            'provider_code',
            'source_key_type',
            'source_key_value',
            name='uq_entity_identity_map_lookup',
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    canonical_entity_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_code: Mapped[str] = mapped_column(String(64), nullable=False)
    source_key_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_key_value: Mapped[str] = mapped_column(String(255), nullable=False)
    match_method: Mapped[str] = mapped_column(String(64), nullable=False, default='batch_object_assembly')
    match_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source_batch_id: Mapped[int | None] = mapped_column(ForeignKey('ingest_batch.id'), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class SkuIdentityBridge(Base, TimestampMixin):
    __tablename__ = 'sku_identity_bridge'
    __table_args__ = (
        UniqueConstraint('shop_id', 'canonical_sku', name='uq_sku_identity_bridge_shop_canonical_sku'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey('dim_shop.id'), nullable=False)
    sku_id: Mapped[int | None] = mapped_column(ForeignKey('dim_sku.id'), nullable=True)
    canonical_sku: Mapped[str] = mapped_column(String(128), nullable=False)
    primary_source_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_code: Mapped[str] = mapped_column(String(64), nullable=False, default='generic')
    match_method: Mapped[str] = mapped_column(String(64), nullable=False, default='batch_object_assembly')
    match_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    source_batch_id: Mapped[int | None] = mapped_column(ForeignKey('ingest_batch.id'), nullable=True)
    source_meta: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class OrderHeader(Base, TimestampMixin):
    __tablename__ = 'order_header'
    __table_args__ = (
        UniqueConstraint('shop_id', 'external_order_no', name='uq_order_header_shop_external_order_no'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey('dim_shop.id'), nullable=False)
    platform_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    external_order_no: Mapped[str] = mapped_column(String(128), nullable=False)
    order_status_normalized: Mapped[str | None] = mapped_column(String(64), nullable=True)
    currency_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    ordered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    buyer_country: Mapped[str | None] = mapped_column(String(16), nullable=True)
    provider_code: Mapped[str] = mapped_column(String(64), nullable=False, default='generic')
    source_batch_id: Mapped[int | None] = mapped_column(ForeignKey('ingest_batch.id'), nullable=True)
    source_row_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class OrderLine(Base, TimestampMixin):
    __tablename__ = 'order_line'
    __table_args__ = (
        UniqueConstraint('order_id', 'line_no', name='uq_order_line_order_line_no'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey('order_header.id'), nullable=False)
    line_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    sku_id: Mapped[int | None] = mapped_column(ForeignKey('dim_sku.id'), nullable=True)
    canonical_sku: Mapped[str | None] = mapped_column(String(128), nullable=True)
    platform_line_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    qty_ordered: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    qty_delivered: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    qty_returned: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    sales_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    discount_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    platform_fee_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fulfillment_fee_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    refund_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    currency_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    source_batch_id: Mapped[int | None] = mapped_column(ForeignKey('ingest_batch.id'), nullable=True)
    source_row_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
