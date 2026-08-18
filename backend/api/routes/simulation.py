"""
API routes for controlling the BBAC Simulator.
Starts/stops the telemetry generator and the analytics engine together,
injects or clears anomaly scenarios, supports one-shot anomaly triggers,
and resets the ML model for a fresh simulation run.
"""

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from api.dependencies import require_admin

from modules.telemetry.generator import generator
from modules.telemetry.scenarios import ANOMALY_SCENARIOS, get_all_scenario_ids
from modules.analytics.engine import analytics_engine
from modules.analytics.risk_scorer import risk_scorer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/simulation", tags=["Simulation"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------
class ScenarioConfig(BaseModel):
    """Schema for setting a persistent anomaly scenario."""
    scenario_id: str = Field(..., description="Key from ANOMALY_SCENARIOS")
    inject_rate: float = Field(
        0.15, ge=0.0, le=1.0,
        description="Probability (0-1) that each generated log is this anomaly",
    )


class TriggerOnceRequest(BaseModel):
    """Schema for triggering a single one-shot anomaly."""
    scenario_id: str = Field(..., description="Key from ANOMALY_SCENARIOS")


class SimulationStatusResponse(BaseModel):
    """Combined status of the generator and the analytics engine."""
    generator: dict
    analytics: dict


class SimulationActionResponse(BaseModel):
    """Generic acknowledgement response for control actions."""
    status: str
    detail: Optional[str] = None


class ScenarioInfo(BaseModel):
    """Metadata describing one available anomaly scenario."""
    id: str
    name: str
    description: str
    type: str


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------
@router.get("/status", response_model=SimulationStatusResponse)
async def get_simulation_status(current_user: Dict[str, str] = Depends(require_admin)):
    """
    Retrieve the combined status of the telemetry generator and the
    analytics engine. Both must be running for the full pipeline
    (log → score → decision → broadcast) to function.
    """
    return SimulationStatusResponse(
        generator=generator.get_status(),
        analytics=analytics_engine.get_status(),
    )


# ---------------------------------------------------------------------------
# Start / Stop — controls BOTH the generator and the analytics engine
# ---------------------------------------------------------------------------
@router.post("/start", response_model=SimulationActionResponse)
async def start_simulation(current_user: Dict[str, str] = Depends(require_admin)):
    """
    Starts the telemetry generator and the analytics engine together.
    Starting only one half of the pipeline would either produce logs
    that are never scored, or run an engine with nothing to process.
    """
    if generator.is_running and analytics_engine.is_running:
        return SimulationActionResponse(status="already_running")

    generator.start()
    analytics_engine.start()
    logger.info("Simulation started: generator + analytics engine.")
    return SimulationActionResponse(status="started")


@router.post("/stop", response_model=SimulationActionResponse)
async def stop_simulation(current_user: Dict[str, str] = Depends(require_admin)):
    """Stops the telemetry generator and the analytics engine together."""
    if not generator.is_running and not analytics_engine.is_running:
        return SimulationActionResponse(status="already_stopped")

    generator.stop()
    analytics_engine.stop()
    logger.info("Simulation stopped: generator + analytics engine.")
    return SimulationActionResponse(status="stopped")


@router.post("/reset", response_model=SimulationActionResponse)
async def reset_simulation(current_user: Dict[str, str] = Depends(require_admin)):
    """
    Resets the ML model to an untrained state. Intended to be called after
    /stop and before the next /start, so a fresh simulation run does not
    silently reuse training data or score normalisation from a previous run.
    Does not delete historical logs or decisions from the database.
    """
    if generator.is_running or analytics_engine.is_running:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stop the simulation before resetting the model.",
        )

    risk_scorer.reset()
    logger.info("Risk scorer model reset.")
    return SimulationActionResponse(
        status="reset", detail="Risk scoring model cleared."
    )


# ---------------------------------------------------------------------------
# Scenario discovery
# ---------------------------------------------------------------------------
@router.get("/scenarios", response_model=List[ScenarioInfo])
async def list_scenarios(current_user: Dict[str, str] = Depends(require_admin)):
    """
    Lists all available anomaly scenarios — powers the ScenarioCard.tsx
    selector in the frontend simulation controls panel.
    """
    return [
        ScenarioInfo(
            id=key,
            name=definition.name,
            description=definition.description,
            type=definition.anomaly_type.value,
        )
        for key, definition in ANOMALY_SCENARIOS.items()
    ]


# ---------------------------------------------------------------------------
# Persistent scenario control
# ---------------------------------------------------------------------------
@router.post("/scenario/set", response_model=SimulationActionResponse)
async def set_scenario(config: ScenarioConfig, current_user: Dict[str, str] = Depends(require_admin)):
    """
    Sets a persistent anomaly scenario — the generator will randomly inject
    this scenario at the given inject_rate on every generation cycle until
    cleared. Trusts generator.set_scenario()'s own return value rather than
    re-validating scenario_id separately, so the two checks can never drift.
    """
    success = generator.set_scenario(config.scenario_id, config.inject_rate)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Scenario '{config.scenario_id}' not found. "
                f"Available scenarios: {get_all_scenario_ids()}"
            ),
        )

    return SimulationActionResponse(
        status="scenario_set",
        detail=f"'{config.scenario_id}' active at {config.inject_rate:.0%} injection rate.",
    )


@router.post("/scenario/clear", response_model=SimulationActionResponse)
async def clear_scenario(current_user: Dict[str, str] = Depends(require_admin)):
    """Clears the persistent anomaly scenario, returning to normal-only generation."""
    generator.set_scenario(None)
    return SimulationActionResponse(status="scenario_cleared")


# ---------------------------------------------------------------------------
# One-shot manual trigger
# ---------------------------------------------------------------------------
@router.post("/scenario/trigger-once", response_model=SimulationActionResponse)
async def trigger_scenario_once(request: TriggerOnceRequest, current_user: Dict[str, str] = Depends(require_admin)):
    """
    Queues exactly ONE anomaly injection on the next generation cycle,
    without changing the persistent active scenario. Powers a "trigger now"
    button distinct from the always-on scenario toggle.
    """
    success = generator.trigger_once(request.scenario_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Scenario '{request.scenario_id}' not found. "
                f"Available scenarios: {get_all_scenario_ids()}"
            ),
        )

    return SimulationActionResponse(
        status="triggered",
        detail=f"'{request.scenario_id}' will be injected on the next log cycle.",
    )