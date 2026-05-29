"""Operator auth via Alibaba Cloud IDaaS (OIDC).

Validates the bearer JWT against the IDaaS JWKS and maps it to an operator
identity + role. JWKS is fetched lazily and cached.
"""

from dataclasses import dataclass

import httpx
from jose import jwt

from app.config import get_settings

_jwks_cache: dict | None = None


@dataclass
class OperatorIdentity:
    subject: str
    email: str | None
    display_name: str | None
    role: str  # admin|operator|viewer


async def _get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache is None:
        settings = get_settings()
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(settings.idaas_jwks_url)
            resp.raise_for_status()
            _jwks_cache = resp.json()
    return _jwks_cache


def _role_from_claims(claims: dict) -> str:
    groups = claims.get("groups") or claims.get("roles") or []
    if "kk-admin" in groups:
        return "admin"
    if "kk-operator" in groups:
        return "operator"
    return "viewer"


async def verify_token(token: str) -> OperatorIdentity:
    settings = get_settings()
    jwks = await _get_jwks()
    claims = jwt.decode(
        token,
        jwks,
        algorithms=["RS256"],
        audience=settings.idaas_audience,
        issuer=settings.idaas_issuer,
    )
    return OperatorIdentity(
        subject=claims["sub"],
        email=claims.get("email"),
        display_name=claims.get("name"),
        role=_role_from_claims(claims),
    )
