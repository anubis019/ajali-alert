from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_role
from app.database import get_db
from app.models import User, Team, ResponderTypeEnum, RoleEnum, RegionEnum
from app.schemas import (
    TeamCreate, TeamUpdate, TeamRead, TeamPerformance,
)

router = APIRouter(prefix="/teams", tags=["Teams"])


@router.get("/", response_model=List[TeamRead])
async def list_teams(
    county: Optional[str] = Query(None, description="Filter by Kenya county"),
    responder_type: Optional[ResponderTypeEnum] = Query(None, description="Filter by responder type"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all emergency response teams, optionally filtered by county or responder type."""
    query = select(Team)
    if county:
        query = query.where(Team.county == county)
    if responder_type:
        query = query.where(Team.responder_type == responder_type)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{team_id}", response_model=TeamRead)
async def get_team(
    team_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(404, "Team not found")
    return team


@router.post("/", response_model=TeamRead, status_code=201)
async def create_team(
    data: TeamCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.admin)),
):
    team = Team(**data.model_dump())
    db.add(team)
    await db.commit()
    await db.refresh(team)
    return team


@router.patch("/{team_id}", response_model=TeamRead)
async def update_team(
    team_id: int,
    data: TeamUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.admin)),
):
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(404, "Team not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(team, k, v)
    await db.commit()
    await db.refresh(team)
    return team


@router.delete("/{team_id}", status_code=204)
async def delete_team(
    team_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.admin)),
):
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(404, "Team not found")
    await db.delete(team)
    await db.commit()
