from __future__ import annotations

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class RegistryDataset(Base, TimestampMixin):
    __tablename__ = 'registry_dataset'
    __table_args__ = (UniqueConstraint('dataset_kind', name='uq_registry_dataset_kind'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    import_profile: Mapped[str] = mapped_column(String(128), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default='file')
    platform: Mapped[str] = mapped_column(String(32), nullable=False, default='generic')
    grain: Mapped[str | None] = mapped_column(String(64), nullable=True)
    loader_target: Mapped[str | None] = mapped_column(String(128), nullable=True)
    gate_policy: Mapped[str] = mapped_column(String(64), nullable=False, default='core_safe')
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False, default='v1')
    entity_key_field: Mapped[str] = mapped_column(String(64), nullable=False, default='sku')
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class RegistryProfile(Base, TimestampMixin):
    __tablename__ = 'registry_profile'
    __table_args__ = (UniqueConstraint('dataset_id', 'profile_code', name='uq_registry_profile_dataset_profile'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey('registry_dataset.id'), nullable=False)
    profile_code: Mapped[str] = mapped_column(String(128), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(32), nullable=False, default='generic')
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default='file')
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class RegistryField(Base, TimestampMixin):
    __tablename__ = 'registry_field'
    __table_args__ = (UniqueConstraint('dataset_id', 'field_name', name='uq_registry_field_dataset_field'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey('registry_dataset.id'), nullable=False)
    field_name: Mapped[str] = mapped_column(String(128), nullable=False)
    field_role: Mapped[str] = mapped_column(String(32), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class RegistryGatePolicy(Base, TimestampMixin):
    __tablename__ = 'registry_gate_policy'
    __table_args__ = (UniqueConstraint('policy_code', name='uq_registry_gate_policy_code'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    policy_code: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    transport_rule: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    semantic_rule: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    importability_rule: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class IngestBatch(Base, TimestampMixin):
    __tablename__ = 'ingest_batch'
    __table_args__ = (UniqueConstraint('workspace_batch_id', name='uq_ingest_batch_workspace_batch_id'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_batch_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    legacy_session_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    legacy_import_batch_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dataset_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    import_profile: Mapped[str] = mapped_column(String(128), nullable=False)
    source_mode: Mapped[str] = mapped_column(String(32), nullable=False, default='upload')
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    platform: Mapped[str | None] = mapped_column(String(32), nullable=True)
    shop_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    operator: Mapped[str | None] = mapped_column(String(128), nullable=True)
    contract_version: Mapped[str] = mapped_column(String(32), nullable=False, default='p0a.v1')
    batch_status: Mapped[str] = mapped_column(String(32), nullable=False, default='uploaded')
    transport_status: Mapped[str] = mapped_column(String(32), nullable=False, default='failed')
    semantic_status: Mapped[str] = mapped_column(String(32), nullable=False, default='failed')
    importability_status: Mapped[str] = mapped_column(String(32), nullable=False, default='failed')
    imported_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quarantine_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    raw_parse_meta: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    raw_confirm_meta: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    parse_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    confirm_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    final_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class IngestSourceObject(Base, TimestampMixin):
    __tablename__ = 'ingest_source_object'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey('ingest_batch.id'), nullable=False)
    object_type: Mapped[str] = mapped_column(String(32), nullable=False, default='file')
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_meta: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class BatchFieldMapping(Base, TimestampMixin):
    __tablename__ = 'batch_field_mapping'
    __table_args__ = (UniqueConstraint('batch_id', 'source_header', name='uq_batch_field_mapping_batch_header'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey('ingest_batch.id'), nullable=False)
    source_header: Mapped[str] = mapped_column(String(255), nullable=False)
    target_field: Mapped[str | None] = mapped_column(String(128), nullable=True)
    confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mapping_status: Mapped[str] = mapped_column(String(32), nullable=False, default='suggested')
    mapping_meta: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class BatchGateResult(Base, TimestampMixin):
    __tablename__ = 'batch_gate_result'
    __table_args__ = (UniqueConstraint('batch_id', 'gate_name', name='uq_batch_gate_result_batch_gate'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey('ingest_batch.id'), nullable=False)
    gate_name: Mapped[str] = mapped_column(String(64), nullable=False)
    gate_status: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_list: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class BatchManualOverride(Base, TimestampMixin):
    __tablename__ = 'batch_manual_override'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey('ingest_batch.id'), nullable=False)
    override_type: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    operator: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class BatchAuditEvent(Base, TimestampMixin):
    __tablename__ = 'batch_audit_event'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey('ingest_batch.id'), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)



class BatchProfileCandidate(Base, TimestampMixin):
    __tablename__ = 'batch_profile_candidate'
    __table_args__ = (UniqueConstraint('batch_id', 'profile_code', name='uq_batch_profile_candidate_batch_profile'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey('ingest_batch.id'), nullable=False)
    dataset_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    profile_code: Mapped[str] = mapped_column(String(128), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    candidate_rank: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    auto_bindable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_manual_confirm: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    reason_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class BatchBusinessKeyCandidate(Base, TimestampMixin):
    __tablename__ = 'batch_business_key_candidate'
    __table_args__ = (UniqueConstraint('batch_id', 'strategy_code', name='uq_batch_business_key_candidate_batch_strategy'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey('ingest_batch.id'), nullable=False)
    strategy_code: Mapped[str] = mapped_column(String(128), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    candidate_rank: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    unresolved_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    surrogate_key_rate: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    downstream_risk: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reason_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class BatchQuarantineRow(Base, TimestampMixin):
    __tablename__ = 'batch_quarantine_row'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey('ingest_batch.id'), nullable=False)
    row_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    reason_cluster_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_auto_recoverable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
