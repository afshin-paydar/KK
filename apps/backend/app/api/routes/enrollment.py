"""Device enrollment: CSR signing, token-authenticated (not IDaaS).

The Pi presents its one-time enrollment token + a CSR. We verify the token
against the pending device, sign a per-device client cert, record it, and return
the cert + CA chain + broker config + initial policy snapshot.
"""

import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import Device, DeviceCertificate, PolicyAssignment
from app.schemas import BrokerConfig, EnrollRequest, EnrollResponse
from app.services import pki

router = APIRouter(tags=["enrollment"])


@router.post("/enroll", response_model=EnrollResponse)
async def enroll(body: EnrollRequest, db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()

    device = (
        await db.execute(select(Device).where(Device.enrollment_token_hash == token_hash))
    ).scalar_one_or_none()
    if not device or device.status != "pending":
        raise HTTPException(401, "invalid enrollment token")
    if device.enrollment_expires_at and device.enrollment_expires_at < datetime.now(timezone.utc):
        raise HTTPException(401, "enrollment token expired")

    try:
        issued = pki.sign_device_csr(body.csr_pem, device.id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    db.add(
        DeviceCertificate(
            device_id=device.id,
            serial_number=issued.serial_number,
            fingerprint_sha256=issued.fingerprint_sha256,
            subject_cn=str(device.id),
            not_before=issued.not_before,
            not_after=issued.not_after,
            status="active",
        )
    )

    device.status = "active"
    device.enrolled_at = datetime.now(timezone.utc)
    device.enrollment_token_hash = None  # one-time use
    device.agent_version = body.agent_version
    device.vision_model_version = body.vision_model_version
    device.tts_model_version = body.tts_model_version
    await db.commit()

    # initial policy snapshot, if one is assigned
    assignment = (
        await db.execute(
            select(PolicyAssignment).where(
                PolicyAssignment.device_id == device.id, PolicyAssignment.is_active.is_(True)
            )
        )
    ).scalar_one_or_none()
    snapshot = assignment.policy.spec if assignment else None

    return EnrollResponse(
        device_id=device.id,
        client_cert_pem=issued.cert_pem,
        ca_chain_pem=pki.ca_chain_pem(),
        broker=BrokerConfig(
            host=settings.mqtt_host,
            port=settings.mqtt_port,
            topic_prefix=f"devices/{device.id}",
        ),
        policy_snapshot=snapshot,
    )
