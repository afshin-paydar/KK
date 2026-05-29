# KK — System Specification

## 1. Overview

Knock Knock (KK) is a platform for registering, configuring, and operating a fleet
of Raspberry Pi **edge agents**. Each Pi:

- captures camera frames and runs a **small vision detection model on‑device**,
- runs a **small text‑to‑speech (TTS) model on‑device**,
- sends compact **metadata** (detections, sensor values, metrics) to the cloud,
- receives **actions** computed by the Qwen LLM under a per‑device **policy**, and
- executes those actions locally (speak, actuate GPIO, raise alert, etc.).

The cloud side is a **control plane** (device registry, policy management,
dashboard) plus a **policy gateway** that brokers every LLM call so policy can be
injected, the response validated, and the decision audited.

### Design goals

1. **Minimal cloud communication.** Vision runs on the Pi. Only structured events
   and actions cross the network. The Pi can resolve common cases locally from a
   cached **policy snapshot** without a round trip.
2. **Strong identity on both ends.** Operators authenticate via IDaaS; devices via
   mutual TLS with per‑device client certificates.
3. **Privacy by construction.** Raw frames never leave the device.
4. **Auditability.** Every enrollment, policy change, LLM decision, and issued
   action is recorded.

## 2. Components

| Component | Tech | Responsibility |
|---|---|---|
| Dashboard | React + TypeScript (Vite) | Operator UI: register devices, author policies, view fleet, audit |
| Backend | Python + FastAPI | Control plane API, PKI, **policy gateway**, MQTT bridge, audit |
| MQTT broker | EMQX / Mosquitto (mTLS) | Pi ↔ cloud transport |
| Datastore | PostgreSQL | Registry, policies, events, decisions, actions, audit |
| LLM | Qwen (DashScope API) | Reasoning over events under policy |
| IDaaS | Alibaba Cloud IDaaS | Operator identity (OIDC) |
| Edge agent | Python (on Pi) | Vision, TTS, MQTT client, local action execution |

## 3. Identity & auth (the three pillars)

### 3.1 Operator auth — Alibaba Cloud IDaaS (OIDC)
- Dashboard is an OIDC client; users authenticate against IDaaS.
- Backend validates the IDaaS‑issued JWT (JWKS) on every request.
- Roles map from IDaaS claims/groups → `admin | operator | viewer`.

### 3.2 Device auth — mutual TLS
- During **enrollment**, the Pi generates a keypair, builds a CSR, and submits it
  with a one‑time enrollment token. The backend PKI signs a **per‑device client
  certificate** whose CN encodes the `device_id`.
- The MQTT broker requires client certs; the broker authenticates the Pi by cert,
  and authorizes it onto only its own `devices/{device_id}/#` topics.
- Certs are short‑lived and renewable; revocation is tracked server‑side (CRL /
  status table) and enforced at the broker.

### 3.3 Data privacy — on‑device inference, metadata only
- The vision model runs on the Pi. Output is structured metadata, e.g.
  `{"label": "person", "count": 2, "confidence": 0.91, "zone": "entry"}`.
- Raw frames and audio stay on the device. The cloud receives only metadata.
- Privacy posture is documented in [SECURITY.md](SECURITY.md).

## 4. Lifecycle

### 4.1 Enrollment
```
Operator (dashboard) ── register device ──► Backend
Backend ── create device(pending) + one‑time enrollment token ──► Operator
Operator ── provisions token onto Pi ──► Pi
Pi ── generate keypair + CSR, POST /enroll {token, csr} (over server‑TLS) ──► Backend
Backend ── verify token, sign cert, return {client_cert, ca_chain, broker_cfg, policy_snapshot} ──► Pi
Pi ── persists cert, connects to MQTT broker via mTLS ──► broker
Backend ── device status: active ─────────────────────────────────────────────
```

