"""SQLAlchemy 2.0 models. Mirrors docs/DATA_SCHEMA.md."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Operator(Base):
    __tablename__ = "operators"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    idaas_subject: Mapped[str] = mapped_column(Text, unique=True)
    email: Mapped[str | None] = mapped_column(Text)
    display_name: Mapped[str | None] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(16), default="viewer")  # admin|operator|viewer
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|active|suspended|revoked
    enrollment_token_hash: Mapped[str | None] = mapped_column(Text)
    enrollment_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    hardware_model: Mapped[str | None] = mapped_column(Text)
    serial: Mapped[str | None] = mapped_column(Text)
    firmware_version: Mapped[str | None] = mapped_column(Text)
    agent_version: Mapped[str | None] = mapped_column(Text)
    vision_model_version: Mapped[str | None] = mapped_column(Text)
    tts_model_version: Mapped[str | None] = mapped_column(Text)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_ip: Mapped[str | None] = mapped_column(INET)
    org_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("operators.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    enrolled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    certificates: Mapped[list["DeviceCertificate"]] = relationship(back_populates="device")
    assignments: Mapped[list["PolicyAssignment"]] = relationship(back_populates="device")


class DeviceCertificate(Base):
    __tablename__ = "device_certificates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id"))
    serial_number: Mapped[str] = mapped_column(Text, unique=True)
    fingerprint_sha256: Mapped[str] = mapped_column(Text, unique=True)
    subject_cn: Mapped[str] = mapped_column(Text)
    not_before: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    not_after: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), default="active")  # active|revoked
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_reason: Mapped[str | None] = mapped_column(Text)
    issued_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("operators.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    device: Mapped[Device] = relationship(back_populates="certificates")


class Policy(Base):
    __tablename__ = "policies"
    __table_args__ = (UniqueConstraint("name", "version"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    description: Mapped[str | None] = mapped_column(Text)
    spec: Mapped[dict] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("operators.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PolicyAssignment(Base):
    __tablename__ = "policy_assignments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id"))
    policy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("policies.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("operators.id"))
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    device: Mapped[Device] = relationship(back_populates="assignments")
    policy: Mapped[Policy] = relationship()


class ActionType(Base):
    __tablename__ = "action_types"

    key: Mapped[str] = mapped_column(Text, primary_key=True)  # e.g. tts.speak
    description: Mapped[str | None] = mapped_column(Text)
    params_schema: Mapped[dict] = mapped_column(JSONB)
    requires_confirmation: Mapped[bool] = mapped_column(Boolean, default=False)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id"), index=True)
    type: Mapped[str] = mapped_column(String(16))  # detection|telemetry|heartbeat|alert
    payload: Mapped[dict] = mapped_column(JSONB)  # metadata only — never raw frames
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    correlation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=_uuid)


class LLMDecision(Base):
    __tablename__ = "llm_decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id"))
    event_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("events.id"))
    policy_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("policies.id"))
    policy_version: Mapped[int | None] = mapped_column(Integer)
    model: Mapped[str] = mapped_column(Text)
    prompt: Mapped[dict] = mapped_column(JSONB)  # metadata-only by construction
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    response_raw: Mapped[dict | None] = mapped_column(JSONB)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    proposed_action: Mapped[dict | None] = mapped_column(JSONB)
    decision: Mapped[str] = mapped_column(String(16))  # allowed|rejected|modified
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Action(Base):
    __tablename__ = "actions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id"))
    decision_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("llm_decisions.id"))
    correlation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=_uuid)
    type: Mapped[str] = mapped_column(ForeignKey("action_types.key"))
    params: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(16), default="queued")
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result: Mapped[dict | None] = mapped_column(JSONB)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    actor_type: Mapped[str] = mapped_column(String(16))  # operator|system|device
    actor_id: Mapped[str | None] = mapped_column(Text)
    action: Mapped[str] = mapped_column(Text)
    target_type: Mapped[str | None] = mapped_column(Text)
    target_id: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)
    ip: Mapped[str | None] = mapped_column(INET)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
