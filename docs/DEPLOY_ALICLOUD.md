# Deploying KK on Alibaba Cloud + enrolling a real Raspberry Pi

Component → Alibaba Cloud service

  ┌───────────────────────────────────┬─────────────────────────────────────────────┐
  │             KK piece              │                   Service                   │
  ├───────────────────────────────────┼─────────────────────────────────────────────┤
  │ Backend (FastAPI)                 │ ECS + Docker (or ACK for k8s)               │
  ├───────────────────────────────────┼─────────────────────────────────────────────┤
  │ Dashboard (React)                 │ OSS static site + CDN                       │
  ├───────────────────────────────────┼─────────────────────────────────────────────┤
  │ Database                          │ ApsaraDB RDS for PostgreSQL                 │
  ├───────────────────────────────────┼─────────────────────────────────────────────┤
  │ MQTT broker (mTLS)                │ self-host EMQX/Mosquitto on ECS             │
  ├───────────────────────────────────┼─────────────────────────────────────────────┤
  │ Operator login                    │ IDaaS OIDC app                              │
  ├───────────────────────────────────┼─────────────────────────────────────────────┤
  │ Qwen LLM                          │ Model Studio / DashScope key (backend-only) │
  ├───────────────────────────────────┼─────────────────────────────────────────────┤
  │ API HTTPS                         │ ALB + cert for api.kk.example.com           │
  ├───────────────────────────────────┼─────────────────────────────────────────────┤
  │ MQTT exposure                     │ NLB TCP passthrough on 8883                 │
  ├───────────────────────────────────┼─────────────────────────────────────────────┤
  │ Secrets (CA key, Qwen key, DB pw) │ KMS / Secrets Manager                       │
  └───────────────────────────────────┴─────────────────────────────────────────────┘

This is the production path: host the stack on Alibaba Cloud, then enroll a
physical Pi over the internet using the three trust pillars (IDaaS, mTLS, on-device
privacy).

## 1. Component → Alibaba Cloud service

| KK component | Alibaba Cloud service | Notes |
|---|---|---|
| Backend (FastAPI) | **ECS** + Docker (simple) or **ACK** (k8s) | container from `apps/backend/Dockerfile` |
| Dashboard (React) | **OSS** static website + **CDN** | `pnpm build` → upload `dist/` |
| Database | **ApsaraDB RDS for PostgreSQL** | managed; set `DATABASE_URL` |
| MQTT broker (mTLS) | self-host **EMQX/Mosquitto** on ECS | keeps our per-device cert + ACL model |
| Operator auth | **IDaaS** (OIDC app) | redirect URI = dashboard URL |
| LLM | **Model Studio / DashScope** (Qwen) | API key, backend-only |
| HTTPS for API | **ALB** + Certificate Mgmt | terminates TLS for `:8000` |
| MQTT exposure | **NLB** (TCP passthrough) or EIP | must NOT terminate mTLS |
| Image registry | **ACR** (Container Registry) | push backend + broker images |
| Secrets (CA key, Qwen key, DB pw) | **KMS / Secrets Manager** | inject as env at runtime |
| Container image build | local `docker build` → ACR | |

> **Managed alternative for MQTT:** Alibaba Cloud IoT Platform gives managed MQTT
> with device management, but its device auth (device secret / its own X.509 model)
> differs from our CN-based ACL. Self-hosting EMQX preserves the spec as written.

## 2. Prerequisites (one-time)

1. **Domain + DNS** (e.g. `kk.example.com`): `api.` for the backend, `mqtt.` for the
   broker, `app.` for the dashboard.
2. **IDaaS OIDC app**: create an application, note issuer / client id / JWKS URL, and
   set the redirect URI to `https://app.kk.example.com/callback`.
3. **DashScope/Qwen** API key from Model Studio.
4. **VPC** with a security group opening: `443` (API/dashboard), `8883` (MQTT). Keep
   `5432` private to the VPC (RDS).
5. **ACR namespace** for images.

## 3. Provision

