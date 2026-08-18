"""
SQLAlchemy 2.0 ORM models for the BBAC Simulator.
All models inherit from Base defined in database/connection.py.
Importing this module registers all tables on Base.metadata,
making them visible to init_db() and Alembic migrations.
"""

import uuid
from datetime import datetime
from typing import Optional, Any

from sqlalchemy import (
    String, Float, Boolean, DateTime,
    ForeignKey, Text, Index, CheckConstraint, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import Mapped, mapped_column, relationship

# ← CRITICAL: Import Base from connection.py — do NOT redefine it here.
# All models must share the same Base so init_db() can find them.
from database.connection import Base


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    baseline: Mapped[Optional["UserBaseline"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# Activity Logs  (TimescaleDB Hypertable — composite PK required)
# ---------------------------------------------------------------------------
class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # timestamp is part of PK — required by TimescaleDB for hypertable partitioning
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, server_default=func.now(), nullable=False
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(INET)
    location: Mapped[Optional[str]] = mapped_column(String(255))
    device_fingerprint: Mapped[Optional[str]] = mapped_column(String(255))
    resource_accessed: Mapped[Optional[str]] = mapped_column(String(255))
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    __table_args__ = (
        # Composite index — covers "all logs for user X ordered by time" queries
        Index("ix_activity_logs_user_time", "user_id", "timestamp"),
    )


# ---------------------------------------------------------------------------
# Risk Scores  (TimescaleDB Hypertable — composite PK required)
# FK to activity_logs omitted — hypertable FK limitation; enforced in app layer
# ---------------------------------------------------------------------------
class RiskScore(Base):
    __tablename__ = "risk_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    log_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False  # FK enforced at application layer
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, server_default=func.now(), nullable=False
    )
    features_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)

    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 100", name="chk_score_range"),
        Index("ix_risk_scores_user_time", "user_id", "computed_at"),
    )


# ---------------------------------------------------------------------------
# Access Decisions
# FK to risk_scores omitted — hypertable FK limitation; enforced in app layer
# ---------------------------------------------------------------------------
class AccessDecision(Base):
    __tablename__ = "access_decisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    risk_score_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False  # FK enforced at application layer
    )
    decision: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "decision IN ('ALLOW', 'MFA_CHALLENGE', 'BLOCK')",
            name="chk_decision_values",
        ),
        Index("ix_access_decisions_user_decided", "user_id", "decided_at"),
    )


# ---------------------------------------------------------------------------
# Policies
# ---------------------------------------------------------------------------
class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # unique=True required so ON CONFLICT (name) works in init.sql seed insert
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    low_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    high_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "low_threshold < high_threshold", name="chk_policy_thresholds"
        ),
    )


# ---------------------------------------------------------------------------
# User Baselines
# ---------------------------------------------------------------------------
class UserBaseline(Base):
    __tablename__ = "user_baselines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    avg_login_hour: Mapped[Optional[float]] = mapped_column(Float)
    common_subnet: Mapped[Optional[str]] = mapped_column(String(255))
    common_device: Mapped[Optional[str]] = mapped_column(String(255))
    typical_actions_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="baseline")


# ---------------------------------------------------------------------------
# User Sessions
# ---------------------------------------------------------------------------
class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(50), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE', 'EXPIRED', 'TERMINATED')",
            name="chk_session_status",
        ),
        Index("ix_user_sessions_user_id", "user_id"),
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="sessions")