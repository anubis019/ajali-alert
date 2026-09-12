from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_role
from app.database import get_db
from app.models import (
    User, EscalationPolicy, EmergencyCategoryEnum,
    ResponderTypeEnum, SeverityEnum, RoleEnum,
)
from app.schemas import (
    EscalationPolicyCreate as PolicyCreate,
    EscalationPolicyUpdate as PolicyUpdate,
    EscalationPolicyRead as PolicyRead,
)

router = APIRouter(prefix="/policies", tags=["Escalation Policies"])


@router.get("/", response_model=List[PolicyRead])
async def list_policies(
    category: Optional[EmergencyCategoryEnum] = Query(None, description="Filter by emergency category"),
    severity: Optional[SeverityEnum] = Query(None, description="Filter by severity"),
    responder_type: Optional[ResponderTypeEnum] = Query(None, description="Filter by responder type"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List escalation policies, optionally filtered by category, severity, or responder type."""
    query = select(EscalationPolicy)
    if category:
        query = query.where(EscalationPolicy.category == category)
    if severity:
        query = query.where(EscalationPolicy.severity == severity)
    if responder_type:
        query = query.where(EscalationPolicy.responder_type == responder_type)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{policy_id}", response_model=PolicyRead)
async def get_policy(
    policy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(EscalationPolicy).where(EscalationPolicy.id == policy_id))
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(404, "Policy not found")
    return policy


@router.post("/", response_model=PolicyRead, status_code=201)
async def create_policy(
    data: PolicyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.admin)),
):
    policy = EscalationPolicy(**data.model_dump())
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy


@router.patch("/{policy_id}", response_model=PolicyRead)
async def update_policy(
    policy_id: int,
    data: PolicyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.admin)),
):
    result = await db.execute(select(EscalationPolicy).where(EscalationPolicy.id == policy_id))
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(404, "Policy not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(policy, k, v)
    await db.commit()
    await db.refresh(policy)
    return policy


@router.delete("/{policy_id}", status_code=204)
async def delete_policy(
    policy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.admin)),
):
    result = await db.execute(select(EscalationPolicy).where(EscalationPolicy.id == policy_id))
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(404, "Policy not found")
    await db.delete(policy)
    await db.commit()