```
RDS for PostgreSQL  → create DB `kk`, user `kk`; note the private endpoint.
ECS instance(s)     → install Docker; attach to the VPC + security group.
ALB                 → listener 443 (cert for api.kk.example.com) → ECS :8000.
NLB                 → listener 8883 TCP passthrough → ECS :8883.
OSS bucket          → static website hosting; front with CDN + cert for app.*.
```

## 4. Production PKI (replace the dev bootstrap)

The dev `infra/pki/bootstrap.sh` is fine to generate the CA chain, but in production:

- Keep `root-ca.key` **offline**. The backend only needs `intermediate-ca.{pem,key}`.
- Store `intermediate-ca.key` in **KMS / Secrets Manager**; mount it at runtime, not
  in the image or repo.
- Issue the **broker server cert with a SAN** matching `mqtt.kk.example.com`:

```bash
# in infra/pki, after bootstrap.sh
openssl req -new -key broker.key -out broker.csr -subj "/O=KnockKnock/CN=mqtt.kk.example.com"
openssl x509 -req -in broker.csr -CA intermediate-ca.pem -CAkey intermediate-ca.key \
  -CAcreateserial -days 825 -out broker.pem \
  -extfile <(printf "subjectAltName=DNS:mqtt.kk.example.com")
```

With a real SAN, the Pi verifies the hostname normally and you set
`tls_insecure = false` in the agent config.

## 5. Configure + ship the backend

`infra/backend.env.prod` (injected via `env_file`; pull secrets from KMS):

```bash
DATABASE_URL=postgresql+asyncpg://kk:<pw>@<rds-private-endpoint>:5432/kk
DEV_AUTH=false
DEV_CREATE_TABLES=false          # use Alembic migrations instead
ENABLE_MQTT_BRIDGE=true

IDAAS_ISSUER=https://<tenant>.aliyunidaas.com/oauth2
IDAAS_AUDIENCE=kk-dashboard
IDAAS_JWKS_URL=https://<tenant>.aliyunidaas.com/oauth2/jwks

QWEN_API_KEY=<from-model-studio>
QWEN_DEFAULT_MODEL=qwen-plus

MQTT_HOST=localhost              # broker runs alongside on the same ECS/compose
PKI_CA_CERT=/app/pki/intermediate-ca.pem
PKI_CA_KEY=/app/pki/intermediate-ca.key   # mount from secret
MQTT_CA_CERT=/app/pki/ca-chain.pem
MQTT_CLIENT_CERT=/app/pki/backend.pem
MQTT_CLIENT_KEY=/app/pki/backend.key
```

Build, push, run:

```bash
# build + push (run locally or in CI)
docker build -t <acr>/kk-backend:0.1.0 apps/backend && docker push <acr>/kk-backend:0.1.0

# on the ECS host
cd infra && bash pki/bootstrap.sh   # or pull CA from KMS
docker compose -f docker-compose.prod.yml up -d
```

Run DB migrations once (Alembic — see §8 gaps): `alembic upgrade head`, then seed the
`action_types` catalog (`tts.speak`, `alert.notify`, …).

## 6. Ship the dashboard

```bash
cd apps/dashboard
# build-time env (production):
echo 'VITE_DEV_AUTH=false'                                   >  .env.production
echo 'VITE_API_BASE=https://api.kk.example.com/api'          >> .env.production
echo 'VITE_IDAAS_AUTHORITY=https://<tenant>.aliyunidaas.com/oauth2' >> .env.production
echo 'VITE_IDAAS_CLIENT_ID=kk-dashboard'                     >> .env.production
echo 'VITE_IDAAS_REDIRECT_URI=https://app.kk.example.com/callback' >> .env.production
pnpm build
# upload dist/ to the OSS bucket (ossutil cp -r dist/ oss://<bucket>/)
```

## 7. Register + connect a real Raspberry Pi

**On the dashboard** (`https://app.kk.example.com`, logged in via IDaaS):
1. Register the device → copy the **one-time enrollment token**.
2. (Optional) author a policy and assign it so the Pi gets a snapshot at enrollment.

