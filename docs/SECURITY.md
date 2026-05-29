# KK — Security & Privacy Model

Three pillars, matching the judge criteria.

## 1. Operator auth — Alibaba Cloud IDaaS (OIDC)

- The dashboard is an OIDC client of Alibaba Cloud IDaaS (Authorization Code +
  PKCE). No passwords are handled by KK.
- The backend validates every `/api/*` request's bearer JWT against the IDaaS
  JWKS (issuer, audience, expiry, signature).
- Authorization: IDaaS group/role claim → `admin | operator | viewer`.
  - `admin`: register/revoke devices, manage all policies, view audit.
  - `operator`: register devices, author/assign policies, view fleet.
  - `viewer`: read‑only.
- Operators are mirrored into the `operators` table on first login for FK refs.

## 2. Device auth — mutual TLS

### PKI
- KK runs a private CA (root + intermediate). The intermediate signs **per‑device
  client certificates**; CN = `device_id`.
- Certs are short‑lived (e.g. 30 days) and renewable before expiry via mTLS.

### Enrollment (CSR signing)
1. Operator registers a device → backend stores `pending` device + a hashed
   **one‑time enrollment token** with a short TTL.
2. Token is provisioned onto the Pi out of band.
3. Pi generates a keypair locally (private key never leaves the device), builds a
   CSR, and `POST /enroll {token, csr}` over server‑side TLS.
4. Backend verifies the token, signs the CSR, records the cert in
   `device_certificates`, and returns the client cert + CA chain + broker config
   + initial policy snapshot.

### Enforcement
- The MQTT broker requires client certs (mTLS). It authenticates the Pi by cert
  and authorizes it onto **only** `devices/{device_id}/#`.
- Revocation: `device_certificates.status = revoked` + broker CRL/ACL update;
  revoked devices cannot reconnect or publish.

## 3. Data privacy — on‑device inference, metadata only

- The vision model runs on the Pi. **Raw frames and audio never leave the
  device.** Only structured metadata (labels, counts, confidences, zones, sensor
  values) is published.
- The `events.payload` and `llm_decisions.prompt` columns are metadata‑only by
  construction; there is no field for image bytes.
- Privacy level is recorded in policy (`privacy_level: metadata_only` for v1).
- Telemetry is operational metrics only (CPU, temp, fps, versions).

## 4. Secrets & boundaries

- The **Qwen / DashScope API key lives only in the backend**; the Pi never holds
  it. All LLM calls go through the policy gateway.
- Device private keys are generated and stored only on the Pi.
- Backend ↔ Postgres and backend ↔ broker use TLS.

## 5. Auditability

Every security‑relevant event is written to `audit_logs`: enrollment, cert
issuance/revocation, policy create/assign, device suspend/revoke, and each LLM
decision (`llm_decisions`) with its allow/reject outcome and reason.

## 6. Threat notes (v1)

- **Stolen enrollment token** → short TTL + one‑time use + bound to a single
  pending device.
- **Compromised Pi** → revoke cert (broker rejects); blast radius limited to that
  device's own topics by ACL.
- **Prompt injection via event metadata** → gateway validates LLM output against
  the action allowlist + JSON schema and `deny_actions`; the model cannot invent
  an action the policy doesn't permit.
- **Action replay** → actions carry `action_id` + `expires_at`; Pi drops expired
  or duplicate `action_id`s.
