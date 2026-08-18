"""
Pydantic v2 schemas for Policy entities.
Used for request validation and response serialization in FastAPI routes.

IMPORTANT — partial update validation gap:
PolicyUpdate only validates thresholds when BOTH are provided in the same
request. The PATCH route handler in api/routes/policies.py must load the
current policy from the database first and check that the merged result
(existing values + incoming changes) still satisfies low < high before
committing. Schema validation alone is not sufficient for partial updates.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ---------------------------------------------------------------------------
# Policy Base
# ---------------------------------------------------------------------------
class PolicyBase(BaseModel):
    """Shared attributes for all policy schemas."""

    name: str = Field(
        ..., min_length=1, max_length=255,
        description="Unique human-readable policy name"
    )
    low_threshold: float = Field(
        ..., ge=0.0, le=100.0,
        description=(
            "Risk scores at or below this value → ALLOW. "
            "Must be strictly less than high_threshold."
        )
    )
    high_threshold: float = Field(
        ..., ge=0.0, le=100.0,
        description=(
            "Risk scores at or above this value → BLOCK. "
            "Scores between low and high → MFA_CHALLENGE."
        )
    )
    is_active: bool = Field(
        default=True,
        description="Only one policy should be active at a time"
    )

    @model_validator(mode="after")
    def check_thresholds(self) -> "PolicyBase":
        """
        Enforces low_threshold < high_threshold (strictly less than).
        Equal values would eliminate the MFA_CHALLENGE zone entirely,
        breaking the three-tier enforcement model.
        Mirrors the SQL CHECK constraint in database/init.sql.
        """
        if self.low_threshold >= self.high_threshold:
            raise ValueError(
                f"low_threshold ({self.low_threshold}) must be strictly less than "
                f"high_threshold ({self.high_threshold}). "
                "Equal values eliminate the MFA zone."
            )
        return self


# ---------------------------------------------------------------------------
# Policy Create
# ---------------------------------------------------------------------------
class PolicyCreate(PolicyBase):
    """Schema for creating a new policy via POST /api/policies."""
    pass


# ---------------------------------------------------------------------------
# Policy Update
# ---------------------------------------------------------------------------
class PolicyUpdate(BaseModel):
    """
    Schema for partially updating a policy via PATCH /api/policies/{id}.
    All fields are optional — only provided fields are updated.

    WARNING: When only one threshold is provided, this validator cannot check
    against the other threshold stored in the DB. The route handler MUST
    load the existing policy, merge the changes, and re-validate the result
    before committing. See api/routes/policies.py for the implementation.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    low_threshold: Optional[float] = Field(None, ge=0.0, le=100.0)
    high_threshold: Optional[float] = Field(None, ge=0.0, le=100.0)
    is_active: Optional[bool] = None

    @model_validator(mode="after")
    def check_thresholds_if_both_provided(self) -> "PolicyUpdate":
        """
        Only validates threshold ordering when BOTH values are in this request.
        For single-field updates, the route handler performs the merged check.
        """
        if self.low_threshold is not None and self.high_threshold is not None:
            if self.low_threshold >= self.high_threshold:
                raise ValueError(
                    f"low_threshold ({self.low_threshold}) must be strictly less than "
                    f"high_threshold ({self.high_threshold})."
                )
        return self


# ---------------------------------------------------------------------------
# Policy Response
# ---------------------------------------------------------------------------
class PolicyResponse(PolicyBase):
    """Schema returned by the API for a single policy."""
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Active Policy Response
# Used by the enforcement engine to quickly retrieve threshold values
# without deserialising the full policy object on every access decision.
# ---------------------------------------------------------------------------
class ActivePolicyResponse(BaseModel):
    """
    Lightweight schema containing only the threshold values of the active policy.
    Imported by modules/policy/enforcement.py to make access decisions.
    """
    id: uuid.UUID
    name: str
    low_threshold: float
    high_threshold: float

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Policy List Response
# ---------------------------------------------------------------------------
class PolicyListResponse(BaseModel):
    """
    Wrapper returned by GET /api/policies.
    Includes count metadata for the frontend policy management table.
    """
    items: list[PolicyResponse]
    total: int = Field(..., description="Total number of policies in the database")
    active_count: int = Field(
        ..., description="Number of currently active policies"
    )