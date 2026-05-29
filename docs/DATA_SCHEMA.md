# KK — Data Schema & Message Contracts

PostgreSQL is the system of record. Timestamps are `timestamptz` (UTC). Primary
keys are UUIDs unless noted. JSON columns are `jsonb`.

## 1. ER overview

```
operators ──< audit_logs
devices ──< device_certificates
devices ──< policy_assignments >── policies
devices ──< events ──< llm_decisions ──< actions
action_types (catalog)  ◄─ referenced by policies.allowed_actions & actions.type
```

## 2. Tables

### operators  (cached from IDaaS)
| column | type | notes |
|---|---|---|
| id | uuid pk | |
| idaas_subject | text unique | OIDC `sub` |
| email | text | |
| display_name | text | |
| role | text | `admin \| operator \| viewer` |
| created_at | timestamptz | |
| last_login_at | timestamptz | |

### devices
| column | type | notes |
|---|---|---|
| id | uuid pk | the `device_id`, encoded in cert CN |
| name | text | |
| description | text | |
| location | text | site / placement |
| status | text | `pending \| active \| suspended \| revoked` |
| enrollment_token_hash | text | hash of one‑time token; null after enroll |
| enrollment_expires_at | timestamptz | token TTL |
| hardware_model | text | e.g. `rpi-5` |
| serial | text | |
| firmware_version | text | |
| agent_version | text | |
| vision_model_version | text | |
| tts_model_version | text | |
| last_seen_at | timestamptz | from heartbeat |
| last_ip | inet | |
| org_id | uuid null | reserved for multi‑tenant |
| created_by | uuid fk operators | |
| created_at | timestamptz | |
| enrolled_at | timestamptz | |
| updated_at | timestamptz | |

### device_certificates
| column | type | notes |
|---|---|---|
| id | uuid pk | |
| device_id | uuid fk devices | |
| serial_number | text unique | cert serial |
| fingerprint_sha256 | text unique | |
| subject_cn | text | = device_id |
| not_before | timestamptz | |
| not_after | timestamptz | |
| status | text | `active \| revoked` |
| revoked_at | timestamptz | |
| revoked_reason | text | |
| issued_by | uuid fk operators | |
| created_at | timestamptz | |

### policies
| column | type | notes |
|---|---|---|
| id | uuid pk | |
| name | text | |
| version | int | monotonic per name |
| description | text | |
| spec | jsonb | policy document (see SPEC §5) |
| is_active | bool | |
| created_by | uuid fk operators | |
| created_at | timestamptz | |
| updated_at | timestamptz | |

`unique(name, version)`.

### policy_assignments
| column | type | notes |
|---|---|---|
| id | uuid pk | |
| device_id | uuid fk devices | |
| policy_id | uuid fk policies | |
| is_active | bool | one active per device |
| assigned_by | uuid fk operators | |
| assigned_at | timestamptz | |

### action_types  (catalog of permissible actions)
| column | type | notes |
|---|---|---|
| key | text pk | e.g. `tts.speak`, `gpio.set`, `alert.notify` |
| description | text | |
| params_schema | jsonb | JSON Schema for params |
| requires_confirmation | bool | |

### events  (ingested from Pi — metadata only)
| column | type | notes |
|---|---|---|
| id | uuid pk | |
| device_id | uuid fk devices | |
| type | text | `detection \| telemetry \| heartbeat \| alert` |
| payload | jsonb | metadata only — no raw frames |
| occurred_at | timestamptz | device clock |
| received_at | timestamptz | server clock |
| correlation_id | uuid | links event→decision→action |

Index: `(device_id, received_at desc)`.

### llm_decisions  (reasoning audit)
| column | type | notes |
|---|---|---|
| id | uuid pk | |
| device_id | uuid fk devices | |
| event_id | uuid fk events | |
| policy_id | uuid fk policies | |
| policy_version | int | |
| model | text | e.g. `qwen-plus` |
| prompt | jsonb | stored prompt (already metadata‑only) |
| prompt_tokens | int | |
| response_raw | jsonb | model output |
| completion_tokens | int | |
| proposed_action | jsonb | |
| decision | text | `allowed \| rejected \| modified` |
| rejection_reason | text | |
| latency_ms | int | |
| created_at | timestamptz | |

### actions  (issued to device)
| column | type | notes |
|---|---|---|
| id | uuid pk | |
| device_id | uuid fk devices | |
| decision_id | uuid fk llm_decisions null | null if from local/manual path |
| correlation_id | uuid | |
| type | text fk action_types.key | |
| params | jsonb | |
| status | text | `queued \| published \| acked \| executed \| failed \| expired` |
| issued_at | timestamptz | |
| published_at | timestamptz | |
| acked_at | timestamptz | |
| executed_at | timestamptz | |
| expires_at | timestamptz | |
| result | jsonb | from Pi ack |

### audit_logs
| column | type | notes |
|---|---|---|
| id | uuid pk | |
| actor_type | text | `operator \| system \| device` |
| actor_id | text | |
| action | text | e.g. `device.register`, `policy.update`, `cert.revoke` |
| target_type | text | |
| target_id | text | |
| metadata | jsonb | |
| ip | inet | |
| created_at | timestamptz | |

## 3. MQTT payload contracts

### event (Pi → `devices/{id}/events`)
```json
{
  "schema": "kk.event.v1",
  "device_id": "uuid",
  "correlation_id": "uuid",
  "type": "detection",
  "occurred_at": "2026-05-29T10:00:00Z",
  "payload": { "label": "person", "count": 2, "confidence": 0.91, "zone": "entry" }
}
```

### telemetry / heartbeat (Pi → `devices/{id}/telemetry`)
```json
{
  "schema": "kk.telemetry.v1",
  "device_id": "uuid",
  "occurred_at": "2026-05-29T10:00:00Z",
  "metrics": { "cpu": 0.32, "temp_c": 51.2, "fps": 12, "agent_version": "0.1.0" }
}
```

### action (cloud → `devices/{id}/actions`)
```json
{
  "schema": "kk.action.v1",
  "action_id": "uuid",
  "correlation_id": "uuid",
  "type": "tts.speak",
  "params": { "text": "Welcome" },
  "expires_at": "2026-05-29T10:00:30Z"
}
```

### ack (Pi → `devices/{id}/acks`)
```json
{
  "schema": "kk.ack.v1",
  "action_id": "uuid",
  "status": "executed",
  "executed_at": "2026-05-29T10:00:02Z",
  "result": { "ok": true }
}
```

### config / policy snapshot (cloud → `devices/{id}/config`)
```json
{
  "schema": "kk.config.v1",
  "policy_id": "uuid",
  "policy_version": 3,
  "spec": { "...": "see SPEC §5" }
}
```

All payload JSON Schemas live in `packages/contracts/` and are the single source
of truth shared by backend, dashboard, and edge agent.
