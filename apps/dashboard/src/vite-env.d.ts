/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_IDAAS_AUTHORITY: string;
  readonly VITE_IDAAS_CLIENT_ID: string;
  readonly VITE_IDAAS_REDIRECT_URI: string;
  readonly VITE_API_BASE: string;
  readonly VITE_DEV_AUTH: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
