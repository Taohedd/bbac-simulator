"""
Anomaly scenario definitions for the BBAC Simulator telemetry module.
Defines how the synthetic log generator mutates normal baseline activity
to simulate realistic security threats and attack patterns.

IMPORTANT: All action_override values MUST exactly match the LogAction
Literal defined in schemas/log.py. Mismatches cause Pydantic validation
errors at log insertion time.

Scenarios are used in two ways:
  1. Automatic injection — the generator randomly selects scenarios based
     on their `anomaly_probability` weight during background simulation.
  2. Manual trigger — the simulation API route allows administrators to
     force-inject a specific scenario via POST /api/simulation/trigger-anomaly.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, List


# ---------------------------------------------------------------------------
# Anomaly Type Enum
# ---------------------------------------------------------------------------
class AnomalyType(str, Enum):
    """
    Classification labels for anomaly types.
    Used by the dashboard AlertsFeed to group and colour-code alerts.
    """
    IMPOSSIBLE_TRAVEL     = "IMPOSSIBLE_TRAVEL"
    OFF_HOURS_ACCESS      = "OFF_HOURS_ACCESS"
    UNRECOGNIZED_DEVICE   = "UNRECOGNIZED_DEVICE"
    DATA_EXFILTRATION     = "DATA_EXFILTRATION"
    PRIVILEGE_ESCALATION  = "PRIVILEGE_ESCALATION"
    COMPROMISED_CREDENTIAL = "COMPROMISED_CREDENTIAL"
    BRUTE_FORCE           = "BRUTE_FORCE"
    LATERAL_MOVEMENT      = "LATERAL_MOVEMENT"


# ---------------------------------------------------------------------------
# AnomalyDefinition Dataclass
# ---------------------------------------------------------------------------
@dataclass
class AnomalyDefinition:
    """
    Defines how a normal baseline log entry should be mutated to represent
    a specific security anomaly.

    Fields set to None are left unchanged from the user's normal profile.
    The generator applies overrides on top of a normally-generated log.

    Attributes:
        name:               Human-readable display name for the dashboard.
        anomaly_type:       Classification label for grouping alerts.
        description:        Explanation shown in the AlertsFeed tooltip.
        action_override:    Replaces the action — MUST match LogAction exactly.
        location_override:  Replaces the geographic location string.
        ip_override:        Replaces the IP address — must be a valid IPv4/IPv6.
        device_override:    Replaces the device fingerprint string.
        resource_override:  Replaces the accessed resource string.
        force_off_hours:    If True, generator forces timestamp outside working hours.
        off_hours_range:    (start_hour, end_hour) to use when force_off_hours=True.
                            Defaults to (1, 4) — the quietest part of the night.
        anomaly_probability: Relative weight for automatic random injection.
                            Higher values = more frequent automatic injection.
                            Not used for manually triggered scenarios.
    """
    name: str
    anomaly_type: AnomalyType
    description: str
    action_override: Optional[str] = None
    location_override: Optional[str] = None
    ip_override: Optional[str] = None
    device_override: Optional[str] = None
    resource_override: Optional[str] = None
    force_off_hours: bool = False
    off_hours_range: Tuple[int, int] = (1, 4)
    anomaly_probability: float = 0.1  # Relative injection weight for auto-mode


# ---------------------------------------------------------------------------
# Scenario Registry
# All action_override values MUST match LogAction in schemas/log.py exactly.
# ---------------------------------------------------------------------------
ANOMALY_SCENARIOS: Dict[str, AnomalyDefinition] = {

    "impossible_travel": AnomalyDefinition(
        name="Impossible Travel",
        anomaly_type=AnomalyType.IMPOSSIBLE_TRAVEL,
        description=(
            "Login from a geographically distant location compared to the user's "
            "baseline — impossible to reach in the elapsed time since last login."
        ),
        action_override="LOGIN",
        location_override="RU (Moscow)",
        ip_override="185.10.0.5",
        anomaly_probability=0.15,
    ),

    "off_hours_access": AnomalyDefinition(
        name="Off-Hours Access",
        anomaly_type=AnomalyType.OFF_HOURS_ACCESS,
        description=(
            "User accessing systems significantly outside their normal working hours — "
            "a common indicator of credential theft or insider misuse."
        ),
        force_off_hours=True,
        off_hours_range=(1, 4),  # 1 AM – 4 AM local time
        anomaly_probability=0.20,
    ),

    "unrecognized_device": AnomalyDefinition(
        name="Unrecognised Device",
        anomaly_type=AnomalyType.UNRECOGNIZED_DEVICE,
        description=(
            "Access from a device fingerprint never previously seen for this user — "
            "may indicate a stolen session token or shared credential."
        ),
        action_override="LOGIN",
        device_override="Unknown-Android-Rooted",
        anomaly_probability=0.15,
    ),

    "data_exfiltration": AnomalyDefinition(
        name="Data Exfiltration",
        anomaly_type=AnomalyType.DATA_EXFILTRATION,
        description=(
            "Unusually large bulk download of sensitive resources — "
            "a common final stage of an insider threat or APT attack."
        ),
        action_override="BULK_DOWNLOAD",       # ← matches LogAction
        resource_override="Customer_DB_Export.csv",
        anomaly_probability=0.10,
    ),

    "privilege_escalation": AnomalyDefinition(
        name="Privilege Escalation Attempt",
        anomaly_type=AnomalyType.PRIVILEGE_ESCALATION,
        description=(
            "Standard-privilege user attempting to access admin-level resources "
            "or modify system configuration — matches lateral movement patterns."
        ),
        action_override="CONFIG_CHANGE",       # ← matches LogAction
        resource_override="Firewall_Rules",
        anomaly_probability=0.10,
    ),

    "compromised_credential": AnomalyDefinition(
        name="Compromised Credential",
        anomaly_type=AnomalyType.COMPROMISED_CREDENTIAL,   # ← own type now
        description=(
            "Combination of foreign IP, unknown device, and foreign location — "
            "strong indicator that credentials have been stolen and are being used "
            "by a threat actor from a different country."
        ),
        action_override="LOGIN",
        location_override="CN (Beijing)",
        ip_override="220.181.38.148",
        device_override="Kali-Linux-Root",
        anomaly_probability=0.10,
    ),

    "brute_force": AnomalyDefinition(
        name="Brute Force Login",
        anomaly_type=AnomalyType.BRUTE_FORCE,
        description=(
            "Rapid successive login attempt — indicative of automated credential "
            "stuffing or password spray attack."
        ),
        action_override="LOGIN",
        ip_override="91.108.4.201",
        location_override="NL (Amsterdam)",
        device_override="HeadlessChrome-Bot",
        anomaly_probability=0.12,
    ),

    "lateral_movement": AnomalyDefinition(
        name="Lateral Movement",
        anomaly_type=AnomalyType.LATERAL_MOVEMENT,
        description=(
            "Authenticated user accessing systems or data entirely outside their "
            "normal role scope — typical of post-compromise lateral movement."
        ),
        action_override="LATERAL_MOVE",        # ← matches LogAction
        resource_override="Prod_DB_Cluster",
        anomaly_probability=0.08,
    ),

    "data_exfil_via_api": AnomalyDefinition(
        name="Data Exfiltration via API",
        anomaly_type=AnomalyType.DATA_EXFILTRATION,
        description=(
            "High-volume automated API calls to a data endpoint — "
            "consistent with scripted exfiltration of records."
        ),
        action_override="DATA_EXFIL",          # ← matches LogAction
        resource_override="Customer_Records_API",
        ip_override="45.33.32.156",
        anomaly_probability=0.10,
    ),
}


# ---------------------------------------------------------------------------
# Public Helpers
# ---------------------------------------------------------------------------
def get_scenario(scenario_id: str) -> Optional[AnomalyDefinition]:
    """
    Returns the AnomalyDefinition for the given scenario ID.

    Args:
        scenario_id: Key in ANOMALY_SCENARIOS (case-insensitive, stripped).

    Returns:
        AnomalyDefinition if found, else None.
    """
    return ANOMALY_SCENARIOS.get(scenario_id.lower().strip())


def get_all_scenario_ids() -> List[str]:
    """
    Returns all registered scenario IDs.
    Used by the simulation API route to populate the frontend scenario selector.

    Returns:
        Sorted list of scenario ID strings.
    """
    return sorted(ANOMALY_SCENARIOS.keys())


def get_weighted_random_scenario() -> AnomalyDefinition:
    """
    Selects a random scenario weighted by each scenario's anomaly_probability.
    Called by the telemetry generator during automatic anomaly injection.

    Returns:
        A randomly selected AnomalyDefinition.
    """
    import random
    scenarios = list(ANOMALY_SCENARIOS.values())
    weights = [s.anomaly_probability for s in scenarios]
    return random.choices(scenarios, weights=weights, k=1)[0]