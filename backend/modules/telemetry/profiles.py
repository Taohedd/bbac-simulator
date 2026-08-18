"""
Virtual user behavioral profiles for the BBAC Simulator telemetry module.
Defines what 'normal' behavior looks like for each user role so the synthetic
log generator can produce realistic baseline activity.

IMPORTANT: All action names in the `actions` dict MUST exactly match the
LogAction Literal defined in schemas/log.py. Any mismatch will cause Pydantic
validation to reject the generated log at insertion time.
"""

import random
import ipaddress
from dataclasses import dataclass, field
from typing import List, Dict, Tuple


# ---------------------------------------------------------------------------
# UserProfile Dataclass
# ---------------------------------------------------------------------------
@dataclass
class UserProfile:
    """
    Defines the baseline behavioral characteristics for a specific user role.
    Used by the synthetic log generator to produce realistic normal activity logs.

    Attributes:
        role:           The role name — must match UserRole in schemas/user.py.
        working_hours:  (start_hour, end_hour) in 24h format. End is exclusive.
        locations:      List of geographic location strings for this role.
        subnet_prefixes: List of IP subnet prefixes (e.g. '192.168.1').
                         The generator appends a random host octet to form a full IP.
        devices:        List of device fingerprint strings typical for this role.
        actions:        Dict mapping action name → relative probability weight.
                        Keys MUST match LogAction in schemas/log.py exactly.
                        Weights must sum to 1.0 (validated in __post_init__).
        resources:      List of resources this role typically accesses.
    """
    role: str
    working_hours: Tuple[int, int]
    locations: List[str]
    subnet_prefixes: List[str]
    devices: List[str]
    actions: Dict[str, float]
    resources: List[str]

    def __post_init__(self) -> None:
        """Validates profile integrity at definition time."""
        # Validate working hours
        start, end = self.working_hours
        if not (0 <= start <= 23 and 0 <= end <= 23):
            raise ValueError(
                f"[{self.role}] working_hours values must be 0–23, got {self.working_hours}"
            )
        # Validate action weights sum to 1.0 (within floating point tolerance)
        total = sum(self.actions.values())
        if not abs(total - 1.0) < 0.01:
            raise ValueError(
                f"[{self.role}] action probability weights must sum to 1.0, got {total:.4f}"
            )

    def random_ip(self) -> str:
        """
        Generates a random valid host IP address from one of this profile's
        subnet prefixes. The last octet is randomised between 2 and 254
        to avoid network (0) and broadcast (255) addresses.

        Returns:
            A valid IPv4 address string, e.g. '192.168.1.47'.
        """
        prefix = random.choice(self.subnet_prefixes)
        last_octet = random.randint(2, 254)
        return f"{prefix}.{last_octet}"

    def random_action(self) -> str:
        """
        Selects a random action weighted by the probability distribution
        defined in the actions dict.

        Returns:
            An action string guaranteed to match LogAction in schemas/log.py.
        """
        actions = list(self.actions.keys())
        weights = list(self.actions.values())
        return random.choices(actions, weights=weights, k=1)[0]

    def random_device(self) -> str:
        """Returns a random device fingerprint string for this profile."""
        return random.choice(self.devices)

    def random_location(self) -> str:
        """Returns a random location string for this profile."""
        return random.choice(self.locations)

    def random_resource(self) -> str:
        """Returns a random resource string for this profile."""
        return random.choice(self.resources)

    def is_working_hours(self, hour: int) -> bool:
        """
        Returns True if the given hour falls within this profile's working hours.
        Handles overnight ranges (e.g. 22–6 for a night-shift worker).
        """
        start, end = self.working_hours
        if start <= end:
            return start <= hour <= end
        # Overnight wrap-around (e.g. start=22, end=6)
        return hour >= start or hour <= end

    def get_typical_actions(self) -> Dict[str, float]:
        """
        Returns the action frequency dict for storage in UserBaseline.typical_actions_json.
        Called by the analytics baseline module when building a user's baseline record.
        """
        return dict(self.actions)


