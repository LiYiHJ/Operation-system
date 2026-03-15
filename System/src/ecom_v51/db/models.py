from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


# -----------------------------
# Dimension tables
# -----------------------------
class DimPlatform(Base, TimestampMixin):
    __tablename__ = "dim_platform"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    platform_name: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class DimShop(Base, TimestampMixin):
    __tablename__ = "dim_shop"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform_id: Mapped[int] = mapped_column(ForeignKey("dim_platform.id"), nullable=False)
    shop_code: Mapped[str] = mapped_column(String(64), nullable=False)
    shop_name: Mapped[str] = mapped_column(String(255), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(8), default="RUB", nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Moscow", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)


class DimCategory(Base, TimestampMixin):
    __tablename__ = "dim_category"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform_id: Mapped[int] = mapped_column(ForeignKey("dim_platform.id"), nullable=False)
    category_code: Mapped[str] = mapped_column(String(128), nullable=False)
    category_name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_category_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    category_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)


class DimProduct(Base, TimestampMixin):
    __tablename__ = "dim_product"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("dim_shop.id"), nullable=False)
    product_code: Mapped[str] = mapped_column(String(128), nullable=False)
    product_name: Mapped[str] = mapped_column(String(512), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("dim_category.id"), nullable=True)
    spu_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)


class DimSku(Base, TimestampMixin):
    __tablename__ = "dim_sku"
    __table_args__ = (
        UniqueConstraint("shop_id", "sku", name="uq_dim_sku_shop_sku"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("dim_shop.id"), nullable=False)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("dim_product.id"), nullable=True)
    sku: Mapped[str] = mapped_column(String(128), nullable=False)
    offer_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    seller_sku: Mapped[str | None] = mapped_column(String(128), nullable=True)
    external_sku: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sku_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    variant_text: Mapped[str | None] = mapped_column(String(512), nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class DimCampaign(Base, TimestampMixin):
    __tablename__ = "dim_campaign"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("dim_shop.id"), nullable=False)
    campaign_code: Mapped[str] = mapped_column(String(128), nullable=False)
    campaign_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)


class DimDate(Base):
    __tablename__ = "dim_date"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date_value: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    day: Mapped[int] = mapped_column(Integer, nullable=False)
    week_of_year: Mapped[int] = mapped_column(Integer, nullable=False)


class FxRateDaily(Base, TimestampMixin):
    __tablename__ = "fx_rate_daily"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date_id: Mapped[int] = mapped_column(ForeignKey("dim_date.id"), nullable=False)
    from_currency: Mapped[str] = mapped_column(String(8), nullable=False)
    to_currency: Mapped[str] = mapped_column(String(8), nullable=False)
    rate: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)


