"""
Baseline computation logic for the BBAC Simulator analytics module.
Analyses historical user activity to establish a behavioral baseline,
which the feature extractor then uses for anomaly detection.

Baseline fields computed:
  - avg_login_hour:        Circular mean of login hours (handles midnight wrap-around)
  - common_subnet:         Most frequently used /24 subnet prefix
  - common_device:         Most frequently used device fingerprint
  - typical_actions_json:  Normalised frequency map of action types (0.0–1.0)
"""

import ipaddress
import logging
import math
import uuid
from collections import Counter
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from config import settings
from database.models import ActivityLog, UserBaseline

logger = logging.getLogger(__name__)

# How old a baseline can be before the engine should recalculate it
_BASELINE_STALE_AFTER_MINUTES: int = 30


class BaselineCalculator:
    """
    Computes and updates behavioural baselines for users based on their
    historical activity logs.

    All public methods are static — this class is a namespace for baseline
    operations, not a stateful service. Import and call methods directly.
    """

    # ------------------------------------------------------------------
    # Public read helpers — called by the analytics engine
    # ------------------------------------------------------------------

    @staticmethod
    async def get_baseline(
        session: AsyncSession, user_id: uuid.UUID
    ) -> Optional[UserBaseline]:
        """
        Fetches the existing UserBaseline for a user without recalculating.
        Returns None if no baseline has been computed yet.

        Args:
            session: Active async DB session.
            user_id: UUID of the user.

        Returns:
            UserBaseline ORM instance, or None.
        """
        result = await session.execute(
            select(UserBaseline).where(UserBaseline.user_id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def has_sufficient_data(
        session: AsyncSession, user_id: uuid.UUID
    ) -> bool:
        """
        Returns True if the user has at least ML_MIN_LOGS_FOR_BASELINE logs.
        The analytics engine calls this before attempting to score a log —
        if insufficient data exists, the engine skips ML scoring for this user.

        Args:
            session: Active async DB session.
            user_id: UUID of the user.

        Returns:
            True if log count >= settings.ML_MIN_LOGS_FOR_BASELINE.
        """
        result = await session.execute(
            select(func.count(ActivityLog.id)).where(
                ActivityLog.user_id == user_id
            )
        )
        count = result.scalar_one()
        return count >= settings.ML_MIN_LOGS_FOR_BASELINE

    @staticmethod
    def should_refresh_baseline(baseline: Optional[UserBaseline]) -> bool:
        """
        Returns True if the baseline is missing or has grown stale.
        Prevents recalculating on every log insert (which would be very slow)
        while ensuring the baseline stays reasonably up to date.

        Args:
            baseline: Existing UserBaseline, or None if none exists yet.

        Returns:
            True if the engine should call update_user_baseline().
        """
        if baseline is None:
            return True
        age = datetime.now(timezone.utc) - baseline.updated_at.replace(
            tzinfo=timezone.utc
        )
        return age > timedelta(minutes=_BASELINE_STALE_AFTER_MINUTES)

    # ------------------------------------------------------------------
    # Public write method — called by the analytics engine
    # ------------------------------------------------------------------

    @staticmethod
    async def update_user_baseline(
        session: AsyncSession, user_id: uuid.UUID
    ) -> Optional[UserBaseline]:
        """
        Computes behavioural metrics for a user and upserts their UserBaseline.

        Returns None if the user has fewer than ML_MIN_LOGS_FOR_BASELINE logs —
        in that case no baseline is written and the engine should skip scoring.

        Args:
            session: Active async DB session.
            user_id: UUID of the user.

        Returns:
            Updated or created UserBaseline, or None if insufficient data.
        """
        # Fetch up to 1000 most recent logs for this user
        result = await session.execute(
            select(ActivityLog)
            .where(ActivityLog.user_id == user_id)
            .order_by(ActivityLog.timestamp.desc())
            .limit(1000)
        )
        logs: List[ActivityLog] = list(result.scalars().all())

        # Gate on minimum log count from settings — do not baseline on sparse data
        if len(logs) < settings.ML_MIN_LOGS_FOR_BASELINE:
            logger.debug(
                "User %s has only %d logs — below minimum %d for baseline.",
                user_id, len(logs), settings.ML_MIN_LOGS_FOR_BASELINE,
            )
            return None

        avg_hour      = BaselineCalculator._compute_circular_mean_hour(logs)
        common_subnet = BaselineCalculator._compute_common_subnet(logs)
        common_device = BaselineCalculator._compute_common_device(logs)
        typical_actions = BaselineCalculator._compute_action_frequencies(logs)

        # Upsert baseline
        baseline_result = await session.execute(
            select(UserBaseline).where(UserBaseline.user_id == user_id)
        )
        baseline = baseline_result.scalar_one_or_none()

        if baseline:
            baseline.avg_login_hour      = avg_hour
            baseline.common_subnet       = common_subnet
            baseline.common_device       = common_device
            baseline.typical_actions_json = typical_actions
            logger.debug("Baseline updated for user %s.", user_id)
        else:
            baseline = UserBaseline(
                user_id=user_id,
                avg_login_hour=avg_hour,
                common_subnet=common_subnet,
                common_device=common_device,
                typical_actions_json=typical_actions,
            )
            session.add(baseline)
            logger.info("Baseline created for user %s.", user_id)

        await session.commit()
        await session.refresh(baseline)
        return baseline

    # ------------------------------------------------------------------
    # Private computation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_circular_mean_hour(logs: List[ActivityLog]) -> float:
        """
        Computes the circular mean of login hours using sin/cos averaging.

        Arithmetic mean fails for time-of-day because it is a circular variable:
        the mean of 23:00 and 01:00 should be 00:00, not 12:00.
        Circular mean correctly handles this wrap-around.

        Returns:
            Mean hour as a float in [0.0, 24.0).
        """
        if not logs:
            return 0.0

        sin_sum = 0.0
        cos_sum = 0.0
        for log in logs:
            hour = log.timestamp.hour + (log.timestamp.minute / 60.0)
            angle = 2.0 * math.pi * hour / 24.0
            sin_sum += math.sin(angle)
            cos_sum += math.cos(angle)

        mean_angle = math.atan2(sin_sum / len(logs), cos_sum / len(logs))
        mean_hour = (mean_angle * 24.0 / (2.0 * math.pi)) % 24.0
        return round(mean_hour, 4)

    @staticmethod
    def _compute_common_subnet(logs: List[ActivityLog]) -> Optional[str]:
        """
        Returns the most frequently used /24 subnet prefix across all logs.
        Uses the ipaddress module to handle both IPv4 and IPv6 safely, and
        casts ip_address to str first to handle asyncpg IPv4Address objects.
        """
        subnets: List[str] = []
        for log in logs:
            if not log.ip_address:
                continue
            try:
                addr = ipaddress.ip_address(str(log.ip_address))
                if isinstance(addr, ipaddress.IPv4Address):
                    subnets.append(".".join(str(addr).split(".")[:3]))
                else:
                    # IPv6 — use first 4 groups as subnet approximation
                    subnets.append(":".join(str(addr).split(":")[:4]))
            except ValueError:
                logger.warning("Skipping unparseable IP in baseline: %s", log.ip_address)
                continue

        if not subnets:
            return None
        return Counter(subnets).most_common(1)[0][0]

    @staticmethod
    def _compute_common_device(logs: List[ActivityLog]) -> Optional[str]:
        """Returns the most frequently used device fingerprint string."""
        devices = [log.device_fingerprint for log in logs if log.device_fingerprint]
        if not devices:
            return None
        return Counter(devices).most_common(1)[0][0]

    @staticmethod
    def _compute_action_frequencies(logs: List[ActivityLog]) -> Dict[str, float]:
        """
        Returns a normalised frequency map of action types.
        Values are proportions in [0.0, 1.0] — e.g. {'LOGIN': 0.10, 'FILE_READ': 0.35}.
        Stored in UserBaseline.typical_actions_json and read by the feature extractor.
        """
        actions = [log.action for log in logs if log.action]
        if not actions:
            return {}
        total = len(actions)
        return {
            action: round(count / total, 6)
            for action, count in Counter(actions).items()
        }