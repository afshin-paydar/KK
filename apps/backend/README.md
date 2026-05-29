# KK Backend

FastAPI control plane, policy gateway, and device PKI.

## Run

```bash
uv sync
cp .env.example .env          # fill in IDaaS + Qwen + MQTT
uv run uvicorn app.main:app --reload
```

## Layout

```
app/
  main.py              app + MQTT bridge lifespan
  config.py            settings (env)
  database.py          async SQLAlchemy session
  models.py            ORM models (see docs/DATA_SCHEMA.md)
  schemas.py           Pydantic API + MQTT contracts
  security/idaas.py    operator auth (IDaaS OIDC JWT)
  api/deps.py          auth + role gating deps
  api/routes/          devices, enrollment, policies
  services/pki.py          per-device client cert signing
  services/policy_engine.py action allowlist + schema validation
  services/llm_gateway.py   Qwen reasoning (backend-only API key)
  services/mqtt_bridge.py   event → reason → validate → action loop
```

## Notes
- `/enroll` is token-authenticated (device); all `/api/*` routes require an IDaaS JWT.
- The Qwen key never leaves the backend; the Pi only talks MQTT.
- Migrations: wire up Alembic against `app.models.Base.metadata`.
