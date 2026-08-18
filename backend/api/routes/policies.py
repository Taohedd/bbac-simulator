"""
API routes for Policy management.
Provides CRUD endpoints for access control policies, enforcing the
invariant that at most one policy is active at any time.
"""

import uuid
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from api.dependencies import require_admin

from database.connection import get_db
from database.models import Policy
from schemas.policy import (
    PolicyCreate,
    PolicyUpdate,
    PolicyResponse,
    ActivePolicyResponse,
)

router = APIRouter(prefix="/policies", tags=["Policies"])


@router.get("/", response_model=List[PolicyResponse])
async def get_policies(db: AsyncSession = Depends(get_db), current_user: Dict[str, str] = Depends(require_admin)):
    """Retrieve all policies, newest first."""
    result = await db.execute(select(Policy).order_by(Policy.created_at.desc()))
    return result.scalars().all()


@router.get("/active", response_model=ActivePolicyResponse)
async def get_active_policy(db: AsyncSession = Depends(get_db), current_user: Dict[str, str] = Depends(require_admin)):
    """
    Retrieve the currently active policy's thresholds only.
    Lightweight response — matches what modules/policy/rules.py needs
    internally, and avoids exposing created_at/is_active to callers
    that only care about the threshold values.
    """
    result = await db.execute(
        select(Policy).where(Policy.is_active == True).limit(1)
    )
    policy = result.scalar_one_or_none()

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active policy found"
        )
    return policy


@router.get("/{policy_id}", response_model=PolicyResponse)
async def get_policy(policy_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: Dict[str, str] = Depends(require_admin)):
    """Retrieve a specific policy by ID."""
    result = await db.execute(select(Policy).where(Policy.id == policy_id))
    policy = result.scalar_one_or_none()

    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    return policy


@router.post("/", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_policy(policy_in: PolicyCreate, db: AsyncSession = Depends(get_db), current_user: Dict[str, str] = Depends(require_admin)):
    """
    Create a new policy. PolicyCreate's model_validator already guarantees
    low_threshold < high_threshold for this request on its own, so no merge
    check is needed here — unlike update_policy below.
    If is_active is True, deactivates every other policy first.
    """
    if policy_in.is_active:
        await _deactivate_all_policies(db)

    new_policy = Policy(**policy_in.model_dump())
    db.add(new_policy)
    await db.commit()
    await db.refresh(new_policy)
    return new_policy


@router.patch("/{policy_id}", response_model=PolicyResponse)
async def update_policy(
    policy_id: uuid.UUID,
    policy_in: PolicyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, str] = Depends(require_admin),
):
    """
    Partially update a policy.

    CRITICAL: PolicyUpdate only validates low < high when BOTH fields are
    present in the SAME request. If a request changes only one threshold,
    we must merge it against the policy's CURRENT stored value and
    re-validate the combined result before applying — otherwise a single-
   -field update can silently corrupt the policy into low >= high, which
    would make the enforcement engine produce backwards access decisions.
    """
    result = await db.execute(select(Policy).where(Policy.id == policy_id))
    policy = result.scalar_one_or_none()

    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")

    update_data = policy_in.model_dump(exclude_unset=True)

    # Merge incoming changes against current stored values, then validate
    merged_low = update_data.get("low_threshold", policy.low_threshold)
    merged_high = update_data.get("high_threshold", policy.high_threshold)

    if merged_low >= merged_high:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Resulting low_threshold ({merged_low}) must be strictly less "
                f"than high_threshold ({merged_high}). This update would "
                f"corrupt the policy's threshold ordering."
            ),
        )

    if update_data.get("is_active") is True:
        await _deactivate_all_policies(db, exclude_id=policy_id)

    for key, value in update_data.items():
        setattr(policy, key, value)

    await db.commit()
    await db.refresh(policy)
    return policy


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy(policy_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: Dict[str, str] = Depends(require_admin)):
    """
    Delete a policy. Refuses to delete the only currently active policy,
    so the system can never end up with zero active policies (which would
    silently fall back to settings.RISK_LOW_THRESHOLD / RISK_HIGH_THRESHOLD
    in modules/policy/rules.py — acceptable, but should be a deliberate
    administrative choice, not an accident).
    """
    result = await db.execute(select(Policy).where(Policy.id == policy_id))
    policy = result.scalar_one_or_none()

    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")

    if policy.is_active:
        active_count = await db.scalar(
            select(func.count(Policy.id)).where(Policy.is_active == True)
        )
        if active_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the only active policy",
            )

    await db.delete(policy)
    await db.commit()


async def _deactivate_all_policies(
    db: AsyncSession, exclude_id: Optional[uuid.UUID] = None
) -> None:
    """
    Sets is_active=False on every active policy except exclude_id, enforcing
    the invariant that at most one policy is active at a time.

    Note: this commits independently of the caller's subsequent commit.
    This is a deliberate simplification for the academic scope of this
    project — a stricter implementation would defer this commit and let
    the caller's single transaction cover both operations atomically.
    """
    query = select(Policy).where(Policy.is_active == True)
    if exclude_id:
        query = query.where(Policy.id != exclude_id)

    result = await db.execute(query)
    active_policies = result.scalars().all()

    for p in active_policies:
        p.is_active = False

    if active_policies:
        await db.commit()