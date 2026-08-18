"""
Synthetic log generator for the BBAC Simulator telemetry module.
Runs as an async background task, producing realistic user activity logs
based on behavioral profiles and injecting anomalies based on configuration.

The generator is a singleton (see module-level `generator` instance).
Wire up the analytics callback in main.py startup to connect the generator
to the ML engine without creating a circular import.
"""

import asyncio
import logging
import random
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Callable, Awaitable

from sqlalchemy import select
from sqlalchemy.sql.expression import func

from config import settings
from database.connection import AsyncSessionLocal
from database.models import User, ActivityLog
from modules.telemetry.profiles import get_profile_for_role, UserProfile
from modules.telemetry.scenarios import (
    ANOMALY_SCENARIOS,
    AnomalyDefinition,
    get_weighted_random_scenario,
)

logger = logging.getLogger(__name__)

# Type alias for the post-log async callback
LogCallback = Callable[[uuid.UUID, uuid.UUID], Awaitable[None]]


class TelemetryGenerator:
    """
    Generates synthetic activity logs for all active users in the database.
    Manages the background simulation loop, scenario injection, and state.

    Usage (wired in main.py):
        generator.set_on_log_created(analytics_engine.process_log)
        generator.start()
    """

    def __init__(self) -> None:
        self.is_running: bool = False
        self._task: Optional[asyncio.Task] = None

        # Persistent scenario: injected at `anomaly_inject_rate` probability each cycle
        self._active_scenario_id: Optional[str] = None
        self._anomaly_inject_rate: float = 0.15  # 15% of logs are anomalies by default

        # One-shot: if set, the NEXT generated log will use this scenario exactly once
        self._trigger_once_scenario_id: Optional[str] = None

        # Per-user active session IDs — maintains session continuity across log entries
        self._user_sessions: Dict[uuid.UUID, uuid.UUID] = {}

        # Async callback fired after each log is saved — wired to the analytics engine
        self._on_log_created: Optional[LogCallback] = None

        # Generation statistics — read by the dashboard stats route
        self.total_logs_generated: int = 0
        self.total_anomalies_injected: int = 0

    # ------------------------------------------------------------------
    # Public control interface — called by the simulation API route
    # ------------------------------------------------------------------

    def set_on_log_created(self, callback: LogCallback) -> None:
        """
        Registers an async callback invoked after every log insert.
        Wire this to analytics_engine.process_log in main.py startup.

        Args:
            callback: Async function accepting (log_id: UUID, user_id: UUID).
        """
        self._on_log_created = callback

    def start(self) -> None:
        """Starts the background log generation loop."""
        if not self.is_running:
            self.is_running = True
            self._task = asyncio.create_task(self._generation_loop())
            logger.info("Telemetry generator started.")

    def stop(self) -> None:
        """Stops the background log generation loop."""
        self.is_running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("Telemetry generator stopped.")

    def set_scenario(
        self,
        scenario_id: Optional[str],
        inject_rate: float = 0.15,
    ) -> bool:
        """
        Sets or clears the persistent anomaly scenario for the generation loop.

        Args:
            scenario_id: Key from ANOMALY_SCENARIOS, or None to disable anomalies.
            inject_rate:  Probability (0.0–1.0) that each generated log is an anomaly.

        Returns:
            True if the scenario was found and set; False if scenario_id was invalid.
        """
        if scenario_id is None:
            self._active_scenario_id = None
            self._anomaly_inject_rate = 0.0
            logger.info("Anomaly injection disabled.")
            return True

        if scenario_id not in ANOMALY_SCENARIOS:
            logger.warning("Unknown scenario ID: %s", scenario_id)
            return False

        self._active_scenario_id = scenario_id
        self._anomaly_inject_rate = max(0.0, min(1.0, inject_rate))
        logger.info(
            "Anomaly scenario set: %s at %.0f%% injection rate",
            scenario_id,
            self._anomaly_inject_rate * 100,
        )
        return True

    def trigger_once(self, scenario_id: str) -> bool:
        """
        Schedules a one-shot anomaly injection on the NEXT generation cycle.
        Does not change the persistent active scenario.

        Args:
            scenario_id: Key from ANOMALY_SCENARIOS.

        Returns:
            True if the scenario was found and queued; False otherwise.
        """
        if scenario_id not in ANOMALY_SCENARIOS:
            logger.warning("trigger_once: Unknown scenario ID: %s", scenario_id)
            return False
        self._trigger_once_scenario_id = scenario_id
        logger.info("One-shot anomaly queued: %s", scenario_id)
        return True

    def get_status(self) -> Dict[str, Any]:
        """
        Returns the current generator state for the simulation API status route.
        """
        return {
            "is_running": self.is_running,
            "active_scenario": self._active_scenario_id,
            "anomaly_inject_rate": self._anomaly_inject_rate,
            "pending_trigger": self._trigger_once_scenario_id,
            "total_logs_generated": self.total_logs_generated,
            "total_anomalies_injected": self.total_anomalies_injected,
            "interval_ms": settings.SIMULATION_INTERVAL_MS,
        }

    # ------------------------------------------------------------------
    # Internal generation loop
    # ------------------------------------------------------------------

    async def _generation_loop(self) -> None:
        """Main async loop — generates one log per interval tick."""
        while self.is_running:
            try:
                await self._generate_single_log()
                await asyncio.sleep(settings.SIMULATION_INTERVAL_MS / 1000.0)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Unexpected error in telemetry generation loop.")
                await asyncio.sleep(5)  # Back off briefly before retrying

    async def _generate_single_log(self) -> None:
        """Picks a random active user and inserts one synthetic ActivityLog."""
        async with AsyncSessionLocal() as session:
            # Fetch one random active user
            result = await session.execute(
                select(User)
                .where(User.is_active == True)
                .order_by(func.random())
                .limit(1)
            )
            user: Optional[User] = result.scalar_one_or_none()

            if not user:
                logger.debug("No active users found — skipping log generation.")
                return

            profile = get_profile_for_role(user.role)

            # Determine whether this log should be anomalous
            anomaly_def: Optional[AnomalyDefinition] = None

            if self._trigger_once_scenario_id:
                # One-shot takes priority over persistent scenario
                anomaly_def = ANOMALY_SCENARIOS.get(self._trigger_once_scenario_id)
                self._trigger_once_scenario_id = None  # Consume immediately
            elif (
                self._active_scenario_id
                and random.random() < self._anomaly_inject_rate
            ):
                anomaly_def = ANOMALY_SCENARIOS.get(self._active_scenario_id)

            log_data = self._build_log_data(user, profile, anomaly_def)

            new_log = ActivityLog(**log_data)
            session.add(new_log)
            await session.commit()
            await session.refresh(new_log)

            # Update statistics
            self.total_logs_generated += 1
            if anomaly_def:
                self.total_anomalies_injected += 1

            logger.debug(
                "Log generated: user=%s action=%s anomaly=%s",
                user.username,
                log_data["action"],
                anomaly_def.anomaly_type.value if anomaly_def else "None",
            )

            # Fire the analytics engine callback (wired from main.py)
            if self._on_log_created:
                try:
                    await self._on_log_created(new_log.id, new_log.user_id)
                except Exception:
                    logger.exception(
                        "Analytics callback failed for log %s", new_log.id
                    )

    # ------------------------------------------------------------------
    # Log data construction
    # ------------------------------------------------------------------

    def _build_log_data(
        self,
        user: User,
        profile: UserProfile,
        anomaly_def: Optional[AnomalyDefinition],
    ) -> Dict[str, Any]:
        """
        Builds the ActivityLog field dict by starting from the user's normal
        profile and applying anomaly overrides where specified.

        Uses the helper methods on UserProfile (random_ip, random_action, etc.)
        that were defined in modules/telemetry/profiles.py.
        """
        now = datetime.now(timezone.utc)

        # --- Normal baseline values from profile helpers ---
        action = profile.random_action()
        location = profile.random_location()
        ip_address = profile.random_ip()
        device = profile.random_device()
        resource = profile.random_resource()

        # --- Apply anomaly overrides ---
        if anomaly_def:
            if anomaly_def.action_override:
                action = anomaly_def.action_override
            if anomaly_def.location_override:
                location = anomaly_def.location_override
            if anomaly_def.ip_override:
                ip_address = anomaly_def.ip_override
            if anomaly_def.device_override:
                device = anomaly_def.device_override
            if anomaly_def.resource_override:
                resource = anomaly_def.resource_override
            if anomaly_def.force_off_hours:
                start_h, end_h = anomaly_def.off_hours_range
                off_hour = random.randint(start_h, end_h)
                off_minute = random.randint(0, 59)
                now = now.replace(hour=off_hour, minute=off_minute, second=0)

        # --- Session continuity ---
        # Each user maintains one active session UUID across log entries.
        # A LOGIN action starts a new session; all other actions reuse it.
        if action == "LOGIN" or user.id not in self._user_sessions:
            self._user_sessions[user.id] = uuid.uuid4()
        session_id = self._user_sessions[user.id]

        return {
            "user_id": user.id,
            "timestamp": now,
            "action": action,
            "ip_address": ip_address,
            "location": location,
            "device_fingerprint": device,
            "resource_accessed": resource,
            "session_id": session_id,
        }


# ---------------------------------------------------------------------------
# Global singleton — imported by main.py and the simulation API route
# ---------------------------------------------------------------------------
generator = TelemetryGenerator()