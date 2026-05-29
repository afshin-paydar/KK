// Thin API client. Attaches the IDaaS bearer token to every request.
import type { Device, DeviceRegistered, Policy } from "@kk/contracts";
import { getAccessToken } from "../auth/idaas";

const BASE = import.meta.env.VITE_API_BASE ?? "/api";

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = await getAccessToken();
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

export const api = {
  listDevices: () => request<Device[]>("/devices"),
  getDevice: (id: string) => request<Device>(`/devices/${id}`),
  registerDevice: (body: { name: string; location?: string; hardware_model?: string }) =>
    request<DeviceRegistered>("/devices", { method: "POST", body: JSON.stringify(body) }),
  revokeDevice: (id: string) => request<void>(`/devices/${id}/revoke`, { method: "POST" }),
  listPolicies: () => request<Policy[]>("/policies"),
  assignPolicy: (deviceId: string, policyId: string) =>
    request<void>(`/devices/${deviceId}/policy`, {
      method: "POST",
      body: JSON.stringify({ policy_id: policyId }),
    }),
};