# -----------------------------
# Fact tables
# -----------------------------
class FactSkuDaily(Base, TimestampMixin):
    __tablename__ = "fact_sku_daily"
    __table_args__ = (
        UniqueConstraint("date_id", "shop_id", "sku_id", name="uq_fact_sku_daily_date_shop_sku"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date_id: Mapped[int] = mapped_column(ForeignKey("dim_date.id"), nullable=False)
    shop_id: Mapped[int] = mapped_column(ForeignKey("dim_shop.id"), nullable=False)
    sku_id: Mapped[int] = mapped_column(ForeignKey("dim_sku.id"), nullable=False)
    impressions_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    impressions_search: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    card_visits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    add_to_cart_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    orders_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    delivered_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cancelled_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    returned_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    revenue_ordered: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    revenue_delivered: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    batch_id: Mapped[int] = mapped_column(ForeignKey("import_batch.id"), nullable=False)




class FactSkuExtDaily(Base, TimestampMixin):
    __tablename__ = "fact_sku_ext_daily"
    __table_args__ = (
        UniqueConstraint("date_id", "shop_id", "sku_id", name="uq_fact_sku_ext_daily_date_shop_sku"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date_id: Mapped[int] = mapped_column(ForeignKey("dim_date.id"), nullable=False)
    shop_id: Mapped[int] = mapped_column(ForeignKey("dim_shop.id"), nullable=False)
    sku_id: Mapped[int] = mapped_column(ForeignKey("dim_sku.id"), nullable=False)
    items_purchased: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    promo_days_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    discount_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    price_index_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("import_batch.id"), nullable=False)


class FactAdsDaily(Base, TimestampMixin):
    __tablename__ = "fact_ads_daily"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date_id: Mapped[int] = mapped_column(ForeignKey("dim_date.id"), nullable=False)
    shop_id: Mapped[int] = mapped_column(ForeignKey("dim_shop.id"), nullable=False)
    sku_id: Mapped[int] = mapped_column(ForeignKey("dim_sku.id"), nullable=False)
    campaign_id: Mapped[int | None] = mapped_column(ForeignKey("dim_campaign.id"), nullable=True)
    ad_spend: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    ad_clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ad_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ad_revenue: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cpc: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    roas: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    batch_id: Mapped[int] = mapped_column(ForeignKey("import_batch.id"), nullable=False)


class FactInventoryDaily(Base, TimestampMixin):
    __tablename__ = "fact_inventory_daily"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date_id: Mapped[int] = mapped_column(ForeignKey("dim_date.id"), nullable=False)
    shop_id: Mapped[int] = mapped_column(ForeignKey("dim_shop.id"), nullable=False)
    sku_id: Mapped[int] = mapped_column(ForeignKey("dim_sku.id"), nullable=False)
    stock_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stock_fbo: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stock_fbs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    days_of_supply: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    batch_id: Mapped[int] = mapped_column(ForeignKey("import_batch.id"), nullable=False)


class FactOrdersDaily(Base, TimestampMixin):
    __tablename__ = "fact_orders_daily"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date_id: Mapped[int] = mapped_column(ForeignKey("dim_date.id"), nullable=False)
    shop_id: Mapped[int] = mapped_column(ForeignKey("dim_shop.id"), nullable=False)
    sku_id: Mapped[int] = mapped_column(ForeignKey("dim_sku.id"), nullable=False)
    ordered_qty: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    delivered_qty: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cancelled_qty: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    returned_qty: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ordered_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    delivered_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    batch_id: Mapped[int] = mapped_column(ForeignKey("import_batch.id"), nullable=False)


class FactReviewsDaily(Base, TimestampMixin):
    __tablename__ = "fact_reviews_daily"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date_id: Mapped[int] = mapped_column(ForeignKey("dim_date.id"), nullable=False)
    shop_id: Mapped[int] = mapped_column(ForeignKey("dim_shop.id"), nullable=False)
    sku_id: Mapped[int] = mapped_column(ForeignKey("dim_sku.id"), nullable=False)
    rating_avg: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    new_reviews_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    negative_reviews_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quality_risk_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    batch_id: Mapped[int] = mapped_column(ForeignKey("import_batch.id"), nullable=False)


class FactProfitSnapshot(Base, TimestampMixin):
    __tablename__ = "fact_profit_snapshot"
    __table_args__ = (
        UniqueConstraint("date_id", "shop_id", "sku_id", name="uq_fact_profit_snapshot_date_shop_sku"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date_id: Mapped[int] = mapped_column(ForeignKey("dim_date.id"), nullable=False)
    shop_id: Mapped[int] = mapped_column(ForeignKey("dim_shop.id"), nullable=False)
    sku_id: Mapped[int] = mapped_column(ForeignKey("dim_sku.id"), nullable=False)
    sale_price: Mapped[float] = mapped_column(Float, nullable=False)
    list_price: Mapped[float] = mapped_column(Float, nullable=False)
    fixed_cost_total: Mapped[float] = mapped_column(Float, nullable=False)
    variable_rate_total: Mapped[float] = mapped_column(Float, nullable=False)
    base_profit: Mapped[float] = mapped_column(Float, nullable=False)
    contribution_profit: Mapped[float] = mapped_column(Float, nullable=False)
    post_fulfillment_profit: Mapped[float] = mapped_column(Float, nullable=False)
    net_profit: Mapped[float] = mapped_column(Float, nullable=False)
    net_margin: Mapped[float] = mapped_column(Float, nullable=False)
    break_even_price: Mapped[float] = mapped_column(Float, nullable=False)
    break_even_discount_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    batch_id: Mapped[int] = mapped_column(ForeignKey("import_batch.id"), nullable=False)


# -----------------------------
# Domain tables
# -----------------------------
class SkuPriceMaster(Base, TimestampMixin):
    __tablename__ = "sku_price_master"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("dim_shop.id"), nullable=False)
    sku_id: Mapped[int] = mapped_column(ForeignKey("dim_sku.id"), nullable=False)
    list_price: Mapped[float] = mapped_column(Float, nullable=False)
    sale_price: Mapped[float] = mapped_column(Float, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False)
    price_index: Mapped[float | None] = mapped_column(Float, nullable=True)


class SkuCostMaster(Base, TimestampMixin):
    __tablename__ = "sku_cost_master"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("dim_shop.id"), nullable=False)
    sku_id: Mapped[int] = mapped_column(ForeignKey("dim_sku.id"), nullable=False)
    purchase_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    first_leg_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    packaging_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    fulfillment_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    warehouse_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    last_mile_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    other_fixed_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


class PriceChangeLog(Base, TimestampMixin):
    __tablename__ = "price_change_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("dim_shop.id"), nullable=False)
    sku_id: Mapped[int] = mapped_column(ForeignKey("dim_sku.id"), nullable=False)
    old_price: Mapped[float] = mapped_column(Float, nullable=False)
    new_price: Mapped[float] = mapped_column(Float, nullable=False)
    change_type: Mapped[str] = mapped_column(String(64), nullable=False)
    change_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    operator: Mapped[str | None] = mapped_column(String(64), nullable=True)


class CompetitorPriceSnapshot(Base, TimestampMixin):
    __tablename__ = "competitor_price_snapshot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("dim_shop.id"), nullable=False)
    sku_id: Mapped[int] = mapped_column(ForeignKey("dim_sku.id"), nullable=False)
    competitor_name: Mapped[str] = mapped_column(String(128), nullable=False)
    competitor_sku: Mapped[str | None] = mapped_column(String(128), nullable=True)
    competitor_price: Mapped[float] = mapped_column(Float, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PromotionEvent(Base, TimestampMixin):
    __tablename__ = "promotion_event"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("dim_shop.id"), nullable=False)
    sku_id: Mapped[int] = mapped_column(ForeignKey("dim_sku.id"), nullable=False)
    promotion_type: Mapped[str] = mapped_column(String(64), nullable=False)
    discount_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    seller_subsidy_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="planned", nullable=False)


class ProfitAssumptionProfile(Base, TimestampMixin):
    __tablename__ = "profit_assumption_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("dim_shop.id"), nullable=False)
    profile_name: Mapped[str] = mapped_column(String(128), nullable=False)
    ad_allocation_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    tax_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    service_fee_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    fx_loss_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ProfitAllocationRule(Base, TimestampMixin):
    __tablename__ = "profit_allocation_rule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("dim_shop.id"), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False)
    scope_id: Mapped[int] = mapped_column(Integer, nullable=False)
    rule_type: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_value: Mapped[float] = mapped_column(Float, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


# -----------------------------
# System tables
# -----------------------------
class ImportBatch(Base, TimestampMixin):
    __tablename__ = "import_batch"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    platform_code: Mapped[str] = mapped_column(String(32), nullable=False)
    shop_id: Mapped[int | None] = mapped_column(ForeignKey("dim_shop.id"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    message: Mapped[str | None] = mapped_column(String(512), nullable=True)


class ImportBatchFile(Base, TimestampMixin):
    __tablename__ = "import_batch_file"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("import_batch.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sheet_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    detected_header_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detected_key_field: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mapped_fields_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    unmapped_fields_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)


class ImportStagingRow(Base, TimestampMixin):
    __tablename__ = "import_staging_row"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("import_batch.id"), nullable=False)
    batch_file_id: Mapped[int] = mapped_column(ForeignKey("import_batch_file.id"), nullable=False)
    row_no: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default='staged', nullable=False)
    sku: Mapped[str | None] = mapped_column(String(128), nullable=True)
    row_data_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    row_error_summary_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


class ImportErrorLog(Base, TimestampMixin):
    __tablename__ = "import_error_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_file_id: Mapped[int] = mapped_column(ForeignKey("import_batch_file.id"), nullable=False)
    row_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    column_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_type: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str] = mapped_column(String(512), nullable=False)


class MappingFeedback(Base, TimestampMixin):
    __tablename__ = "mapping_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform_code: Mapped[str] = mapped_column(String(32), nullable=False)
    raw_field_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mapped_field_name: Mapped[str] = mapped_column(String(128), nullable=False)
    confirmed_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class StrategyTask(Base, TimestampMixin):
    __tablename__ = "strategy_task"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("dim_shop.id"), nullable=False)
    sku_id: Mapped[int | None] = mapped_column(ForeignKey("dim_sku.id"), nullable=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("dim_category.id"), nullable=True)
    strategy_type: Mapped[str] = mapped_column(String(64), nullable=False)
    priority: Mapped[str] = mapped_column(String(8), nullable=False)
    trigger_rule: Mapped[str | None] = mapped_column(String(255), nullable=True)
    issue_summary: Mapped[str] = mapped_column(String(512), nullable=False)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)
    risk_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    observation_metrics_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    owner: Mapped[str | None] = mapped_column(String(64), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class AlertEvent(Base, TimestampMixin):
    __tablename__ = "alert_event"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("dim_shop.id"), nullable=False)
    sku_id: Mapped[int | None] = mapped_column(ForeignKey("dim_sku.id"), nullable=True)
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    message: Mapped[str] = mapped_column(String(512), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)


class ReportSnapshot(Base, TimestampMixin):
    __tablename__ = "report_snapshot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("dim_shop.id"), nullable=False)
    report_type: Mapped[str] = mapped_column(String(32), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    content_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UserAccount(Base, TimestampMixin):
    __tablename__ = "user_account"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="operator")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")


class ReminderReadState(Base, TimestampMixin):
    __tablename__ = "reminder_read_state"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_reminder_read_state_user"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_account.id"), nullable=False)
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ExecutionLog(Base, TimestampMixin):
    __tablename__ = "execution_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_task_id: Mapped[int] = mapped_column(ForeignKey("strategy_task.id"), nullable=False)
    source_page: Mapped[str] = mapped_column(String(64), nullable=False)
    action_before: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_after: Mapped[str | None] = mapped_column(Text, nullable=True)
    operator: Mapped[str] = mapped_column(String(64), nullable=False)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    result_summary: Mapped[str] = mapped_column(String(512), nullable=False)
    status_before: Mapped[str] = mapped_column(String(32), nullable=False)
    status_after: Mapped[str] = mapped_column(String(32), nullable=False)
    extra_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class ExternalDataSourceConfig(Base, TimestampMixin):
    __tablename__ = "external_data_source_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_sync_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sync_frequency: Mapped[str] = mapped_column(String(32), default='manual', nullable=False)
    credentials_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    settings_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_sync_error: Mapped[str | None] = mapped_column(String(512), nullable=True)


class SyncRunLog(Base, TimestampMixin):
    __tablename__ = "sync_run_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger_mode: Mapped[str] = mapped_column(String(32), default='manual', nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    imported_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    batch_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    message: Mapped[str | None] = mapped_column(String(512), nullable=True)


class PushDeliveryLog(Base, TimestampMixin):
    __tablename__ = "push_delivery_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_task_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    execution_log_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_system: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    response_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    pushed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