**On the Pi** (Raspberry Pi OS 64-bit):
```bash
sudo apt update && sudo apt install -y python3 git
curl -LsSf https://astral.sh/uv/install.sh | sh        # install uv

git clone <your-repo> kk && cd kk/apps/edge-agent
uv sync                                                  # add --extra vision --extra tts for models

sudo mkdir -p /etc/kk /var/lib/kk
sudo cp agent.toml.example /etc/kk/agent.toml
sudo nano /etc/kk/agent.toml
```
Set in `/etc/kk/agent.toml`:
```toml
backend_url = "https://api.kk.example.com"
broker_host = "mqtt.kk.example.com"
broker_port = 8883
tls_insecure = false                 # true only if broker cert has no matching SAN
enrollment_token = "<paste-from-dashboard>"
state_dir = "/var/lib/kk"
```
Run it:
```bash
sudo KK_AGENT_CONFIG=/etc/kk/agent.toml uv run kk-agent
```

What happens: the agent generates a keypair + CSR **locally** (private key never
leaves the Pi), exchanges the token for a per-device client cert over HTTPS, then
connects to the broker over mTLS (cert CN = device_id) and starts publishing
heartbeats. The dashboard shows the device go **active**; on detections it publishes
metadata to `devices/{id}/events`, the backend reasons via Qwen under policy, and
pushes validated actions to `devices/{id}/actions`.

**Run as a service** (so it survives reboot): create a systemd unit
`/etc/systemd/system/kk-agent.service` running the same command, then
`sudo systemctl enable --now kk-agent`.

## 8. Code gaps to close before production

The scaffold runs in dev mode; for a real deployment finish these:
- **Alembic migrations** (replace `DEV_CREATE_TABLES`); seed `action_types`.
- **Complete `mqtt_bridge.handle_event`**: load active policy → `llm_gateway.reason`
  → `policy_engine.validate_action` → publish action → persist `Event`/`LLMDecision`/
  `Action`; handle acks + update `last_seen_at`.
- **Operators**: upsert the IDaaS subject into `operators` on first call (FK target).
- **Cert lifecycle**: renewal endpoint + revocation pushed to the broker ACL/CRL.
- **Secrets** from KMS, not files in the image.
```



The two deployment "gotchas" that matter most

  1. Don't terminate mTLS at the load balancer. The API goes behind ALB (TLS terminates there → backend). But MQTT must go through NLB in TCP passthrough (or a
  direct EIP) so the per-device client cert reaches the broker — an ALB would break device auth.
  2. Give the broker a real SAN. Reissue broker.pem with subjectAltName=DNS:mqtt.kk.example.com (signed by your intermediate CA). Then the Pi verifies the
  hostname normally and you set tls_insecure = false. The §4 of the doc has the exact openssl command.

  Registering a real Pi (the actual flow)

  1. Dashboard (logged in via IDaaS): register device → copy the one-time enrollment token.
  2. On the Pi: install uv, git clone, cd apps/edge-agent && uv sync, write /etc/kk/agent.toml:
  backend_url = "https://api.kk.example.com"
  broker_host = "mqtt.kk.example.com"
  broker_port = 8883
  tls_insecure = false
  enrollment_token = "<paste-from-dashboard>"
  state_dir = "/var/lib/kk"
  3. sudo KK_AGENT_CONFIG=/etc/kk/agent.toml uv run kk-agent

  The Pi generates its keypair+CSR locally (private key never leaves it), swaps the token for a per-device cert over HTTPS, then connects to the broker over mTLS
  (cert CN = device_id) and goes active in the dashboard. Run it under systemd to survive reboots (unit example in the doc).

  What you must finish in code before this is real (doc §8)

  The scaffold is dev-mode; production needs:
  - Alembic migrations (replace DEV_CREATE_TABLES) + seed the action_types catalog
  - Complete mqtt_bridge.handle_event — it currently returns noop; it needs: load policy → llm_gateway.reason (Qwen) → policy_engine.validate_action → publish
  action → persist Event/LLMDecision/Action + handle acks + update last_seen_at
  - Upsert IDaaS operator on first call (FK target), and turn DEV_AUTH=false
  - Cert renewal/revocation wired to the broker ACL
