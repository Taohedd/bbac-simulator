"""
Main orchestration engine for the BBAC Simulator analytics module.
Coordinates feature extraction, baseline management, ML risk scoring,
policy enforcement, and real-time WebSocket broadcasting.

Processing pipeline for each ActivityLog:
    1. Fetch log from DB
    2. Check / refresh user baseline
    3. Extract feature vector
    4. Train or retrain global Isolation Forest if needed
    5. Compute 0–100 risk score
    6. Persist RiskScore to DB
    7. Trigger policy enforcement → AccessDecision
    8. Broadcast result over WebSocket

Entry points:
    - process_log(log_id, user_id)  ← called by telemetry generator callback
    - _processing_loop()            ← background catch-up for missed logs
    - initialize()                  ← called at startup to train on existing data
"""

import asyncio
import logging
import uuid
from typing import Optional, Callable, Awaitable

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.connection import AsyncSessionLocal
from database.models import ActivityLog, RiskScore
from modules.analytics.baseline import BaselineCalculator
from modules.analytics.feature_extractor import FeatureExtractor
from modules.analytics.risk_scorer import risk_scorer   # global singleton
from modules.policy.enforcement import PolicyEnforcer

logger = logging.getLogger(__name__)

BroadcastCallback = Callable[[dict], Awaitable[None]]


