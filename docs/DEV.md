# KK — Local dev mode

Dev mode lets you click through the dashboard with **no IDaaS and no migrations**.
It is gated by env flags and must never be enabled in production.

| Flag | Where | Effect |
|---|---|---|
| `DEV_AUTH=true` | backend `.env` | skip IDaaS; every request runs as a stub **admin** operator |
| `DEV_CREATE_TABLES=true` | backend `.env` | create tables on startup (no Alembic) |
| `ENABLE_MQTT_BRIDGE=false` | backend `.env` | don't start the MQTT bridge (no broker/certs needed) |
| `VITE_DEV_AUTH=true` | dashboard `.env` | skip OIDC redirect; send a dummy bearer token |

`.env` files for both apps are already created with these set.

## Run it (3 terminals)

```bash
# 1. Postgres (broker not needed for dashboard testing)
cd infra && bash pki/bootstrap.sh && docker compose up -d postgres

# 2. Backend  → http://localhost:8000  (docs at /docs)
cd apps/backend && uv sync && uv run uvicorn app.main:app --reload --port 8000

# 3. Dashboard → http://localhost:5173
cd apps/dashboard && pnpm install && pnpm dev
```

Open http://localhost:5173: register a device, watch it appear in the fleet
table with its one-time enrollment token, and revoke it. The dashboard proxies
`/api` → `:8000`.

## Quick API check (no browser)

```bash
curl -X POST localhost:8000/api/devices -H 'Authorization: Bearer dev' \
  -H 'Content-Type: application/json' -d '{"name":"front-door-pi","location":"lobby"}'
curl localhost:8000/api/devices -H 'Authorization: Bearer dev'
```

## Going to production
Set all four flags off (or unset). Then wire real IDaaS env (`IDAAS_*`,
`VITE_IDAAS_*`), replace `DEV_CREATE_TABLES` with Alembic migrations, and enable
the MQTT bridge with the broker + backend client cert.
