"""
API routes for User management.
Provides CRUD endpoints for users, their behavioral baselines, a risk-aware
summary listing for the dashboard table, and recent decision history for
the user detail deep-dive view.
"""

import uuid
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from api.dependencies import require_admin

from database.connection import get_db
from database.models import User, UserBaseline, RiskScore, AccessDecision
from modules.policy.enforcement import PolicyEnforcer
from schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserDetailResponse,
    UserBaselineResponse,
)
from schemas.risk import UserRiskSummary, AccessDecisionResponse, score_to_risk_level
from config import settings

router = APIRouter(prefix="/users", tags=["Users"])

_enforcer = PolicyEnforcer()


@router.get("/", response_model=List[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, str] = Depends(require_admin),
):
    """Retrieve a paginated list of all users (basic profile fields only)."""
    query = (
        select(User)
        .order_by(User.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/summary", response_model=List[UserRiskSummary])
async def get_users_risk_summary(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, str] = Depends(require_admin),
):
    """
    Retrieves all users combined with their current risk state — used by
    the UserTable.tsx component to render risk badges without an N+1
    API call per row.

    Note: this query uses PostgreSQL's DISTINCT ON, which is specific to
    this project's chosen database (PostgreSQL + TimescaleDB).
    """
    # Latest RiskScore per user via PostgreSQL DISTINCT ON
    latest_scores = (
        select(
            RiskScore.user_id,
            RiskScore.id.label("risk_score_id"),
            RiskScore.score,
            RiskScore.computed_at,
        )
        .distinct(RiskScore.user_id)
        .order_by(RiskScore.user_id, RiskScore.computed_at.desc())
        .subquery()
    )

    query = (
        select(
            User.id,
            User.username,
            User.role,
            User.is_active,
            latest_scores.c.score,
            latest_scores.c.computed_at,
            AccessDecision.decision,
        )
        .outerjoin(latest_scores, latest_scores.c.user_id == User.id)
        .outerjoin(
            AccessDecision,
            AccessDecision.risk_score_id == latest_scores.c.risk_score_id,
        )
        .order_by(User.username)
    )
    result = await db.execute(query)
    rows = result.all()

    summaries: List[UserRiskSummary] = []
    for user_id, username, role, is_active, score, computed_at, decision in rows:
        summaries.append(
            UserRiskSummary(
                user_id=user_id,
                username=username,
                role=role,
                is_active=is_active,
                latest_score=score,
                latest_decision=decision,
                risk_level=(
                    score_to_risk_level(
                        score,
                        settings.RISK_LOW_THRESHOLD,
                        settings.RISK_HIGH_THRESHOLD,
                    )
                    if score is not None
                    else None
                ),
                last_seen=computed_at,
            )
        )
    return summaries


@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    current_user: Dict[str, str] = Depends(require_admin),
    """
    Retrieve a single user with their behavioral baseline included —
    powers the UserDetailModal deep-dive view.

    Uses selectinload() to eagerly fetch the baseline relationship.
    Async SQLAlchemy cannot lazy-load relationships after the session
    context — accessing user.baseline without eager loading would raise
    a MissingGreenlet error during response serialization.
    """
    query = (
        select(User)
        .options(selectinload(User.baseline))
        .where(User.id == user_id)
    )
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.get("/{user_id}/decisions", response_model=List[AccessDecisionResponse])
async def get_user_decisions(
    user_id: uuid.UUID,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, str] = Depends(require_admin),
):
    """
    Retrieves the most recent access decisions for a user, newest first —
    powers the decision history panel in UserDetailModal.
    """
    user_exists = await db.scalar(select(User.id).where(User.id == user_id))
    if not user_exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return await _enforcer.get_recent_decisions(db, user_id, limit=limit)


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user_in: UserCreate, db: AsyncSession = Depends(get_db), current_user: Dict[str, str] = Depends(require_admin)):
    """Create a new user."""
    existing = await db.execute(
        select(User).where(
            (User.username == user_in.username) | (User.email == user_in.email)
        )
    )
    if existing.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered",
        )

    new_user = User(**user_in.model_dump())
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    user_in: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, str] = Depends(require_admin),
):
    """
    Partially update a user. Only fields present in the request body
    are changed — matches PATCH semantics (PUT would imply full replacement).
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    update_data = user_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: Dict[str, str] = Depends(require_admin)):
    """Delete a user. Cascades to their logs, baseline, sessions, and decisions."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await db.delete(user)
    await db.commit()


@router.get("/{user_id}/baseline", response_model=UserBaselineResponse)
async def get_user_baseline(user_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: Dict[str, str] = Depends(require_admin)):
    """Retrieve the behavioral baseline for a specific user."""
    user_exists = await db.scalar(select(User.id).where(User.id == user_id))
    if not user_exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    result = await db.execute(
        select(UserBaseline).where(UserBaseline.user_id == user_id)
    )
    baseline = result.scalar_one_or_none()

    if not baseline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Baseline not yet computed for this user",
        )

    return baseline