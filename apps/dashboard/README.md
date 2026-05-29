# KK Dashboard

Admin dashboard (React + TypeScript, Vite). Operators authenticate via Alibaba
Cloud IDaaS (OIDC) and manage the device fleet + policies.

## Run

```bash
pnpm install
cp .env.example .env     # fill in IDaaS authority + client id
pnpm dev                 # http://localhost:5173 (proxies /api to :8000)
```

## Layout

```
src/
  auth/idaas.ts     OIDC login + access token (IDaaS)
  api/client.ts     fetch wrapper, attaches bearer token
  pages/Devices.tsx register / list / revoke devices
  App.tsx / main.tsx routing shell
```

Shared types come from `@kk/contracts`.
