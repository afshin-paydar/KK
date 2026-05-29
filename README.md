# Knock Knock (KK)

Manage a fleet of **Raspberry Pi edge agents** that run local vision detection and
text‑to‑speech, reason against the **Qwen** cloud LLM through a central **policy
gateway**, and act locally. Cloud traffic is minimal: inference runs on‑device and
only compact metadata and actions cross the wire.

## Trust pillars

| Concern | Mechanism |
|---|---|
| Operator auth | Alibaba Cloud **IDaaS** (OIDC) |
| Device auth | **Mutual TLS** with a per‑device client certificate |
| Data privacy | **On‑device inference** — only detection metadata leaves the Pi; raw frames never do |

## Layout

```
apps/backend/      FastAPI control plane + policy gateway + PKI (Python)
apps/dashboard/    Admin dashboard (React/TS, Vite)
apps/edge-agent/   Raspberry Pi agent daemon (Python)
packages/contracts/ Shared schemas: OpenAPI, JSON Schema, MQTT contracts
infra/             docker-compose, MQTT broker, PKI bootstrap
docs/              SPEC.md, DATA_SCHEMA.md, SECURITY.md
```

## Docs

- [docs/SPEC.md](docs/SPEC.md) — system spec & message flows
- [docs/DATA_SCHEMA.md](docs/DATA_SCHEMA.md) — DB schema & message contracts
- [docs/SECURITY.md](docs/SECURITY.md) — auth, PKI, mTLS, privacy

## Dev quick start

```bash
cd infra && docker compose up -d          # Postgres + MQTT + PKI bootstrap
cd apps/backend && uv sync && uv run uvicorn app.main:app --reload
cd apps/dashboard && pnpm install && pnpm dev
```