### 4.2 Runtime decision loop
```
Pi: frame ──► local vision ──► detection metadata
Pi: evaluate cached policy snapshot
     ├─ resolvable locally?  ──► execute action locally  (no cloud round trip)
     └─ needs reasoning?     ──► publish event to devices/{id}/events
Broker ──► Backend (MQTT bridge) consumes event
Backend: load device policy ──► build prompt (event + policy) ──► Qwen
Qwen ──► proposed action(s)
Backend: validate proposed action against policy allowlist + JSON schema
     ├─ allowed   ──► publish to devices/{id}/actions ; audit (decision=allowed)
     └─ rejected  ──► drop / fallback ; audit (decision=rejected, reason)
Pi: receive action ──► execute locally (TTS / GPIO / alert) ──► publish ack/result
```

### 4.3 Telemetry & heartbeat
- Pi publishes periodic heartbeat + lightweight metrics to `devices/{id}/telemetry`.
- Backend updates `last_seen_at`; dashboard shows fleet health.

## 5. Policy model

A **policy** is a versioned JSON document assigned to one or more devices. It
governs what the device may do and how the LLM is allowed to reason. Sketch:

```json
{
  "privacy_level": "metadata_only",
  "vision": { "labels_of_interest": ["person", "package"], "min_confidence": 0.6 },
  "llm": { "model": "qwen-plus", "max_tokens": 256, "escalation_only": true },
  "allowed_actions": [
    { "type": "tts.speak", "constraints": { "max_chars": 200 } },
    { "type": "alert.notify", "constraints": { "channels": ["dashboard"] } }
  ],
  "local_rules": [
    { "when": { "label": "person", "zone": "entry" }, "do": { "type": "tts.speak", "params": { "text": "Welcome" } } }
  ],
  "guardrails": { "deny_actions": ["gpio.set"], "rate_limit_per_min": 6 }
}
```

- `local_rules` are evaluated **on the Pi** from the snapshot — no cloud needed.
- `allowed_actions` is the allowlist the gateway validates every LLM proposal against.
- `guardrails` are enforced both at the Pi and the gateway.

## 6. Policy gateway (LLM brokering)

Every Qwen call goes through the backend. The gateway:
1. Resolves the device's active policy + version.
2. Builds a constrained prompt: system role + policy summary + allowed action
   JSON schema + the triggering event. Uses structured/tool‑style output.
3. Calls Qwen (DashScope), with timeout + retry budget.
4. **Validates** the proposed action: type ∈ allowlist, params ⊨ JSON schema,
   not in `deny_actions`, within rate limits.
5. Emits the action to MQTT and writes an `llm_decision` + `action` audit record.

This keeps the Qwen credential server‑side, centralizes enforcement, and gives a
full reasoning audit trail.

## 7. Transport (MQTT topics)

mTLS required; a device may only use topics under its own `device_id`.

| Topic | Dir | Payload |
|---|---|---|
| `devices/{id}/telemetry` | Pi→cloud | heartbeat, metrics |
| `devices/{id}/events`    | Pi→cloud | detection metadata needing reasoning |
| `devices/{id}/actions`   | cloud→Pi | validated action to execute |
| `devices/{id}/acks`      | Pi→cloud | action execution result |
| `devices/{id}/config`    | cloud→Pi | policy snapshot updates |

QoS 1 for events/actions/acks; QoS 0 for telemetry. Payload contracts in
[DATA_SCHEMA.md](DATA_SCHEMA.md).

## 8. APIs (backend, summary)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `POST` | `/api/devices` | operator | register device (pending) → token |
| `GET`  | `/api/devices` | operator | list/fleet |
| `GET`  | `/api/devices/{id}` | operator | device detail + status |
| `POST` | `/api/devices/{id}/revoke` | admin | revoke device + cert |
| `POST` | `/enroll` | enrollment token | CSR → signed client cert |
| `POST` | `/api/policies` | operator | create policy version |
| `POST` | `/api/devices/{id}/policy` | operator | assign policy |
| `GET`  | `/api/events` | operator | query events |
| `GET`  | `/api/decisions` | operator | LLM decision audit |
| `GET`  | `/api/actions` | operator | action history |
| `GET`  | `/api/audit` | admin | audit log |

`/enroll` is authenticated by the one‑time token (not IDaaS). All `/api/*`
routes require a valid IDaaS token.

## 9. Out of scope (v1)
- Multi‑tenant org isolation (schema leaves room via nullable `org_id`).
- OTA model/firmware delivery (tracked as `*_version` fields only).
- Live video streaming to cloud (explicitly disallowed by privacy model).
