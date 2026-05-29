"""Policy authoring + assignment (operator-authenticated)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.database import get_db
from app.models import Device, Policy, PolicyAssignment
from app.schemas import PolicyAssign, PolicyCreate, PolicyOut

router = APIRouter(prefix="/api", tags=["policies"])


@router.post("/policies", response_model=PolicyOut)
async def create_policy(
    body: PolicyCreate,
    db: AsyncSession = Depends(get_db),
    op=Depends(require_role("admin", "operator")),
):
    # next version for this policy name
    current_max = (
        await db.execute(select(func.max(Policy.version)).where(Policy.name == body.name))
    ).scalar()
    version = (current_max or 0) + 1

    policy = Policy(
        name=body.name, version=version, description=body.description, spec=body.spec
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return PolicyOut.model_validate(policy)


@router.get("/policies", response_model=list[PolicyOut])
async def list_policies(db: AsyncSession = Depends(get_db), op=Depends(require_role("admin", "operator", "viewer"))):
    rows = (await db.execute(select(Policy).order_by(Policy.name, Policy.version.desc()))).scalars().all()
    return [PolicyOut.model_validate(r) for r in rows]


@router.post("/devices/{device_id}/policy", status_code=204)
async def assign_policy(
    device_id: uuid.UUID,
    body: PolicyAssign,
    db: AsyncSession = Depends(get_db),
    op=Depends(require_role("admin", "operator")),
):
    device = await db.get(Device, device_id)
    policy = await db.get(Policy, body.policy_id)
    if not device or not policy:
        raise HTTPException(404, "device or policy not found")

    # deactivate previous assignment(s), then add the new active one
    await db.execute(
        update(PolicyAssignment)
        .where(PolicyAssignment.device_id == device_id, PolicyAssignment.is_active.is_(True))
        .values(is_active=False)
    )
    db.add(PolicyAssignment(device_id=device_id, policy_id=policy.id, is_active=True))
    await db.commit()
    # TODO: publish kk.config.v1 policy snapshot to devices/{id}/config
