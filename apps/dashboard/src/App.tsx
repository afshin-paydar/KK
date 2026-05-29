import { Link, Route, Routes } from "react-router-dom";
import { DevicesPage } from "./pages/Devices";

export function App() {
  return (
    <div style={{ fontFamily: "system-ui", maxWidth: 960, margin: "0 auto", padding: 24 }}>
      <header style={{ display: "flex", gap: 16, alignItems: "baseline" }}>
        <h1 style={{ marginRight: "auto" }}>Knock Knock</h1>
        <Link to="/">Devices</Link>
        <Link to="/policies">Policies</Link>
      </header>
      <Routes>
        <Route path="/" element={<DevicesPage />} />
        <Route path="/policies" element={<p>Policies (todo)</p>} />
        <Route path="/callback" element={<p>Signing in…</p>} />
      </Routes>
    </div>
  );
}
