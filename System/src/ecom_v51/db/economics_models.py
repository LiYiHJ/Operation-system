from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class RegistryCostComponent(Base, TimestampMixin):
    __tablename__ = 'registry_cost_component'
    __table_args__ = (
        UniqueConstraint('component_code', name='uq_registry_cost_component_code'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    component_code: Mapped[str] = mapped_column(String(64), nullable=False)
    component_name: Mapped[str] = mapped_column(String(128), nullable=False)
    component_scope: Mapped[str] = mapped_column(String(64), nullable=False, default='sku')
    source_mode_default: Mapped[str] = mapped_column(String(64), nullable=False, default='rule_estimate')
    confidence_default: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    version_label: Mapped[str] = mapped_column(String(64), nullable=False, default='v1')
    affects_profit_layer: Mapped[str] = mapped_column(String(64), nullable=False, default='base_contribution_profit')
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class RegistryProfitProfile(Base, TimestampMixin):
    __tablename__ = 'registry_profit_profile'
    __table_args__ = (
        UniqueConstraint('profile_code', name='uq_registry_profit_profile_code'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_code: Mapped[str] = mapped_column(String(64), nullable=False)
    profile_name: Mapped[str] = mapped_column(String(128), nullable=False)
    pricing_mode: Mapped[str] = mapped_column(String(64), nullable=False, default='balanced_profit')
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version_label: Mapped[str] = mapped_column(String(64), nullable=False, default='v1')
    layer_schema: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    explanation_schema: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class SkuCostCard(Base, TimestampMixin):
    __tablename__ = 'sku_cost_card'
    __table_args__ = (
        UniqueConstraint('shop_id', 'canonical_sku', 'profile_code', name='uq_sku_cost_card_shop_sku_profile'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int | None] = mapped_column(ForeignKey('dim_shop.id'), nullable=True)
    sku_id: Mapped[int | None] = mapped_column(ForeignKey('dim_sku.id'), nullable=True)
    canonical_sku: Mapped[str] = mapped_column(String(128), nullable=False)
    profile_code: Mapped[str] = mapped_column(String(64), nullable=False, default='default_profit_v1')
    currency_code: Mapped[str] = mapped_column(String(16), nullable=False, default='CNY')
    ads_cost_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    other_cost_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    source_mode: Mapped[str] = mapped_column(String(64), nullable=False, default='manual_override')
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)
    version_label: Mapped[str] = mapped_column(String(64), nullable=False, default='v1')
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    component_values: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
