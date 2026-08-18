"""
API routes for Activity Logs and their associated risk scores and
access decisions. Supports filtering, pagination, and a detailed
single-log view including the raw ML feature vector.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from api.dependencies import require_admin

from database.connection import get_db
from database.models import ActivityLog, RiskScore, AccessDecision, User
from schemas.log import LogWithRiskResponse, PaginatedLogResponse, LogAction

router = APIRouter(prefix="/logs", tags=["Logs"])


@router.get("/", response_model=PaginatedLogResponse)
async def get_logs(
    user_id: Optional[uuid.UUID] = Query(None, description="Filter by user"),
    action: Optional[LogAction] = Query(None, description="Filter by action type"),
    min_score: Optional[float] = Query(None, ge=0, le=100, description="Minimum risk score"),
    max_score: Optional[float] = Query(None, ge=0, le=100, description="Maximum risk score"),
    start_time: Optional[datetime] = Query(None, description="Logs at or after this time"),
    end_time: Optional[datetime] = Query(None, description="Logs at or before this time"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, str] = Depends(require_admin),
):
    """
    Retrieve a filtered, paginated list of activity logs enriched with
    their risk score and access decision, newest first.

    Powers the LogStream.tsx component and its filter controls.
    """
    # ------------------------------------------------------------------
    # Shared filter predicate builder — applied to both the data query
    # and the count query so totals always match the returned page.
    # ------------------------------------------------------------------
    base_query = (
        select(
            ActivityLog,
            RiskScore.score.label("risk_score"),
            RiskScore.id.label("risk_score_id"),
            AccessDecision.decision.label("decision"),
        )
        .outerjoin(RiskScore, ActivityLog.id == RiskScore.log_id)
        .outerjoin(AccessDecision, RiskScore.id == AccessDecision.risk_score_id)
    )

    if user_id:
        base_query = base_query.where(ActivityLog.user_id == user_id)
    if action:
        base_query = base_query.where(ActivityLog.action == action)
    if min_score is not None:
        base_query = base_query.where(RiskScore.score >= min_score)
    if max_score is not None:
        base_query = base_query.where(RiskScore.score <= max_score)
    if start_time:
        base_query = base_query.where(ActivityLog.timestamp >= start_time)
    if end_time:
        base_query = base_query.where(ActivityLog.timestamp <= end_time)

    # Total count for pagination metadata — same filters, no limit/offset
    count_query = select(func.count()).select_from(base_query.subquery())
    total = await db.scalar(count_query) or 0

    # Paginated data query
    data_query = (
        base_query
        .order_by(desc(ActivityLog.timestamp))
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(data_query)
    rows = result.all()

    items: List[LogWithRiskResponse] = []
    for log, risk_score, risk_score_id, decision in rows:
        items.append(
            LogWithRiskResponse(
                id=log.id,
                user_id=log.user_id,
                timestamp=log.timestamp,
                action=log.action,
                ip_address=str(log.ip_address) if log.ip_address else None,
                location=log.location,
                device_fingerprint=log.device_fingerprint,
                resource_accessed=log.resource_accessed,
                session_id=log.session_id,
                risk_score=risk_score,
                risk_score_id=risk_score_id,
                decision=decision,
            )
        )

    return PaginatedLogResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{log_id}/details")
async def get_log_details(log_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: Dict[str, str] = Depends(require_admin)):
    """
    Retrieve full detail for a single log: the raw log fields, the user
    who triggered it, the ML feature vector and risk score, and the final
    enforcement decision. Used by the log detail expansion panel.

    Note: querying ActivityLog by id alone (without a timestamp bound)
    forces a scan across all TimescaleDB hypertable chunks. This is
    acceptable for this academic simulator's data volume; a production
    system would carry a timestamp hint alongside log_id to prune chunks.
    """
    query = (
        select(ActivityLog, RiskScore, AccessDecision, User.username)
        .outerjoin(RiskScore, ActivityLog.id == RiskScore.log_id)
        .outerjoin(AccessDecision, RiskScore.id == AccessDecision.risk_score_id)
        .join(User, ActivityLog.user_id == User.id)
        .where(ActivityLog.id == log_id)
    )
    result = await db.execute(query)
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Log {log_id} not found",
        )

    log, risk_score, decision, username = row

    return {
        "log": {
            "id": str(log.id),
            "timestamp": log.timestamp.isoformat(),
            "action": log.action,
            "ip_address": str(log.ip_address) if log.ip_address else None,
            "location": log.location,
            "device_fingerprint": log.device_fingerprint,
            "resource_accessed": log.resource_accessed,
            "session_id": str(log.session_id) if log.session_id else None,
        },
        "user": {
            "id": str(log.user_id),
            "username": username,
        },
        "analysis": {
            "risk_score_id": str(risk_score.id) if risk_score else None,
            "risk_score": risk_score.score if risk_score else None,
            "features": risk_score.features_json if risk_score else None,
            "computed_at": risk_score.computed_at.isoformat() if risk_score else None,
        },
        "enforcement": {
            "decision": decision.decision if decision else None,
            "reason": decision.reason if decision else None,
            "decided_at": decision.decided_at.isoformat() if decision else None,
        },
    }