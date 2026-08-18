"""
Pydantic v2 schemas for RiskScore and AccessDecision entities.
Also defines the RiskLevel enum and combined response schemas used
by the dashboard, WebSocket stream, and user detail views.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------
class DecisionEnum(str, Enum):
    """
    Possible access control decisions produced by the policy enforcement engine.
    Using str mixin ensures JSON serialisation returns the string value directly.
    """
    ALLOW = "ALLOW"
    MFA_CHALLENGE = "MFA_CHALLENGE"
    BLOCK = "BLOCK"


class RiskLevel(str, Enum):
    """
    Human-readable risk classification derived from a numeric risk score.
    Used by the frontend RiskBadge component and AlertsFeed to display
    colour-coded severity labels without re-implementing threshold logic in JS.

    Thresholds mirror settings.RISK_LOW_THRESHOLD and RISK_HIGH_THRESHOLD.
    Use the helper function score_to_risk_level() to compute this consistently.
    """
    LOW = "LOW"          # score 0–30    → green badge  → ALLOW
    MEDIUM = "MEDIUM"    # score 31–69   → amber badge  → MFA_CHALLENGE
    HIGH = "HIGH"        # score 70–100  → red badge    → BLOCK


def score_to_risk_level(
    score: float,
    low_threshold: float = 30.0,
    high_threshold: float = 70.0,
) -> RiskLevel:
    """
    Converts a numeric risk score into a RiskLevel enum value.
    Called by the enforcement module and API routes to populate risk_level fields.

    Args:
        score: Numeric risk score between 0.0 and 100.0.
        low_threshold: Upper bound for LOW risk (default 30, from settings).
        high_threshold: Lower bound for HIGH risk (default 70, from settings).

    Returns:
        RiskLevel.LOW, RiskLevel.MEDIUM, or RiskLevel.HIGH.
    """
    if score <= low_threshold:
        return RiskLevel.LOW
    if score >= high_threshold:
        return RiskLevel.HIGH
    return RiskLevel.MEDIUM


# ---------------------------------------------------------------------------
# Risk Score Schemas
# ---------------------------------------------------------------------------
class RiskScoreBase(BaseModel):
    """Shared attributes for risk score schemas."""
    score: float = Field(
        ..., ge=0.0, le=100.0,
        description="Anomaly risk score between 0 (normal) and 100 (highly anomalous)"
    )
    features_json: Optional[Dict[str, Any]] = Field(
        None,
        description="Feature vector passed to Isolation Forest — for audit and debugging"
    )


class RiskScoreCreate(RiskScoreBase):
    """Schema used by the analytics engine to persist a computed risk score."""
    user_id: uuid.UUID = Field(..., description="ID of the user whose behaviour was scored")
    log_id: uuid.UUID = Field(..., description="ID of the ActivityLog that triggered scoring")


class RiskScoreResponse(RiskScoreBase):
    """Schema for a single risk score returned by the API."""
    id: uuid.UUID
    user_id: uuid.UUID
    log_id: uuid.UUID
    computed_at: datetime
    risk_level: Optional[RiskLevel] = Field(
        None, description="Named risk classification derived from the score"
    )

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Access Decision Schemas
# ---------------------------------------------------------------------------
class AccessDecisionBase(BaseModel):
    """Shared attributes for access decision schemas."""
    decision: DecisionEnum = Field(
        ..., description="Enforcement decision: ALLOW | MFA_CHALLENGE | BLOCK"
    )
    reason: Optional[str] = Field(
        None, max_length=1000,
        description="Human-readable explanation of why this decision was made"
    )


class AccessDecisionCreate(AccessDecisionBase):
    """Schema used by the enforcement engine to persist an access decision."""
    user_id: uuid.UUID = Field(..., description="ID of the affected user")
    risk_score_id: uuid.UUID = Field(
        ..., description="ID of the RiskScore that triggered this decision"
    )


class AccessDecisionResponse(AccessDecisionBase):
    """Schema for a single access decision returned by the API."""
    id: uuid.UUID
    user_id: uuid.UUID
    risk_score_id: uuid.UUID
    decided_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Combined / Aggregate Schemas
# ---------------------------------------------------------------------------
class RiskScoreWithDecisionResponse(RiskScoreResponse):
    """
    Risk score combined with its enforcement decision.
    Used by the dashboard stats panel, WebSocket stream, and user detail view
    to avoid requiring two separate API calls per scored event.
    """
    decision: Optional[DecisionEnum] = Field(
        None, description="Access decision produced from this risk score"
    )
    decision_reason: Optional[str] = Field(
        None, max_length=1000,
        description="Reason text from the associated AccessDecision"
    )
    decision_id: Optional[uuid.UUID] = Field(
        None, description="ID of the associated AccessDecision record"
    )

    model_config = ConfigDict(from_attributes=True)


class UserRiskSummary(BaseModel):
    """
    Lightweight schema combining a user's identity with their current risk state.
    Populated by the users list endpoint and the dashboard active-users panel.
    Avoids serialising the full ORM object in high-volume contexts.
    """
    user_id: uuid.UUID
    username: str
    role: str
    is_active: bool
    latest_score: Optional[float] = Field(
        None, description="Most recent computed risk score for this user"
    )
    latest_decision: Optional[DecisionEnum] = Field(
        None, description="Most recent enforcement decision for this user"
    )
    risk_level: Optional[RiskLevel] = Field(
        None, description="Risk level label derived from the latest score"
    )
    last_seen: Optional[datetime] = Field(
        None, description="Timestamp of the most recent activity log for this user"
    )

    model_config = ConfigDict(from_attributes=True)