class AnalyticsEngine:
    """
    Orchestrates the full BBAC analytics pipeline from raw log to access decision.

    Wire callbacks in main.py startup:
        analytics_engine.set_broadcast_callback(websocket_manager.broadcast)
    Then register the engine with the generator:
        generator.set_on_log_created(analytics_engine.process_log)
    """

    def __init__(self) -> None:
        self.is_running: bool = False
        self._task: Optional[asyncio.Task] = None
        self._broadcast: Optional[BroadcastCallback] = None
        self.enforcer = PolicyEnforcer()

        self.total_logs_processed: int = 0
        self.total_alerts_raised: int = 0

    # ------------------------------------------------------------------
    # Wiring — called from main.py startup
    # ------------------------------------------------------------------

    def set_broadcast_callback(self, callback: BroadcastCallback) -> None:
        """
        Registers the async WebSocket broadcast callback.
        Wired in main.py to websocket_manager.broadcast so that every
        risk score and enforcement decision is pushed to the dashboard.
        """
        self._broadcast = callback
        logger.info("WebSocket broadcast callback registered.")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """
        Trains the global Isolation Forest on all existing log data at startup.
        Called once in main.py's lifespan startup event, after init_db().
        """
        logger.info("Initialising analytics engine — training on existing data...")
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ActivityLog)
                .order_by(ActivityLog.timestamp.desc())
                .limit(2000)
            )
            logs = list(result.scalars().all())

        if len(logs) < settings.ML_MIN_LOGS_FOR_BASELINE:
            logger.info(
                "Only %d existing logs found — model will train once %d logs accumulate.",
                len(logs), settings.ML_MIN_LOGS_FOR_BASELINE,
            )
            return

        feature_list = [
            FeatureExtractor.extract_features(log, baseline=None)
            for log in logs
        ]
        df = FeatureExtractor.to_dataframe(feature_list)
        trained = risk_scorer.train(df)

        if trained:
            logger.info("Global Isolation Forest trained on %d historical logs.", len(logs))

    def start(self) -> None:
        """Starts the background catch-up polling loop."""
        if not self.is_running:
            self.is_running = True
            self._task = asyncio.create_task(self._processing_loop())
            logger.info("Analytics Engine background loop started.")

    def stop(self) -> None:
        """Stops the background polling loop."""
        self.is_running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("Analytics Engine stopped.")

    def get_status(self) -> dict:
        """Returns engine state for the simulation status API route."""
        return {
            "is_running": self.is_running,
            "total_logs_processed": self.total_logs_processed,
            "total_alerts_raised": self.total_alerts_raised,
            "model_status": risk_scorer.get_status(),
        }

    # ------------------------------------------------------------------
    # Primary entry point — wired as the generator's on_log_created callback
    # ------------------------------------------------------------------

    async def process_log(
        self,
        log_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """
        Full analytics pipeline for one ActivityLog.
        Signature matches LogCallback: Callable[[UUID, UUID], Awaitable[None]].
        """
        async with AsyncSessionLocal() as session:
            try:
                await self._run_pipeline(session, log_id, user_id)
            except Exception:
                logger.exception(
                    "Pipeline error for log %s (user %s).", log_id, user_id
                )

    async def _run_pipeline(
        self,
        session: AsyncSession,
        log_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """
        Internal pipeline — runs inside an existing session so it can be called
        from both the callback path and the catch-up polling loop.
        """
        result = await session.execute(
            select(ActivityLog).where(
                ActivityLog.id == log_id,
                ActivityLog.user_id == user_id,
            )
        )
        log: Optional[ActivityLog] = result.scalar_one_or_none()

        if not log:
            logger.warning("Log %s not found for user %s.", log_id, user_id)
            return

        baseline = await BaselineCalculator.get_baseline(session, user_id)

        if BaselineCalculator.should_refresh_baseline(baseline):
            has_enough = await BaselineCalculator.has_sufficient_data(
                session, user_id
            )
            if has_enough:
                baseline = await BaselineCalculator.update_user_baseline(
                    session, user_id
                )
            else:
                logger.debug(
                    "User %s has insufficient data for baseline — using heuristic.",
                    user_id,
                )

        features = FeatureExtractor.extract_features(log, baseline)

        if (
            not risk_scorer.is_trained
            or self.total_logs_processed % 100 == 0
        ):
            await self._retrain_global_model(session)

        score_value = risk_scorer.compute_score(features)

        risk_score_row = RiskScore(
            user_id=log.user_id,
            log_id=log.id,
            score=score_value,
            features_json=features,
        )
        session.add(risk_score_row)
        await session.commit()
        await session.refresh(risk_score_row)

        self.total_logs_processed += 1

        decision = await self.enforcer.evaluate_and_enforce(
            session, risk_score_row
        )

        if decision and decision.decision in ("MFA_CHALLENGE", "BLOCK"):
            self.total_alerts_raised += 1

        if self._broadcast and decision:
            payload = {
                "type": "risk_event",
                "log_id": str(log.id),
                "user_id": str(log.user_id),
                "action": log.action,
                "timestamp": log.timestamp.isoformat(),
                "risk_score": score_value,
                "decision": decision.decision,
                "reason": decision.reason,
                "features": features,
            }
            try:
                await self._broadcast(payload)
            except Exception:
                logger.exception("WebSocket broadcast failed for log %s.", log_id)

    # ------------------------------------------------------------------
    # Background catch-up loop
    # ------------------------------------------------------------------

    async def _processing_loop(self) -> None:
        """
        Polls for ActivityLogs that have no RiskScore — processes them in batches.
        """
        while self.is_running:
            try:
                async with AsyncSessionLocal() as session:
                    result = await session.execute(
                        select(ActivityLog.id, ActivityLog.user_id)
                        .outerjoin(RiskScore, ActivityLog.id == RiskScore.log_id)
                        .where(RiskScore.id.is_(None))
                        .order_by(ActivityLog.timestamp.asc())
                        .limit(10)
                    )
                    unprocessed = result.all()

                if unprocessed:
                    for log_id, user_id in unprocessed:
                        await self.process_log(log_id, user_id)
                else:
                    await asyncio.sleep(1.0)

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in analytics catch-up loop.")
                await asyncio.sleep(5.0)

    # ------------------------------------------------------------------
    # Model training helper
    # ------------------------------------------------------------------

    async def _retrain_global_model(self, session: AsyncSession) -> None:
        """
        Fetches recent logs, extracts features, and retrains the global
        Isolation Forest. Called every 100 processed logs.
        """
        result = await session.execute(
            select(ActivityLog)
            .order_by(ActivityLog.timestamp.desc())
            .limit(2000)
        )
        logs = list(result.scalars().all())

        if len(logs) < settings.ML_MIN_LOGS_FOR_BASELINE:
            return

        feature_list = [
            FeatureExtractor.extract_features(log, baseline=None)
            for log in logs
        ]
        df: pd.DataFrame = FeatureExtractor.to_dataframe(feature_list)
        risk_scorer.train(df)


# ---------------------------------------------------------------------------
# Global singleton — imported by main.py and the simulation API route
# ---------------------------------------------------------------------------
analytics_engine = AnalyticsEngine()