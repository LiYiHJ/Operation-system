from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy import select

from ecom_v51.config.settings import settings
from ecom_v51.db.base import Base
from ecom_v51.db.economics_models import RegistryCostComponent, RegistryProfitProfile, SkuCostCard
from ecom_v51.db.models import DimSku
from ecom_v51.services.object_assembly_service import ObjectAssemblyService
from ecom_v51.db.session import get_engine, get_session


class EconomicsConfigService:
    CONTRACT_VERSION = 'p4.economics_config.v1'
    RESOLVE_CONTRACT_VERSION = 'p4.economics_config_resolve.v1'

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = Path(root_dir)

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
    def _to_bool(value: Any, default: bool = False) -> bool:
        if value in (None, ''):
            return default
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {'1', 'true', 'yes', 'y', 'on'}

    @staticmethod
    def _to_int(value: Any, default: int | None = None) -> int | None:
        if value in (None, ''):
            return default
        try:
            return int(value)
        except Exception:
            return default

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def _ensure_schema(self) -> None:
        from ecom_v51.db import economics_models  # noqa: F401
        from ecom_v51.db import models  # noqa: F401

        Base.metadata.create_all(bind=get_engine())

    def _seed_defaults(self) -> None:
        self._ensure_schema()
        default_components = [
            {
                'component_code': 'platform_fee',
                'component_name': '平台费',
                'component_scope': 'order_line',
                'source_mode_default': 'import_value',
                'confidence_default': 0.95,
                'version_label': 'v1',
                'affects_profit_layer': 'base_contribution_profit',
                'is_required': True,
                'payload': {'description': '来自订单/结算导入的站点平台费'},
            },
            {
                'component_code': 'fulfillment_fee',
                'component_name': '履约费',
                'component_scope': 'order_line',
                'source_mode_default': 'import_value',
                'confidence_default': 0.95,
                'version_label': 'v1',
                'affects_profit_layer': 'base_contribution_profit',
                'is_required': True,
                'payload': {'description': '来自订单/结算导入的履约费'},
            },
            {
                'component_code': 'ads_cost',
                'component_name': '广告成本',
                'component_scope': 'sku_daily',
                'source_mode_default': 'manual_override',
                'confidence_default': 0.7,
                'version_label': 'v1',
                'affects_profit_layer': 'profit_after_ads',
                'is_required': False,
                'payload': {'description': '后续与广告 facts 联动，当前先以成本卡占位'},
            },
            {
                'component_code': 'other_variable_cost',
                'component_name': '其他可变成本',
                'component_scope': 'sku',
                'source_mode_default': 'manual_override',
                'confidence_default': 0.6,
                'version_label': 'v1',
                'affects_profit_layer': 'base_contribution_profit',
                'is_required': False,
                'payload': {'description': '暂存包装/人工等其他可变成本占位'},
            },
        ]
        default_profile = {
            'profile_code': 'default_profit_v1',
            'profile_name': '默认三层利润口径 V1',
            'pricing_mode': 'balanced_profit',
            'is_default': True,
            'is_active': True,
            'version_label': 'v1',
            'layer_schema': {
                'layers': [
                    'base_contribution_profit',
                    'profit_after_ads',
                    'risk_adjusted_profit',
                ],
                'currentCoreState': 'transitional_facade',
            },
            'explanation_schema': {
                'requiredOutputs': [
                    'profit_confidence',
                    'cost_source_mix',
                    'uncertainty_band',
                    'dominant_driver',
                    'dominant_risk_driver',
                ]
            },
            'payload': {
                'notes': 'P4 Round1 先冻结配置契约；P3 Round2 /core 只作为临时 facade，不继续扩写。',
            },
        }
        with get_session() as session:
            for item in default_components:
                row = session.execute(
                    select(RegistryCostComponent).where(RegistryCostComponent.component_code == item['component_code'])
                ).scalar_one_or_none()
                if row is None:
                    session.add(RegistryCostComponent(**item))
            profile = session.execute(
                select(RegistryProfitProfile).where(RegistryProfitProfile.profile_code == default_profile['profile_code'])
            ).scalar_one_or_none()
            if profile is None:
                session.add(RegistryProfitProfile(**default_profile))

    def _get_object_service(self) -> ObjectAssemblyService:
        return ObjectAssemblyService(self.root_dir)

    @staticmethod
    def _coerce_component_value(card: dict[str, Any], component_code: str) -> float:
        component_values = dict(card.get('componentValues') or {})
        if component_code in component_values:
            try:
                return float(component_values.get(component_code) or 0.0)
            except Exception:
                return 0.0
        fallback_map = {
            'ads_cost': card.get('adsCostAmount'),
            'other_variable_cost': card.get('otherCostAmount'),
        }
        try:
            return float(fallback_map.get(component_code) or 0.0)
        except Exception:
            return 0.0

    def _get_default_profile_row(self, session) -> Optional[RegistryProfitProfile]:
        row = session.execute(
            select(RegistryProfitProfile)
            .where(RegistryProfitProfile.is_active.is_(True), RegistryProfitProfile.is_default.is_(True))
            .order_by(RegistryProfitProfile.id.asc())
        ).scalar_one_or_none()
        if row is not None:
            return row
        return session.execute(
            select(RegistryProfitProfile)
            .where(RegistryProfitProfile.is_active.is_(True))
            .order_by(RegistryProfitProfile.id.asc())
        ).scalar_one_or_none()

    def _find_cost_card_row(self, session, *, shop_id: int | None, canonical_sku: str, profile_code: str) -> Optional[SkuCostCard]:
        if shop_id is None or not canonical_sku:
            return None
        return session.execute(
            select(SkuCostCard).where(
                SkuCostCard.shop_id == shop_id,
                SkuCostCard.canonical_sku == canonical_sku,
                SkuCostCard.profile_code == profile_code,
                SkuCostCard.is_active.is_(True),
            )
        ).scalar_one_or_none()

    def _serialize_component(self, row: RegistryCostComponent) -> Dict[str, Any]:
        return {
            'id': int(row.id),
            'componentCode': row.component_code,
            'componentName': row.component_name,
            'componentScope': row.component_scope,
            'sourceModeDefault': row.source_mode_default,
            'confidenceDefault': float(row.confidence_default or 0.0),
            'versionLabel': row.version_label,
            'affectsProfitLayer': row.affects_profit_layer,
            'isRequired': bool(row.is_required),
            'isActive': bool(row.is_active),
            'payload': dict(row.payload or {}),
            'updatedAt': row.updated_at.isoformat() if row.updated_at else None,
        }

    def _serialize_profile(self, row: RegistryProfitProfile) -> Dict[str, Any]:
        return {
            'id': int(row.id),
            'profileCode': row.profile_code,
            'profileName': row.profile_name,
            'pricingMode': row.pricing_mode,
            'isDefault': bool(row.is_default),
            'isActive': bool(row.is_active),
            'versionLabel': row.version_label,
            'layerSchema': dict(row.layer_schema or {}),
            'explanationSchema': dict(row.explanation_schema or {}),
            'payload': dict(row.payload or {}),
            'updatedAt': row.updated_at.isoformat() if row.updated_at else None,
        }

    def _serialize_cost_card(self, row: SkuCostCard) -> Dict[str, Any]:
        return {
            'id': int(row.id),
            'shopId': int(row.shop_id) if row.shop_id is not None else None,
            'skuId': int(row.sku_id) if row.sku_id is not None else None,
            'canonicalSku': row.canonical_sku,
            'profileCode': row.profile_code,
            'currencyCode': row.currency_code,
            'adsCostAmount': float(row.ads_cost_amount or 0.0),
            'otherCostAmount': float(row.other_cost_amount or 0.0),
            'sourceMode': row.source_mode,
            'confidence': float(row.confidence or 0.0),
            'versionLabel': row.version_label,
            'overrideReason': row.override_reason,
            'effectiveFrom': row.effective_from.isoformat() if row.effective_from else None,
            'lastVerifiedAt': row.last_verified_at.isoformat() if row.last_verified_at else None,
            'isActive': bool(row.is_active),
            'componentValues': dict(row.component_values or {}),
            'payload': dict(row.payload or {}),
            'updatedAt': row.updated_at.isoformat() if row.updated_at else None,
        }

    def get_config_contract(self) -> Dict[str, Any]:
        self._seed_defaults()
        components = self.list_cost_components(active_only=False)['items']
        profiles = self.list_profit_profiles(active_only=False)['items']
        return {
            'contractName': 'economics_config_contract',
            'contractVersion': self.CONTRACT_VERSION,
            'status': 'ready',
            'transitionalCorePolicy': {
                'p3CoreKept': True,
                'expandP3CoreFurther': False,
                'targetDirection': 'config_driven_profit_engine',
            },
            'tables': [
                'registry_cost_component',
                'registry_profit_profile',
                'sku_cost_card',
            ],
            'routes': {
                'contract': '/api/v1/economics/config/contract',
                'costComponents': '/api/v1/economics/config/cost-components',
                'profitProfiles': '/api/v1/economics/config/profit-profiles',
                'skuCostCards': '/api/v1/economics/config/sku-cost-cards',
            },
            'defaultCostComponents': [item['componentCode'] for item in components if item.get('isActive')],
            'defaultProfitProfile': next((item['profileCode'] for item in profiles if item.get('isDefault')), None),
            'componentSchema': {
                'requiredFields': ['componentCode', 'componentName', 'componentScope', 'sourceModeDefault', 'affectsProfitLayer'],
                'optionalFields': ['confidenceDefault', 'versionLabel', 'isRequired', 'payload'],
            },
            'profitProfileSchema': {
                'requiredFields': ['profileCode', 'profileName', 'pricingMode'],
                'optionalFields': ['layerSchema', 'explanationSchema', 'isDefault', 'payload'],
            },
            'skuCostCardSchema': {
                'requiredFields': ['shopId', 'canonicalSku', 'profileCode', 'currencyCode'],
                'optionalFields': ['adsCostAmount', 'otherCostAmount', 'sourceMode', 'confidence', 'componentValues', 'overrideReason'],
            },
            'notes': [
                '本轮先冻结 economics config contract，不继续扩写 P3 /core。',
                '后续 profit solve / pricing recommend 必须消费这里的配置对象。',
            ],
        }

    def list_cost_components(self, *, active_only: bool = True) -> Dict[str, Any]:
        self._seed_defaults()
        with get_session() as session:
            stmt = select(RegistryCostComponent)
            if active_only:
                stmt = stmt.where(RegistryCostComponent.is_active.is_(True))
            rows = session.execute(stmt.order_by(RegistryCostComponent.component_code.asc())).scalars().all()
            return {
                'contractVersion': self.CONTRACT_VERSION,
                'itemCount': len(rows),
                'items': [self._serialize_component(row) for row in rows],
            }

    def upsert_cost_component(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._seed_defaults()
        component_code = self._clean_str(payload.get('componentCode'))
        component_name = self._clean_str(payload.get('componentName'))
        if not component_code or not component_name:
            raise ValueError('component_code_and_name_required')
        with get_session() as session:
            row = session.execute(
                select(RegistryCostComponent).where(RegistryCostComponent.component_code == component_code)
            ).scalar_one_or_none()
            if row is None:
                row = RegistryCostComponent(component_code=component_code, component_name=component_name)
                session.add(row)
            row.component_name = component_name
            row.component_scope = self._clean_str(payload.get('componentScope'), row.component_scope or 'sku')
            row.source_mode_default = self._clean_str(payload.get('sourceModeDefault'), row.source_mode_default or 'rule_estimate')
            row.confidence_default = self._to_float(payload.get('confidenceDefault'), row.confidence_default or 0.7)
            row.version_label = self._clean_str(payload.get('versionLabel'), row.version_label or 'v1')
            row.affects_profit_layer = self._clean_str(payload.get('affectsProfitLayer'), row.affects_profit_layer or 'base_contribution_profit')
            row.is_required = self._to_bool(payload.get('isRequired'), row.is_required if row.id else False)
            row.is_active = self._to_bool(payload.get('isActive'), True if row.is_active is None else row.is_active)
            row.payload = dict(payload.get('payload') or row.payload or {})
            session.flush()
            return self._serialize_component(row)

    def list_profit_profiles(self, *, active_only: bool = True) -> Dict[str, Any]:
        self._seed_defaults()
        with get_session() as session:
            stmt = select(RegistryProfitProfile)
            if active_only:
                stmt = stmt.where(RegistryProfitProfile.is_active.is_(True))
            rows = session.execute(stmt.order_by(RegistryProfitProfile.profile_code.asc())).scalars().all()
            return {
                'contractVersion': self.CONTRACT_VERSION,
                'itemCount': len(rows),
                'items': [self._serialize_profile(row) for row in rows],
            }

    def upsert_profit_profile(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._seed_defaults()
        profile_code = self._clean_str(payload.get('profileCode'))
        profile_name = self._clean_str(payload.get('profileName'))
        if not profile_code or not profile_name:
            raise ValueError('profile_code_and_name_required')
        with get_session() as session:
            row = session.execute(
                select(RegistryProfitProfile).where(RegistryProfitProfile.profile_code == profile_code)
            ).scalar_one_or_none()
            if row is None:
                row = RegistryProfitProfile(profile_code=profile_code, profile_name=profile_name)
                session.add(row)
            row.profile_name = profile_name
            row.pricing_mode = self._clean_str(payload.get('pricingMode'), row.pricing_mode or 'balanced_profit')
            row.version_label = self._clean_str(payload.get('versionLabel'), row.version_label or 'v1')
            row.is_default = self._to_bool(payload.get('isDefault'), row.is_default if row.id else False)
            row.is_active = self._to_bool(payload.get('isActive'), True if row.is_active is None else row.is_active)
            row.layer_schema = dict(payload.get('layerSchema') or row.layer_schema or {})
            row.explanation_schema = dict(payload.get('explanationSchema') or row.explanation_schema or {})
            row.payload = dict(payload.get('payload') or row.payload or {})
            if row.is_default:
                others = session.execute(
                    select(RegistryProfitProfile).where(RegistryProfitProfile.profile_code != profile_code)
                ).scalars().all()
                for other in others:
                    other.is_default = False
            session.flush()
            return self._serialize_profile(row)

    def _resolve_sku_id(self, session, *, shop_id: int | None, sku_id: int | None, canonical_sku: str) -> int | None:
        if sku_id is not None:
            return sku_id
        if not canonical_sku:
            return None
        stmt = select(DimSku)
        if shop_id is not None:
            stmt = stmt.where(DimSku.shop_id == shop_id)
        stmt = stmt.where(DimSku.sku == canonical_sku)
        row = session.execute(stmt).scalar_one_or_none()
        return int(row.id) if row is not None else None

    def list_sku_cost_cards(
        self,
        *,
        shop_id: int | None = None,
        canonical_sku: str | None = None,
        profile_code: str | None = None,
        active_only: bool = True,
    ) -> Dict[str, Any]:
        self._seed_defaults()
        with get_session() as session:
            stmt = select(SkuCostCard)
            if shop_id is not None:
                stmt = stmt.where(SkuCostCard.shop_id == shop_id)
            if canonical_sku:
                stmt = stmt.where(SkuCostCard.canonical_sku == canonical_sku)
            if profile_code:
                stmt = stmt.where(SkuCostCard.profile_code == profile_code)
            if active_only:
                stmt = stmt.where(SkuCostCard.is_active.is_(True))
            rows = session.execute(
                stmt.order_by(SkuCostCard.shop_id.asc(), SkuCostCard.canonical_sku.asc(), SkuCostCard.profile_code.asc())
            ).scalars().all()
            return {
                'contractVersion': self.CONTRACT_VERSION,
                'itemCount': len(rows),
                'items': [self._serialize_cost_card(row) for row in rows],
            }

    def upsert_sku_cost_card(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._seed_defaults()
        shop_id = self._to_int(payload.get('shopId'))
        canonical_sku = self._clean_str(payload.get('canonicalSku'))
        profile_code = self._clean_str(payload.get('profileCode'), 'default_profit_v1')
        currency_code = self._clean_str(payload.get('currencyCode'), settings.DEFAULT_CURRENCY)
        if shop_id is None or not canonical_sku:
            raise ValueError('shop_id_and_canonical_sku_required')
        with get_session() as session:
            row = session.execute(
                select(SkuCostCard).where(
                    SkuCostCard.shop_id == shop_id,
                    SkuCostCard.canonical_sku == canonical_sku,
                    SkuCostCard.profile_code == profile_code,
                )
            ).scalar_one_or_none()
            if row is None:
                row = SkuCostCard(shop_id=shop_id, canonical_sku=canonical_sku, profile_code=profile_code)
                session.add(row)
            row.sku_id = self._resolve_sku_id(
                session,
                shop_id=shop_id,
                sku_id=self._to_int(payload.get('skuId')),
                canonical_sku=canonical_sku,
            )
            row.currency_code = currency_code
            row.ads_cost_amount = self._to_float(payload.get('adsCostAmount'), row.ads_cost_amount or 0.0)
            row.other_cost_amount = self._to_float(payload.get('otherCostAmount'), row.other_cost_amount or 0.0)
            row.source_mode = self._clean_str(payload.get('sourceMode'), row.source_mode or 'manual_override')
            row.confidence = self._to_float(payload.get('confidence'), row.confidence or 0.8)
            row.version_label = self._clean_str(payload.get('versionLabel'), row.version_label or 'v1')
            row.override_reason = self._clean_str(payload.get('overrideReason')) or None
            row.is_active = self._to_bool(payload.get('isActive'), True if row.is_active is None else row.is_active)
            row.last_verified_at = self._now()
            row.component_values = dict(payload.get('componentValues') or row.component_values or {})
            row.payload = dict(payload.get('payload') or row.payload or {})
            session.flush()
            return self._serialize_cost_card(row)


    def _build_resolve_contract(self, batch_id: int, *, default_profile: str | None, component_codes: list[str]) -> Dict[str, Any]:
        return {
            'contractName': 'economics_config_resolve',
            'contractVersion': self.RESOLVE_CONTRACT_VERSION,
            'defaultView': 'all',
            'availableViews': ['all', 'ready', 'issues'],
            'defaultProfileCode': default_profile,
            'componentCodes': list(component_codes),
            'primaryKeyFields': ['factDate', 'shopId', 'canonicalSku', 'currencyCode', 'providerCode', 'unresolvedReason'],
            'dimensionFields': ['factDate', 'shopId', 'skuId', 'canonicalSku', 'currencyCode', 'providerCode'],
            'resolveFields': ['profileCode', 'profileResolvedFrom', 'costCardFound', 'configReady', 'configBlockers'],
            'componentField': 'resolvedComponents',
            'exportFileStem': f'batch_{batch_id}_economics_config_resolve',
        }

    def _build_component_specs(self, *, component_rows: list[RegistryCostComponent], card: dict[str, Any] | None, fact_row: dict[str, Any]) -> list[dict[str, Any]]:
        specs: list[dict[str, Any]] = []
        for component in component_rows:
            code = component.component_code
            source_mode = component.source_mode_default
            value = 0.0
            coverage_state = 'missing'
            confidence = float(component.confidence_default or 0.0)
            if code == 'platform_fee':
                value = float(fact_row.get('platformFeeAmount') or 0.0)
                source_mode = 'import_value'
                coverage_state = 'covered'
                confidence = 0.95
            elif code == 'fulfillment_fee':
                value = float(fact_row.get('fulfillmentFeeAmount') or 0.0)
                source_mode = 'import_value'
                coverage_state = 'covered'
                confidence = 0.95
            elif card is not None:
                value = self._coerce_component_value(card, code)
                source_mode = self._clean_str(card.get('sourceMode'), component.source_mode_default)
                confidence = float(card.get('confidence') or component.confidence_default or 0.0)
                coverage_state = 'covered'
            specs.append({
                'componentCode': code,
                'affectsProfitLayer': component.affects_profit_layer,
                'isRequired': bool(component.is_required),
                'sourceMode': source_mode,
                'coverageState': coverage_state,
                'value': round(float(value or 0.0), 4),
                'confidence': round(float(confidence or 0.0), 4),
            })
        return specs

    def _build_resolve_item(
        self,
        *,
        fact_row: dict[str, Any],
        default_profile: dict[str, Any] | None,
        cost_card: dict[str, Any] | None,
        component_rows: list[RegistryCostComponent],
    ) -> dict[str, Any]:
        profile_code = self._clean_str((cost_card or {}).get('profileCode') or (default_profile or {}).get('profileCode')) or None
        profile_resolved_from = 'sku_cost_card' if cost_card else 'default_profile'
        blockers: list[str] = []
        if fact_row.get('factReady') is not True:
            blockers.append('fact_not_ready')
        if not profile_code:
            blockers.append('missing_profit_profile')
        if cost_card is None:
            blockers.append('missing_cost_card')
        components = self._build_component_specs(component_rows=component_rows, card=cost_card, fact_row=fact_row)
        component_map = {item['componentCode']: dict(item) for item in components}
        config_ready = len(blockers) == 0
        return {
            'factDate': fact_row.get('factDate'),
            'shopId': fact_row.get('shopId'),
            'skuId': fact_row.get('skuId'),
            'canonicalSku': fact_row.get('canonicalSku'),
            'currencyCode': fact_row.get('currencyCode'),
            'providerCode': fact_row.get('providerCode'),
            'factReady': bool(fact_row.get('factReady') is True),
            'unresolvedReason': fact_row.get('unresolvedReason'),
            'identityConfidenceBucket': fact_row.get('identityConfidenceBucket'),
            'profileCode': profile_code,
            'profileResolvedFrom': profile_resolved_from if profile_code else None,
            'costCardFound': cost_card is not None,
            'costCardId': (cost_card or {}).get('id'),
            'costCardSourceMode': (cost_card or {}).get('sourceMode'),
            'costCardConfidence': (cost_card or {}).get('confidence'),
            'configReady': config_ready,
            'configBlockers': blockers,
            'resolvedComponents': components,
            'resolvedComponentMap': component_map,
        }

    @staticmethod
    def _filter_resolve_rows(rows: list[dict[str, Any]], *, view: str) -> list[dict[str, Any]]:
        if view == 'ready':
            return [dict(row) for row in rows if row.get('configReady') is True]
        if view == 'issues':
            return [dict(row) for row in rows if row.get('configReady') is not True]
        return [dict(row) for row in rows]

    @staticmethod
    def _paginate_rows(rows: list[dict[str, Any]], *, offset: int, limit: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        total = len(rows)
        page = rows[offset: offset + limit]
        return page, {
            'offset': offset,
            'limit': limit,
            'returned': len(page),
            'total': total,
            'hasMore': offset + len(page) < total,
        }

    @staticmethod
    def _build_component_coverage(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        coverage: dict[str, dict[str, Any]] = {}
        for row in rows:
            for comp in list(row.get('resolvedComponents') or []):
                bucket = coverage.setdefault(comp['componentCode'], {
                    'componentCode': comp['componentCode'],
                    'coveredRowCount': 0,
                    'missingRowCount': 0,
                    'required': bool(comp.get('isRequired')),
                    'sourceModes': set(),
                })
                if comp.get('coverageState') == 'covered':
                    bucket['coveredRowCount'] += 1
                else:
                    bucket['missingRowCount'] += 1
                if comp.get('sourceMode'):
                    bucket['sourceModes'].add(comp['sourceMode'])
        out = []
        for code in sorted(coverage):
            item = coverage[code]
            out.append({
                'componentCode': code,
                'coveredRowCount': item['coveredRowCount'],
                'missingRowCount': item['missingRowCount'],
                'required': item['required'],
                'sourceModes': sorted(item['sourceModes']),
            })
        return out

    def _build_resolve_summary(self, rows: list[dict[str, Any]], *, default_profile_code: str | None) -> dict[str, Any]:
        total_rows = len(rows)
        ready_count = sum(1 for row in rows if row.get('configReady') is True)
        card_count = sum(1 for row in rows if row.get('costCardFound') is True)
        return {
            'sourceFactRowCount': total_rows,
            'configReadyRowCount': ready_count,
            'blockedRowCount': total_rows - ready_count,
            'costCardAttachedRowCount': card_count,
            'missingCostCardRowCount': total_rows - card_count,
            'defaultProfileCode': default_profile_code,
            'configReadyRate': round((ready_count / total_rows) if total_rows else 0.0, 4),
            'componentCoverage': self._build_component_coverage(rows),
        }

    @staticmethod
    def _build_issue_buckets(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        buckets: dict[str, int] = {}
        for row in rows:
            for blocker in list(row.get('configBlockers') or []):
                buckets[blocker] = buckets.get(blocker, 0) + 1
        return [
            {'reason': code, 'rowCount': count}
            for code, count in sorted(buckets.items(), key=lambda item: (-item[1], item[0]))
        ]

    def _project_resolve_rows(self, rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
        fields = [
            'factDate', 'shopId', 'skuId', 'canonicalSku', 'currencyCode', 'providerCode',
            'factReady', 'profileCode', 'profileResolvedFrom', 'costCardFound', 'configReady', 'configBlockers',
            'resolvedComponents', 'resolvedComponentMap',
        ]
        return ([{field: row.get(field) for field in fields} for row in rows], fields)

    def _build_resolve_state(self, batch_ref: str) -> Optional[dict[str, Any]]:
        self._seed_defaults()
        state = self._get_object_service()._load_batch_object_state(batch_ref)
        if not state:
            return None
        fact_model = self._get_object_service()._build_fact_read_model(state)
        with get_session() as session:
            default_profile_row = self._get_default_profile_row(session)
            component_rows = session.execute(
                select(RegistryCostComponent)
                .where(RegistryCostComponent.is_active.is_(True))
                .order_by(RegistryCostComponent.component_code.asc())
            ).scalars().all()
            default_profile = self._serialize_profile(default_profile_row) if default_profile_row is not None else None
            rows: list[dict[str, Any]] = []
            for fact_row in list(fact_model.get('rows') or []):
                canonical_sku = self._clean_str(fact_row.get('canonicalSku'))
                shop_id = self._to_int(fact_row.get('shopId'))
                card_row = None
                if default_profile and canonical_sku and not canonical_sku.startswith('batch-'):
                    card_row = self._find_cost_card_row(session, shop_id=shop_id, canonical_sku=canonical_sku, profile_code=default_profile['profileCode'])
                cost_card = self._serialize_cost_card(card_row) if card_row is not None else None
                rows.append(
                    self._build_resolve_item(
                        fact_row=dict(fact_row),
                        default_profile=default_profile,
                        cost_card=cost_card,
                        component_rows=component_rows,
                    )
                )
            return {
                'batchId': state['batchId'],
                'detail': dict(state.get('detail') or {}),
                'factReadiness': fact_model.get('factReadiness') or {},
                'defaultProfile': default_profile,
                'componentCodes': [row.component_code for row in component_rows],
                'rows': rows,
            }

    def get_batch_config_resolve(self, batch_ref: str, *, limit: int = 50, offset: int = 0, view: str = 'all') -> Optional[Dict[str, Any]]:
        state = self._build_resolve_state(batch_ref)
        if not state:
            return None
        normalized_view = self._clean_str(view, 'all').lower()
        if normalized_view not in {'all', 'ready', 'issues'}:
            raise ValueError('unsupported_config_resolve_view')
        filtered_rows = self._filter_resolve_rows(list(state['rows']), view=normalized_view)
        safe_offset = max(int(offset or 0), 0)
        safe_limit = min(max(int(limit or 50), 1), 200)
        page, pagination = self._paginate_rows(filtered_rows, offset=safe_offset, limit=safe_limit)
        projected_page, column_order = self._project_resolve_rows(page)
        summary = self._build_resolve_summary(filtered_rows, default_profile_code=(state['defaultProfile'] or {}).get('profileCode'))
        contract = self._build_resolve_contract(
            state['batchId'],
            default_profile=(state['defaultProfile'] or {}).get('profileCode'),
            component_codes=list(state['componentCodes']),
        )
        return {
            'batchId': state['batchId'],
            'datasetKind': state['detail'].get('datasetKind'),
            'contractVersion': self.RESOLVE_CONTRACT_VERSION,
            'view': normalized_view,
            'columnOrder': column_order,
            'pagination': pagination,
            'factReadiness': dict(state['factReadiness']),
            'defaultProfile': state['defaultProfile'],
            'resolveSummary': summary,
            'issueBuckets': self._build_issue_buckets(filtered_rows),
            'exportSpec': {
                'fileStem': contract['exportFileStem'],
                'suggestedFileName': f"{contract['exportFileStem']}_{normalized_view}.json",
                'selectedColumns': column_order,
            },
            'items': projected_page,
        }

    def get_batch_config_resolve_contract(self, batch_ref: str) -> Optional[Dict[str, Any]]:
        state = self._build_resolve_state(batch_ref)
        if not state:
            return None
        return {
            'batchId': state['batchId'],
            'datasetKind': state['detail'].get('datasetKind'),
            'consumerContract': self._build_resolve_contract(
                state['batchId'],
                default_profile=(state['defaultProfile'] or {}).get('profileCode'),
                component_codes=list(state['componentCodes']),
            ),
            'defaultProfile': state['defaultProfile'],
            'factReadiness': dict(state['factReadiness']),
        }

    def get_batch_config_resolve_summary(self, batch_ref: str) -> Optional[Dict[str, Any]]:
        state = self._build_resolve_state(batch_ref)
        if not state:
            return None
        return self._build_resolve_summary(list(state['rows']), default_profile_code=(state['defaultProfile'] or {}).get('profileCode'))
