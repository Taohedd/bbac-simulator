"""
Pydantic v2 schemas for User and UserBaseline entities.
Used for request validation and response serialization in FastAPI routes.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# Role definition — matches the roles used in the telemetry profiles module
# ---------------------------------------------------------------------------
UserRole = Literal["admin", "analyst", "employee", "contractor", "viewer"]


# ---------------------------------------------------------------------------
# User Schemas
# ---------------------------------------------------------------------------
class UserBase(BaseModel):
    """Shared attributes for all user schemas."""
    username: str = Field(..., min_length=3, max_length=255,
                          description="Unique username for the user")
    email: EmailStr = Field(...,
                            description="Valid email address — format is validated")
    role: UserRole = Field(...,
                           description="User role: admin | analyst | employee | contractor | viewer")
    is_active: bool = Field(default=True,
                            description="Whether the user account is currently active")


class UserCreate(UserBase):
    """Schema for creating a new user via POST /api/users."""
    pass


class UserUpdate(BaseModel):
    """
    Schema for partially updating a user via PATCH /api/users/{id}.
    All fields are optional — only provided fields are updated.
    """
    username: Optional[str] = Field(None, min_length=3, max_length=255)
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """Schema returned by the API for a single user."""
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserDetailResponse(UserResponse):
    """
    Extended user response that includes the behavioral baseline.
    Returned by GET /api/users/{id} for deep-dive profile views.
    """
    baseline: Optional["UserBaselineResponse"] = None

    model_config = ConfigDict(from_attributes=True)


class UserSummary(BaseModel):
    """
    Lightweight user representation for dashboard stats and log stream entries.
    Avoids serializing the full user object in high-volume real-time contexts.
    """
    id: uuid.UUID
    username: str
    role: UserRole
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# UserBaseline Schemas
# ---------------------------------------------------------------------------
class UserBaselineBase(BaseModel):
    """Base schema for user behavioral baseline attributes."""
    avg_login_hour: Optional[float] = Field(
        None,
        description="Average hour of day the user logs in (0.0–23.99)",
    )
    common_subnet: Optional[str] = Field(
        None, max_length=255,
        description="Most frequently used IP subnet prefix (e.g. '192.168.1')",
    )
    common_device: Optional[str] = Field(
        None, max_length=255,
        description="Most frequently used device fingerprint string",
    )
    typical_actions_json: Optional[Dict[str, Any]] = Field(
        None,
        description="JSON map of action names to frequency counts",
    )

    @field_validator("avg_login_hour", mode="before")
    @classmethod
    def validate_login_hour(cls, v: Optional[float]) -> Optional[float]:
        """Login hour must be in the 0–24 range (represents hour of the day)."""
        if v is None:
            return v
        v = float(v)
        if not (0.0 <= v < 24.0):
            raise ValueError(
                f"avg_login_hour must be between 0.0 and 23.99, got {v}"
            )
        return v


class UserBaselineResponse(UserBaselineBase):
    """Schema returned by the API for a user's behavioral baseline."""
    id: uuid.UUID
    user_id: uuid.UUID
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Rebuild model to resolve the forward reference in UserDetailResponse
UserDetailResponse.model_rebuild()