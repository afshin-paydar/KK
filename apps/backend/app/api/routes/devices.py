"""Device registry routes (operator-authenticated)."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_operator, require_role
from app.config import get_settings
from app.database import get_db
from app.models import Device
from app.schemas import DeviceCreate, DeviceOut, DeviceRegistered

router = APIRouter(prefix="/api/devices", tags=["devices"])


@router.post("", response_model=DeviceRegistered)
async def register_device(
    body: DeviceCreate,
    db: AsyncSession = Depends(get_db),
    op=Depends(require_role("admin", "operator")),
):
    settings = get_settings()
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.enrollment_token_ttl_minutes)

    device = Device(
        name=body.name,
        description=body.description,
        location=body.location,
        hardware_model=body.hardware_model,
        serial=body.serial,
        status="pending",
        enrollment_token_hash=hashlib.sha256(token.encode()).hexdigest(),
        enrollment_expires_at=expires,
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)

    # token is returned exactly once; only its hash is stored
    return DeviceRegistered(
        device=DeviceOut.model_validate(device),
        enrollment_token=token,
        enrollment_expires_at=expires,
    )


@router.get("", response_model=list[DeviceOut])
async def list_devices(db: AsyncSession = Depends(get_db), op=Depends(current_operator)):
    rows = (await db.execute(select(Device).order_by(Device.created_at.desc()))).scalars().all()
    return [DeviceOut.model_validate(r) for r in rows]


@router.get("/{device_id}", response_model=DeviceOut)
async def get_device(
    device_id: uuid.UUID, db: AsyncSession = Depends(get_db), op=Depends(current_operator)
):
    device = await db.get(Device, device_id)
    if not device:
        raise HTTPException(404, "device not found")
    return DeviceOut.model_validate(device)


@router.post("/{device_id}/revoke", status_code=204)
async def revoke_device(
    device_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    op=Depends(require_role("admin")),
):
    device = await db.get(Device, device_id)
    if not device:
        raise HTTPException(404, "device not found")
    device.status = "revoked"
    # TODO: mark device_certificates revoked + push broker ACL/CRL update
    await db.commit()
