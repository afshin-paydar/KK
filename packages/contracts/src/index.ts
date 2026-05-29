// Shared TypeScript types for the KK API + MQTT contracts.
// Mirrors docs/DATA_SCHEMA.md and the backend Pydantic schemas.
// Single source of truth shared by dashboard, backend (via OpenAPI), and edge agent.

export type DeviceStatus = "pending" | "active" | "suspended" | "revoked";
export type OperatorRole = "admin" | "operator" | "viewer";

export interface Device {
  id: string;
  name: string;
  description: string | null;
  location: string | null;
  status: DeviceStatus;
  hardware_model: string | null;
  agent_version: string | null;
  last_seen_at: string | null;
  created_at: string;
}

export interface DeviceRegistered {
  device: Device;
  enrollment_token: string;
  enrollment_expires_at: string;
}

export interface Policy {
  id: string;
  name: string;
  version: number;
  description: string | null;
  spec: PolicySpec;
  is_active: boolean;
  created_at: string;
}

export interface PolicySpec {
  privacy_level: "metadata_only";
  vision?: { labels_of_interest: string[]; min_confidence: number };
  llm?: { model: string; max_tokens: number; escalation_only?: boolean };
  allowed_actions: { type: string; constraints?: Record<string, unknown> }[];
  local_rules?: { when: Record<string, unknown>; do: ActionRef }[];
  guardrails?: { deny_actions?: string[]; rate_limit_per_min?: number };
}

export interface ActionRef {
  type: string;
  params: Record<string, unknown>;
}

// --- MQTT message contracts ---

export interface EventMsg {
  schema: "kk.event.v1";
  device_id: string;
  correlation_id: string;
  type: "detection" | "telemetry" | "heartbeat" | "alert";
  occurred_at: string;
  payload: Record<string, unknown>;
}

export interface ActionMsg {
  schema: "kk.action.v1";
  action_id: string;
  correlation_id: string;
  type: string;
  params: Record<string, unknown>;
  expires_at?: string;
}

export interface AckMsg {
  schema: "kk.ack.v1";
  action_id: string;
  status: "executed" | "failed";
  executed_at: string;
  result?: Record<string, unknown>;
}
