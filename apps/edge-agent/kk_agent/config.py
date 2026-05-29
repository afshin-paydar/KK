"""Agent configuration, loaded from a TOML file (default /etc/kk/agent.toml)."""

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AgentConfig:
    backend_url: str          # https base for enrollment
    enrollment_token: str     # one-time, provisioned out of band
    state_dir: Path           # where cert/key/policy snapshot are stored
    camera_index: int = 0
    heartbeat_interval_s: int = 30

    @property
    def key_path(self) -> Path:
        return self.state_dir / "device.key"

    @property
    def cert_path(self) -> Path:
        return self.state_dir / "device.pem"

    @property
    def ca_path(self) -> Path:
        return self.state_dir / "ca-chain.pem"

    @property
    def policy_path(self) -> Path:
        return self.state_dir / "policy.json"


def load_config(path: str = "/etc/kk/agent.toml") -> AgentConfig:
    data = tomllib.loads(Path(path).read_text())
    return AgentConfig(
        backend_url=data["backend_url"],
        enrollment_token=data.get("enrollment_token", ""),
        state_dir=Path(data.get("state_dir", "/var/lib/kk")),
        camera_index=data.get("camera_index", 0),
        heartbeat_interval_s=data.get("heartbeat_interval_s", 30),
    )
