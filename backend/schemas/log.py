"""
Pydantic v2 schemas for ActivityLog entities.
Used for request validation, response serialization, and query filtering
in the /api/logs routes and the WebSocket real-time stream.
"""

import uuid
import ipaddress
from datetime import datetime
from typing import Optional, Literal
from schemas.risk import DecisionEnum
from pydantic import BaseModel, ConfigDict, Field, field_validator
from schemas.risk import DecisionEnum

# ---------------------------------------------------------------------------
# Action type definition
# Must stay in sync with telemetry/scenarios.py action constants.
# Normal operations and anomalous operations are both included here so the
# schema validates logs from both the baseline and attack simulation paths.
# ---------------------------------------------------------------------------
LogAction = Literal[
    # --- Normal operations ---
    "LOGIN",
    "LOGOUT",
    "FILE_READ",
    "FILE_WRITE",
    "FILE_DELETE",
    "DB_QUERY",
    "API_CALL",
    "EMAIL_SEND",
    "REPORT_VIEW",
    "SETTINGS_VIEW",
    "MFA_VERIFY",
    "PASSWORD_CHANGE",
    # --- Anomalous / attack-simulation operations ---
    "DB_EXPORT",
    "BULK_DOWNLOAD",
    "CONFIG_CHANGE",
    "ADMIN_ACTION",
    "PRIVILEGE_ESCALATION",
    "DATA_EXFIL",
    "LATERAL_MOVE",
]


# ---------------------------------------------------------------------------
# Log Base
# ---------------------------------------------------------------------------
class LogBase(BaseModel):
    """Shared attributes for all activity log schemas."""

    action: LogAction = Field(
        ..., description="The action performed — must be a recognised log action type"
    )
    ip_address: Optional[str] = Field(
        None, description="Valid IPv4 or IPv6 address from which the action originated"
    )
    location: Optional[str] = Field(
        None, max_length=255,
        description="Geographic location derived from the IP address"
    )
    device_fingerprint: Optional[str] = Field(
        None, max_length=255,
        description="Unique string identifying the device used"
    )
    resource_accessed: Optional[str] = Field(
        None, max_length=255,
        description="The specific resource, file, or endpoint accessed"
    )
    session_id: Optional[uuid.UUID] = Field(
        None, description="ID of the current user session"
    )

    @field_validator("ip_address", mode="before")
    @classmethod
    def validate_ip_address(cls, v: Optional[str]) -> Optional[str]:
        """
        Validates that ip_address is a properly formatted IPv4 or IPv6 address.
        Rejects the value early so asyncpg never receives a malformed INET string.
        """
        if v is None:
            return v
        try:
            ipaddress.ip_address(str(v))
            return str(v)
        except ValueError:
            raise ValueError(
                f"'{v}' is not a valid IPv4 or IPv6 address"
            )


# ---------------------------------------------------------------------------
# Log Create — used by the telemetry generator to insert new logs
# ---------------------------------------------------------------------------
class LogCreate(LogBase):
    """Schema for creating a new activity log entry."""
    user_id: uuid.UUID = Field(..., description="ID of the user performing the action")
    timestamp: Optional[datetime] = Field(
        default=None,
        description="Event time — defaults to server NOW() if not provided",
    )


# ---------------------------------------------------------------------------
# Log Response — single log entry returned from the API
# ---------------------------------------------------------------------------
class LogResponse(LogBase):
    """Schema for a single activity log returned in API responses."""
    id: uuid.UUID
    user_id: uuid.UUID
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Log With Risk Response
# Used by the WebSocket stream and the log list view to show the log
# entry together with its computed risk score and access decision.
# ---------------------------------------------------------------------------
class LogWithRiskResponse(LogResponse):
    """
    Extended log response that includes ML risk scoring output.
    Returned by the WebSocket real-time stream and the enriched log API.
    """
    risk_score: Optional[float] = Field(
        None, description="Computed anomaly risk score (0–100)"
    )
    decision: Optional[DecisionEnum] = Field(
        None, description="Access decision made by the policy enforcement engine"
    )
    risk_score_id: Optional[uuid.UUID] = Field(
        None, description="ID of the associated RiskScore record"
    )

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Log Filter — query parameters for GET /api/logs
# ---------------------------------------------------------------------------
class LogFilter(BaseModel):
    """
    Optional filters for the paginated log listing endpoint.
    Passed as query parameters: GET /api/logs?user_id=...&action=LOGIN&limit=50
    """
    user_id: Optional[uuid.UUID] = Field(
        None, description="Filter logs for a specific user"
    )
    action: Optional[LogAction] = Field(
        None, description="Filter by a specific action type"
    )
    min_score: Optional[float] = Field(
        None, ge=0, le=100,
        description="Only return logs with a risk score at or above this value"
    )
    max_score: Optional[float] = Field(
        None, ge=0, le=100,
        description="Only return logs with a risk score at or below this value"
    )
    start_time: Optional[datetime] = Field(
        None, description="Only return logs at or after this timestamp"
    )
    end_time: Optional[datetime] = Field(
        None, description="Only return logs at or before this timestamp"
    )
    limit: int = Field(50, ge=1, le=500,
                       description="Number of results per page (max 500)")
    offset: int = Field(0, ge=0,
                        description="Number of results to skip for pagination")


# ---------------------------------------------------------------------------
# Paginated Log Response — wraps a page of logs with metadata
# ---------------------------------------------------------------------------
class PaginatedLogResponse(BaseModel):
    """
    Paginated wrapper returned by GET /api/logs.
    The frontend uses total + limit + offset to build pagination controls.
    """
    items: list[LogResponse]
    total: int = Field(..., description="Total number of logs matching the filter")
    limit: int = Field(..., description="Page size used for this response")
    offset: int = Field(..., description="Offset used for this response")