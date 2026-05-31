# KK Dashboard

Admin dashboard (Next.js + React + TypeScript, Tailwind CSS, Ant Design).
Operators authenticate via Alibaba Cloud IDaaS (OIDC) and manage the device
fleet + policies.

## Run

```bash
pnpm install
cp .env.example .env     # fill in IDaaS authority + client id
pnpm dev                 # http://localhost:5173 (rewrites /api, /enroll to :8000)
```

## Layout

```
app/
  layout.tsx           root layout (AntdRegistry + ConfigProvider + chrome)
  page.tsx             devices (/)
  policies/page.tsx    /policies (todo)
  callback/page.tsx    OIDC redirect target
  globals.css          Tailwind directives
components/
  devices/DevicesPage.tsx
lib/
  api/client.ts        fetch wrapper, attaches bearer token
  auth/idaas.ts        OIDC login + access token (IDaaS)
next.config.ts         /api, /enroll rewrites to BACKEND_URL
tailwind.config.ts     Tailwind v3 (preflight disabled to defer to AntD reset)
```

Shared types come from `@kk/contracts`.
