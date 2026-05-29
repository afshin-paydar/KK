// Operator auth against Alibaba Cloud IDaaS via OIDC (Authorization Code + PKCE).
import { UserManager, WebStorageStateStore } from "oidc-client-ts";

export const userManager = new UserManager({
  authority: import.meta.env.VITE_IDAAS_AUTHORITY,
  client_id: import.meta.env.VITE_IDAAS_CLIENT_ID,
  redirect_uri: import.meta.env.VITE_IDAAS_REDIRECT_URI,
  response_type: "code",
  scope: "openid profile email",
  userStore: new WebStorageStateStore({ store: window.localStorage }),
});

const DEV_AUTH = import.meta.env.VITE_DEV_AUTH === "true";

export async function getAccessToken(): Promise<string | null> {
  // LOCAL ONLY: skip OIDC; backend accepts any token when DEV_AUTH is on.
  if (DEV_AUTH) return "dev";
  const user = await userManager.getUser();
  return user?.access_token ?? null;
}

export const login = () => (DEV_AUTH ? Promise.resolve() : userManager.signinRedirect());
export const logout = () => (DEV_AUTH ? Promise.resolve() : userManager.signoutRedirect());
