"""Pydantic request/response models for the API and MQTT contracts."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

# --- Devices ---


class DeviceCreate(BaseModel):
    name: str
    description: str | None = None
    location: str | None = None
    hardware_model: str | None = None
    serial: str | None = None


class DeviceOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    location: str | None
    status: str
    hardware_model: str | None
    agent_version: str | None
    last_seen_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DeviceRegistered(BaseModel):
    device: DeviceOut
    enrollment_token: str = Field(description="one-time token; shown once")
    enrollment_expires_at: datetime


# --- Enrollment (device side, token-authenticated) ---


class EnrollRequest(BaseModel):
    token: str
    csr_pem: str
    agent_version: str | None = None
    vision_model_version: str | None = None
    tts_model_version: str | None = None


class BrokerConfig(BaseModel):
    host: str
    port: int
    topic_prefix: str  # devices/{device_id}


class EnrollResponse(BaseModel):
    device_id: uuid.UUID
    client_cert_pem: str
    ca_chain_pem: str
    broker: BrokerConfig
    policy_snapshot: dict[str, Any] | None


# --- Policies ---


class PolicyCreate(BaseModel):
    name: str
    description: str | None = None
    spec: dict[str, Any]


class PolicyOut(BaseModel):
    id: uuid.UUID
    name: str
    version: int
    description: str | None
    spec: dict[str, Any]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PolicyAssign(BaseModel):
    policy_id: uuid.UUID


# --- MQTT payload contracts (mirror docs/DATA_SCHEMA.md §3) ---


class EventMsg(BaseModel):
    schema_: Literal["kk.event.v1"] = Field("kk.event.v1", alias="schema")
    device_id: uuid.UUID
    correlation_id: uuid.UUID
    type: Literal["detection", "telemetry", "heartbeat", "alert"]
    occurred_at: datetime
    payload: dict[str, Any]


class ActionMsg(BaseModel):
    schema_: Literal["kk.action.v1"] = Field("kk.action.v1", alias="schema")
    action_id: uuid.UUID
    correlation_id: uuid.UUID
    type: str
    params: dict[str, Any]
    expires_at: datetime | None = None


class AckMsg(BaseModel):
    schema_: Literal["kk.ack.v1"] = Field("kk.ack.v1", alias="schema")
    action_id: uuid.UUID
    status: Literal["executed", "failed"]
    executed_at: datetime
    result: dict[str, Any] | None = None
