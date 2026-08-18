"""
API routes for the Security Administrator Dashboard.
Provides aggregated statistics, decision breakdowns, and a 24-hour
timeline of risk activity for the frontend dashboard view.
"""

import logging
from typing import Dict, List
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from database.models import User, ActivityLog, AccessDecision, RiskScore
from api.websocket import manager
from api.dependencies import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# ---------------------------------------------------------------------------
# Response Schemas
# Defined here rather than in schemas/ since dashboard stats are a route-
# specific aggregate view, not a persisted entity.
# ---------------------------------------------------------------------------
class DecisionBreakdown(BaseModel):
    """Count of each access decision type within the reporting window."""
    ALLOW: int = 0
    MFA_CHALLENGE: int = 0
    BLOCK: int = 0


class DashboardStatsResponse(BaseModel):
    """High-level statistics for the dashboard summary cards."""
    total_active_accounts: int = Field(
        ..., description="Users with is_active=True (registered, not disabled)"
    )
    users_active_24h: int = Field(
        ..., description="Distinct users with at least one log in the last 24h"
    )
    events_24h: int = Field(..., description="Total activity logs in the last 24h")
    decisions_24h: DecisionBreakdown
    anomaly_rate_percent: float = Field(
        ..., description="(MFA_CHALLENGE + BLOCK) / total decisions, as a percentage"
    )
    average_risk_score_24h: float = Field(
        ..., description="Mean computed risk score across all logs in the last 24h"
    )
    connected_dashboard_clients: int = Field(
        ..., description="Number of admin browsers currently connected via WebSocket"
    )


class TimelineBucket(BaseModel):
    """One hourly bucket in the 24-hour activity timeline."""
    time: str
    ALLOW: int = 0
    MFA_CHALLENGE: int = 0
    BLOCK: int = 0
    avg_risk_score: float = 0.0


class TimelineResponse(BaseModel):
    """24-hour timeline of decisions and average risk score, for charting."""
    timeline: List[TimelineBucket]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, str] = Depends(require_admin),
) -> DashboardStatsResponse:
    """
    Retrieves high-level statistics for the dashboard summary cards:
    account counts, recent activity volume, decision breakdown, average
    risk score, and live admin connection count.
    """
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=24)

    # 1. Total active accounts (not disabled)
    total_active_accounts = await db.scalar(
        select(func.count(User.id)).where(User.is_active == True)
    ) or 0

    # 2. Distinct users with activity in the last 24h
    users_active_24h = await db.scalar(
        select(func.count(func.distinct(ActivityLog.user_id))).where(
            ActivityLog.timestamp >= window_start
        )
    ) or 0

    # 3. Total events in the last 24h
    events_24h = await db.scalar(
        select(func.count(ActivityLog.id)).where(
            ActivityLog.timestamp >= window_start
        )
    ) or 0

    # 4. Average risk score in the last 24h — the core BBAC metric
    average_risk_score_24h = await db.scalar(
        select(func.avg(RiskScore.score)).where(
            RiskScore.computed_at >= window_start
        )
    ) or 0.0

    # 5. Decision breakdown in the last 24h
    decisions_result = await db.execute(
        select(AccessDecision.decision, func.count(AccessDecision.id))
        .where(AccessDecision.decided_at >= window_start)
        .group_by(AccessDecision.decision)
    )
    decision_counts = {"ALLOW": 0, "MFA_CHALLENGE": 0, "BLOCK": 0}
    for decision_type, count in decisions_result:
        if decision_type in decision_counts:
            decision_counts[decision_type] = count

    total_decisions = sum(decision_counts.values())
    anomalies = decision_counts["MFA_CHALLENGE"] + decision_counts["BLOCK"]
    anomaly_rate = (anomalies / total_decisions * 100) if total_decisions > 0 else 0.0

    return DashboardStatsResponse(
        total_active_accounts=total_active_accounts,
        users_active_24h=users_active_24h,
        events_24h=events_24h,
        decisions_24h=DecisionBreakdown(**decision_counts),
        anomaly_rate_percent=round(anomaly_rate, 2),
        average_risk_score_24h=round(float(average_risk_score_24h), 2),
        connected_dashboard_clients=manager.get_connection_count(),
    )


@router.get("/timeline", response_model=TimelineResponse)
async def get_activity_timeline(
    db: AsyncSession = Depends(get_db),
) -> TimelineResponse:
    """
    Retrieves an hourly breakdown of access decisions and average risk score
    over the last 24 hours, for the dashboard's global overview chart.

    Implementation note: grouping is done in Python rather than with
    TimescaleDB's time_bucket() for cross-database simplicity in this
    academic simulator. This is correct ONLY because the window is exactly
    24 hours, so each hour-of-day label ("%H:00") appears exactly once.
    A production system or a wider time window should use time_bucket()
    instead — noted as a recommended future extension.
    """
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=24)

    # Fetch decisions joined with their risk scores for the avg_risk_score field
    decisions_result = await db.execute(
        select(
            AccessDecision.decided_at,
            AccessDecision.decision,
            RiskScore.score,
        )
        .join(RiskScore, AccessDecision.risk_score_id == RiskScore.id)
        .where(AccessDecision.decided_at >= window_start)
        .order_by(AccessDecision.decided_at.asc())
    )
    rows = decisions_result.all()

    # Initialise all 24 hourly buckets with zero counts, preserving order
    timeline: Dict[str, TimelineBucket] = {}
    for i in range(24):
        hour_mark = (now - timedelta(hours=23 - i)).replace(
            minute=0, second=0, microsecond=0
        )
        hour_str = hour_mark.strftime("%H:00")
        timeline[hour_str] = TimelineBucket(time=hour_str)

    # Accumulate scores per bucket so we can average them after the loop
    score_sums: Dict[str, float] = {k: 0.0 for k in timeline}
    score_counts: Dict[str, int] = {k: 0 for k in timeline}

    for decided_at, decision_type, score in rows:
        hour_str = decided_at.replace(minute=0, second=0, microsecond=0).strftime("%H:00")
        bucket = timeline.get(hour_str)
        if bucket is None:
            continue  # Defensive — should not happen given the window math above

        if decision_type == "ALLOW":
            bucket.ALLOW += 1
        elif decision_type == "MFA_CHALLENGE":
            bucket.MFA_CHALLENGE += 1
        elif decision_type == "BLOCK":
            bucket.BLOCK += 1

        score_sums[hour_str] += float(score)
        score_counts[hour_str] += 1

    # Compute per-bucket average risk score
    for hour_str, bucket in timeline.items():
        if score_counts[hour_str] > 0:
            bucket.avg_risk_score = round(score_sums[hour_str] / score_counts[hour_str], 2)

    return TimelineResponse(timeline=list(timeline.values()))