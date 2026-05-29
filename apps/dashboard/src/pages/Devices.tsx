import type { Device, DeviceRegistered } from "@kk/contracts";
import { useEffect, useState } from "react";
import { api } from "../api/client";

export function DevicesPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [name, setName] = useState("");
  const [registered, setRegistered] = useState<DeviceRegistered | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = () => api.listDevices().then(setDevices).catch((e) => setError(String(e)));
  useEffect(() => {
    refresh();
  }, []);

  async function register(e: React.FormEvent) {
    e.preventDefault();
    try {
      const result = await api.registerDevice({ name });
      setRegistered(result); // enrollment token is shown exactly once
      setName("");
      refresh();
    } catch (err) {
      setError(String(err));
    }
  }

  return (
    <section>
      <h2>Fleet</h2>
      {error && <p style={{ color: "crimson" }}>{error}</p>}

      <form onSubmit={register} style={{ display: "flex", gap: 8, margin: "12px 0" }}>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Device name" required />
        <button type="submit">Register</button>
      </form>

      {registered && (
        <div style={{ background: "#fffbe6", padding: 12, borderRadius: 8 }}>
          <strong>Enrollment token (shown once):</strong>
          <code style={{ display: "block", wordBreak: "break-all" }}>{registered.enrollment_token}</code>
          <small>Provision this onto {registered.device.name} before {registered.enrollment_expires_at}.</small>
        </div>
      )}

      <table style={{ width: "100%", marginTop: 16, borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>
            <th>Name</th>
            <th>Status</th>
            <th>Agent</th>
            <th>Last seen</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {devices.map((d) => (
            <tr key={d.id} style={{ borderBottom: "1px solid #f0f0f0" }}>
              <td>{d.name}</td>
              <td>{d.status}</td>
              <td>{d.agent_version ?? "—"}</td>
              <td>{d.last_seen_at ?? "never"}</td>
              <td>
                {d.status !== "revoked" && (
                  <button onClick={() => api.revokeDevice(d.id).then(refresh)}>Revoke</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
