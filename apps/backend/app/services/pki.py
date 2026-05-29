"""Device PKI: sign per-device client certificates from a CSR.

The intermediate CA key/cert live only in the backend. CN of the issued cert is
the device_id, which the MQTT broker uses for identity + topic authorization.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from app.config import get_settings


@dataclass
class IssuedCert:
    cert_pem: str
    serial_number: str
    fingerprint_sha256: str
    not_before: datetime
    not_after: datetime


def _load_ca() -> tuple[x509.Certificate, object]:
    settings = get_settings()
    with open(settings.pki_ca_cert, "rb") as f:
        ca_cert = x509.load_pem_x509_certificate(f.read())
    with open(settings.pki_ca_key, "rb") as f:
        ca_key = load_pem_private_key(f.read(), password=None)
    return ca_cert, ca_key


def sign_device_csr(csr_pem: str, device_id: uuid.UUID) -> IssuedCert:
    settings = get_settings()
    csr = x509.load_pem_x509_csr(csr_pem.encode())
    if not csr.is_signature_valid:
        raise ValueError("CSR signature invalid")

    ca_cert, ca_key = _load_ca()
    now = datetime.now(timezone.utc)
    not_after = now + timedelta(days=settings.pki_device_cert_ttl_days)

    subject = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, str(device_id))])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(csr.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(not_after)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.ExtendedKeyUsage([x509.ExtendedKeyUsageOID.CLIENT_AUTH]), critical=False
        )
        .sign(ca_key, hashes.SHA256())
    )

    pem = cert.public_bytes(serialization.Encoding.PEM).decode()
    return IssuedCert(
        cert_pem=pem,
        serial_number=format(cert.serial_number, "x"),
        fingerprint_sha256=cert.fingerprint(hashes.SHA256()).hex(),
        not_before=now,
        not_after=not_after,
    )


def ca_chain_pem() -> str:
    with open(get_settings().pki_ca_cert) as f:
        return f.read()
