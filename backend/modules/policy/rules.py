"""
Policy evaluation rules for the BBAC Simulator.
Determines access decisions (ALLOW, MFA_CHALLENGE, BLOCK) by comparing a
computed risk score against the currently active Policy's thresholds.

Fallback behaviour:
If no active Policy exists in the database (e.g. fresh install before
init.sql seed runs, or all policies deactivated), this module falls back
to settings.RISK_LOW_THRESHOLD / RISK_HIGH_THRESHOLD from config.py.
The fallback uses the SAME boundary logic as the DB-driven path
(< low → ALLOW, >= high → BLOCK) so behaviour is consistent either way.
"""

import logging
from typing import Tuple, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import settings
from database.models import Policy
from schemas.risk import DecisionEnum, RiskLevel, score_to_risk_level

logger = logging.getLogger(__name__)


class PolicyEvaluator:
    """
    Evaluates risk scores against the active policy's thresholds to determine
    the appropriate access control decision.
    """

    @staticmethod
    async def get_active_policy(session: AsyncSession) -> Optional[Policy]:
        """
        Returns the currently active Policy, or None if none is active.

        If multiple policies are marked active (an administrative error —
        normally only one should be active at a time), the most recently
        created one is used, and a warning is logged so the inconsistency
        is visible rather than silently arbitrary.

        Args:
            session: Active async DB session.

        Returns:
            The active Policy ORM instance, or None.
        """
        result = await session.execute(
            select(Policy)
            .where(Policy.is_active == True)
            .order_by(Policy.created_at.desc())
        )
        active_policies = list(result.scalars().all())

        if not active_policies:
            return None

        if len(active_policies) > 1:
            logger.warning(
                "%d policies are marked active simultaneously — using most "
                "recently created: '%s'. Only one policy should be active.",
                len(active_policies), active_policies[0].name,
            )

        return active_policies[0]

    @staticmethod
    async def evaluate_score(
        session: AsyncSession, risk_score: float
    ) -> Tuple[DecisionEnum, str, RiskLevel]:
        """
        Evaluates a risk score against the active policy's thresholds.

        Args:
            session: Active async DB session.
            risk_score: Computed risk score in [0.0, 100.0].

        Returns:
            Tuple of (DecisionEnum, reason string, RiskLevel).
        """
        active_policy = await PolicyEvaluator.get_active_policy(session)

        if active_policy is None:
            logger.debug(
                "No active policy found — using settings fallback thresholds "
                "(low=%.1f, high=%.1f).",
                settings.RISK_LOW_THRESHOLD, settings.RISK_HIGH_THRESHOLD,
            )
            return PolicyEvaluator._evaluate_against_thresholds(
                risk_score,
                low=settings.RISK_LOW_THRESHOLD,
                high=settings.RISK_HIGH_THRESHOLD,
                policy_label="default settings (no active policy in database)",
            )

        return PolicyEvaluator._evaluate_against_thresholds(
            risk_score,
            low=active_policy.low_threshold,
            high=active_policy.high_threshold,
            policy_label=f"policy '{active_policy.name}'",
        )

    @staticmethod
    def _evaluate_against_thresholds(
        risk_score: float,
        low: float,
        high: float,
        policy_label: str,
    ) -> Tuple[DecisionEnum, str, RiskLevel]:
        """
        Single shared boundary logic used by both the DB-driven path and the
        settings fallback path, so the two can never silently disagree at
        boundary values.

        Boundary rules:
            risk_score <  low   → ALLOW
            risk_score >= high  → BLOCK
            otherwise           → MFA_CHALLENGE

        Args:
            risk_score: Score being evaluated.
            low: Low threshold — below this is ALLOW.
            high: High threshold — at or above this is BLOCK.
            policy_label: Human-readable source of these thresholds, used in reason text.

        Returns:
            Tuple of (DecisionEnum, reason string, RiskLevel).
        """
        risk_level = score_to_risk_level(risk_score, low, high)

        if risk_score < low:
            decision = DecisionEnum.ALLOW
            reason = (
                f"Risk score {risk_score:.1f} is below the low threshold "
                f"({low:.1f}) of {policy_label}. Access granted."
            )
        elif risk_score >= high:
            decision = DecisionEnum.BLOCK
            reason = (
                f"Risk score {risk_score:.1f} meets or exceeds the high threshold "
                f"({high:.1f}) of {policy_label}. Access blocked."
            )
        else:
            decision = DecisionEnum.MFA_CHALLENGE
            reason = (
                f"Risk score {risk_score:.1f} falls between thresholds "
                f"({low:.1f}–{high:.1f}) of {policy_label}. Step-up authentication required."
            )

        return decision, reason, risk_level