# ---------------------------------------------------------------------------
# Role Profiles
# All action names MUST exactly match LogAction in schemas/log.py.
# ---------------------------------------------------------------------------
PROFILES: Dict[str, UserProfile] = {

    "employee": UserProfile(
        role="employee",
        working_hours=(8, 18),
        locations=[
            "US-East (New York)",
            "US-West (San Francisco)",
            "US-Central (Chicago)",
        ],
        subnet_prefixes=["192.168.1", "192.168.2", "10.0.1"],
        devices=["Corp-Win-Laptop", "Corp-MacBook-Pro"],
        actions={
            "LOGIN":         0.10,
            "FILE_READ":     0.35,
            "FILE_WRITE":    0.15,
            "EMAIL_SEND":    0.15,
            "REPORT_VIEW":   0.10,
            "DB_QUERY":      0.05,
            "SETTINGS_VIEW": 0.05,
            "LOGOUT":        0.05,
        },
        resources=[
            "HR_Portal", "Project_Share", "Email_Server", "Intranet", "Report_Dashboard"
        ],
    ),

    "admin": UserProfile(
        role="admin",
        working_hours=(0, 23),   # 24/7 on-call access
        locations=["US-East (New York)", "VPN-Gateway", "US-West (San Francisco)"],
        subnet_prefixes=["10.0.0", "10.0.254", "192.168.254"],
        devices=["Admin-Linux-Workstation", "Admin-MacBook-Pro", "Admin-VPN-Client"],
        actions={
            "LOGIN":          0.08,
            "API_CALL":       0.25,
            "CONFIG_CHANGE":  0.15,
            "ADMIN_ACTION":   0.20,
            "REPORT_VIEW":    0.15,
            "DB_QUERY":       0.10,
            "SETTINGS_VIEW":  0.04,
            "LOGOUT":         0.03,
        },
        resources=[
            "Prod_DB_Cluster", "Firewall_Config", "K8s_Control_Plane",
            "Auth_Server", "SIEM_Dashboard", "Secrets_Manager"
        ],
    ),

    "analyst": UserProfile(
        role="analyst",
        working_hours=(9, 17),
        locations=["US-East (New York)", "US-Central (Chicago)", "Remote-VPN"],
        subnet_prefixes=["10.0.2", "172.16.10", "192.168.5"],
        devices=["Analyst-Win-Workstation", "Analyst-MacBook"],
        actions={
            "LOGIN":       0.08,
            "DB_QUERY":    0.35,
            "REPORT_VIEW": 0.30,
            "FILE_READ":   0.15,
            "API_CALL":    0.07,
            "LOGOUT":      0.05,
        },
        resources=[
            "Data_Warehouse", "BI_Dashboard", "Analytics_DB",
            "Report_Server", "ML_Pipeline_UI"
        ],
    ),

    "contractor": UserProfile(
        role="contractor",
        working_hours=(10, 16),
        locations=["UK (London)", "India (Bangalore)", "Canada (Toronto)"],
        subnet_prefixes=["203.0.113", "198.51.100", "172.16.20"],
        devices=["BYOD-Windows", "BYOD-Mac", "BYOD-Linux"],
        actions={
            "LOGIN":         0.12,
            "FILE_READ":     0.30,
            "FILE_WRITE":    0.25,
            "BULK_DOWNLOAD": 0.10,
            "API_CALL":      0.10,
            "EMAIL_SEND":    0.08,
            "LOGOUT":        0.05,
        },
        resources=[
            "Git_Repository", "Jira_Board", "Wiki",
            "Staging_Environment", "CI_CD_Pipeline"
        ],
    ),

    "viewer": UserProfile(
        role="viewer",
        working_hours=(9, 17),
        locations=["US-East (New York)", "US-West (San Francisco)"],
        subnet_prefixes=["192.168.10", "10.0.5"],
        devices=["Viewer-Corp-Laptop", "Viewer-Thin-Client"],
        actions={
            "LOGIN":       0.12,
            "FILE_READ":   0.45,
            "REPORT_VIEW": 0.30,
            "SETTINGS_VIEW": 0.05,
            "LOGOUT":      0.08,
        },
        resources=[
            "Public_Dashboard", "Read_Only_Reports",
            "Intranet", "Knowledge_Base"
        ],
    ),
}


# ---------------------------------------------------------------------------
# Public Helper
# ---------------------------------------------------------------------------
def get_profile_for_role(role: str) -> UserProfile:
    """
    Returns the UserProfile for the given role name (case-insensitive).
    Falls back to the 'employee' profile if the role is unrecognised.

    Args:
        role: The user's role string (e.g. 'admin', 'analyst').

    Returns:
        The matching UserProfile instance.
    """
    return PROFILES.get(role.lower().strip(), PROFILES["employee"])