"""FastAPI dependencies: operator authentication + role gating."""

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError

from app.config import get_settings
from app.security.idaas import OperatorIdentity, verify_token

# Stub operator used only when DEV_AUTH is enabled.
_DEV_OPERATOR = OperatorIdentity(
    subject="dev-operator",
    email="dev@local",
    display_name="Dev Operator",
    role="admin",
)


async def current_operator(authorization: str = Header(default="")) -> OperatorIdentity:
    # LOCAL ONLY: skip IDaaS entirely and act as a stub admin.
    if get_settings().dev_auth:
        return _DEV_OPERATOR

    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        return await verify_token(token)
    except (JWTError, KeyError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token") from exc


def require_role(*roles: str):
    async def _checker(op: OperatorIdentity = Depends(current_operator)) -> OperatorIdentity:
        if op.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"requires one of {roles}")
        return op

    return _checker
