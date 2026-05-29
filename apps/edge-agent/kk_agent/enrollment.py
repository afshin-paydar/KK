"""Device enrollment: generate keypair + CSR locally, exchange token for a cert.

The private key is generated on the Pi and never leaves it. We send only a CSR.
"""

import json
import uuid

import httpx
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from kk_agent.config import AgentConfig

AGENT_VERSION = "0.1.0"


def _generate_key_and_csr() -> tuple[bytes, str]:
    key = ec.generate_private_key(ec.SECP256R1())
    key_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    # CN is filled by the backend (= device_id); use a placeholder subject here.
    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, "kk-device")]))
        .sign(key, hashes.SHA256())
    )
    csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode()
    return key_pem, csr_pem


def enroll(cfg: AgentConfig) -> uuid.UUID:
    """Run enrollment if no cert exists yet. Returns the assigned device_id."""
    cfg.state_dir.mkdir(parents=True, exist_ok=True)
    key_pem, csr_pem = _generate_key_and_csr()

    resp = httpx.post(
        f"{cfg.backend_url}/enroll",
        json={
            "token": cfg.enrollment_token,
            "csr_pem": csr_pem,
            "agent_version": AGENT_VERSION,
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    cfg.key_path.write_bytes(key_pem)
    cfg.cert_path.write_text(data["client_cert_pem"])
    cfg.ca_path.write_text(data["ca_chain_pem"])
    if data.get("policy_snapshot"):
        cfg.policy_path.write_text(json.dumps(data["policy_snapshot"]))
    return uuid.UUID(data["device_id"])
