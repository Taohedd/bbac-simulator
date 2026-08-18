"""
Policy enforcement logic for the BBAC Simulator.
Takes an evaluated risk score, determines the access decision via
PolicyEvaluator, and persists the result as an AccessDecision row.

Architecture note — broadcasting responsibility:
This module does NOT broadcast over WebSocket. That responsibility belongs
exclusively to modules/analytics/engine.py, which already constructs a
single unified "risk_event" payload (log + score + decision) and sends it
through the callback registered via engine.set_broadcast_callback() in
main.py. Broadcasting here as well would send two different payload shapes
for the same event and force the frontend to handle both.

Layering note:
modules/policy must never import from api/ — that would invert the
dependency direction (api/ depends on modules/, not the reverse) and risks
circular imports once api/websocket.py and api/routes/ are wired up.
"""

import logging
import uuid
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import RiskScore, AccessDecision
from modules.policy.rules import PolicyEvaluator

logger = logging.getLogger(__name__)


class PolicyEnforcer:
    """
    Executes policy decisions and persists them as AccessDecision records.
    Does not handle broadcasting — see module docstring.
    """

    async def evaluate_and_enforce(
        self,
        session: AsyncSession,
        risk_score: RiskScore,
    ) -> AccessDecision:
        """
        Evaluates a RiskScore against the active policy and persists the
        resulting AccessDecision.

        Args:
            session: Active async DB session (same one used to save risk_score
                     by the caller — engine.py manages the transaction).
            risk_score: The RiskScore ORM instance to evaluate. Must already
                        be committed/flushed so risk_score.id is populated.

        Returns:
            The newly created and refreshed AccessDecision instance.
        """
        decision_enum, reason, risk_level = await PolicyEvaluator.evaluate_score(
            session, risk_score.score
        )

        decision = AccessDecision(
            user_id=risk_score.user_id,
            risk_score_id=risk_score.id,
            decision=decision_enum.value,
            reason=reason,
        )
        session.add(decision)
        await session.commit()
        await session.refresh(decision)

        logger.info(
            "Decision %s for user %s (score=%.1f, level=%s).",
            decision.decision, decision.user_id, risk_score.score, risk_level.value,
        )

        return decision

    async def get_recent_decisions(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 20,
    ) -> List[AccessDecision]:
        """
        Returns the most recent AccessDecision records for a user, newest first.
        Used by the UserDetailModal on the frontend to show decision history
        for a specific user's behavioral profile deep-dive.

        Args:
            session: Active async DB session.
            user_id: UUID of the user.
            limit: Maximum number of records to return (default 20).

        Returns:
            List of AccessDecision ORM instances, most recent first.
        """
        result = await session.execute(
            select(AccessDecision)
            .where(AccessDecision.user_id == user_id)
            .order_by(AccessDecision.decided_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())