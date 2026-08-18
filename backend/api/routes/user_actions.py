"""
API routes for User Actions.
Allows the regular 'user' role to manually trigger activity log entries
and view their own risk scores and recent activity in real time.

Every triggered action flows through the full BBAC pipeline:
  1. ActivityLog saved to DB
  2. analytics_engine.process_log() called immediately
  3. Isolation Forest scores the log
  4. AccessDecision persisted
  5. WebSocket broadcasts the result to the dashboard
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from database.connection import get_db
from database.models import User, ActivityLog, RiskScore, AccessDecision
from schemas.log import LogAction
from schemas.risk import score_to_risk_level
from api.dependencies import require_user
from modules.analytics.engine import analytics_engine

router = APIRouter(prefix="/user", tags=["User Actions"])


# ---------------------------------------------------------------------------
# Request schema
# ---------------------------------------------------------------------------
class UserActionRequest(BaseModel):
    """Schema for a user manually triggering an activity log entry."""
    action: LogAction = Field(
        ...,
        description="The action to simulate — must match a recognised LogAction type",
    )
    resource: Optional[str] = Field(
        None,
        description="The resource being accessed (optional — defaults based on action)",
    )


# Default resources shown in the user panel when the user doesn't specify one
_DEFAULT_RESOURCES: Dict[str, str] = {
    "LOGIN":              "Auth_Server",
    "LOGOUT":             "Auth_Server",
    "FILE_READ":          "Project_Share",
    "FILE_WRITE":         "Project_Share",
    "FILE_DELETE":        "Project_Share",
    "DB_QUERY":           "Analytics_DB",
    "API_CALL":           "Internal_API",
    "EMAIL_SEND":         "Email_Server",
    "REPORT_VIEW":        "Report_Dashboard",
    "SETTINGS_VIEW":      "Settings_Portal",
    "MFA_VERIFY":         "Auth_Server",
    "PASSWORD_CHANGE":    "Auth_Server",
    "DB_EXPORT":          "Customer_DB",
    "BULK_DOWNLOAD":      "File_Storage",
    "CONFIG_CHANGE":      "System_Config",
    "ADMIN_ACTION":       "Admin_Console",
    "PRIVILEGE_ESCALATION": "Firewall_Rules",
    "DATA_EXFIL":         "Customer_Records_API",
    "LATERAL_MOVE":       "Prod_DB_Cluster",
}


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------
async def _get_db_user(username: str, db: AsyncSession) -> User:
    """
    Fetches the real User ORM record for the JWT-authenticated username.
    Raises 404 if the user record doesn't exist in the database yet.
    """
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"User '{username}' not found in the database. "
                "The simulation must run at least once to create user records."
            ),
        )
    return user


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/trigger-action")
async def trigger_action(
    request: UserActionRequest,
    current_user: Dict[str, str] = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Manually creates an ActivityLog entry for the authenticated user
    and immediately invokes the analytics engine to score it.

    This is the core of the User Panel — every button press on the
    frontend calls this endpoint, flows through the full ML pipeline,
    and the result appears live on the admin Dashboard via WebSocket.
    """
    db_user = await _get_db_user(current_user["username"], db)

    new_log = ActivityLog(
        user_id=db_user.id,
        timestamp=datetime.now(timezone.utc),
        action=request.action,
        ip_address="127.0.0.1",
        location="Local Workstation",
        device_fingerprint="User-Panel-Browser",
        resource_accessed=request.resource or _DEFAULT_RESOURCES.get(
            request.action, "General_Resource"
        ),
        session_id=uuid.uuid4(),
    )

    db.add(new_log)
    await db.commit()
    await db.refresh(new_log)

    # Trigger the ML pipeline immediately — without this call the log
    # would sit unscored in the DB until the catch-up polling loop finds it.
    # Calling process_log() directly gives the user instant feedback.
    try:
        await analytics_engine.process_log(new_log.id, new_log.user_id)
    except Exception:
        # Don't block the response if ML scoring fails —
        # the catch-up loop will score it on the next pass.
        pass

    return {
        "log_id": str(new_log.id),
        "action": request.action,
        "timestamp": new_log.timestamp.isoformat(),
        "message": f"Action '{request.action}' logged. Risk score computing...",
    }


@router.get("/my-risk-score")
async def get_my_risk_score(
    current_user: Dict[str, str] = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns the authenticated user's most recent ML risk score and
    the enforcement decision that was made from it.
    Returns null fields if the user hasn't been scored yet.
    """
    db_user = await _get_db_user(current_user["username"], db)

    result = await db.execute(
        select(RiskScore, AccessDecision)
        .outerjoin(AccessDecision, RiskScore.id == AccessDecision.risk_score_id)
        .where(RiskScore.user_id == db_user.id)
        .order_by(desc(RiskScore.computed_at))
        .limit(1)
    )
    row = result.first()

    if not row:
        return {
            "score": None,
            "risk_level": None,
            "decision": None,
            "computed_at": None,
        }

    risk_score, decision = row

    # Use the shared score_to_risk_level helper — same thresholds as everywhere else
    risk_level = score_to_risk_level(
        risk_score.score,
        low_threshold=30.0,
        high_threshold=70.0,
    )

    return {
        "score": round(risk_score.score, 2),
        "risk_level": risk_level.value,
        "decision": decision.decision if decision else "PENDING",
        "computed_at": risk_score.computed_at.isoformat(),
    }


@router.get("/my-recent-activity")
async def get_my_recent_activity(
    current_user: Dict[str, str] = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Returns the authenticated user's 10 most recent activity log entries,
    each enriched with the computed risk score and access decision.
    Powers the recent activity feed in the User Panel.
    """
    db_user = await _get_db_user(current_user["username"], db)

    result = await db.execute(
        select(
            ActivityLog,
            RiskScore.score.label("risk_score"),
            AccessDecision.decision,
        )
        .outerjoin(RiskScore, ActivityLog.id == RiskScore.log_id)
        .outerjoin(AccessDecision, RiskScore.id == AccessDecision.risk_score_id)
        .where(ActivityLog.user_id == db_user.id)
        .order_by(desc(ActivityLog.timestamp))
        .limit(10)
    )
    rows = result.all()

    return [
        {
            "id":               str(log.id),
            "timestamp":        log.timestamp.isoformat(),
            "action":           log.action,
            "resource_accessed": log.resource_accessed,
            "risk_score":       round(float(score), 2) if score is not None else None,
            "decision":         decision if decision else "PENDING",
        }
        for log, score, decision in rows
    ]