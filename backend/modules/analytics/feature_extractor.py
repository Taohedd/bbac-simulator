"""
Feature extraction logic for the BBAC Simulator analytics module.
Transforms raw ActivityLog + UserBaseline data into a consistent numerical
feature vector suitable for Scikit-Learn Isolation Forest scoring.

IMPORTANT: FEATURE_NAMES defines the authoritative column order for the
feature vector. Both this file and modules/analytics/risk_scorer.py must
import FEATURE_NAMES — never redefine it in the scorer.
"""

import ipaddress
import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from database.models import ActivityLog, UserBaseline

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Authoritative feature column order
# Import this in risk_scorer.py — do NOT redefine it there.
# The order here determines the column order of every numpy array passed
# to Isolation Forest. Changing order without retraining the model
# will silently corrupt all risk scores.
# ---------------------------------------------------------------------------
FEATURE_NAMES: List[str] = [
    "hour_of_day",        # Float 0.0–23.99 — time of event
    "time_deviation",     # Float 0.0–12.0  — circular distance from avg login hour
    "is_off_hours",       # Binary 0.0/1.0  — outside typical working time window
    "is_new_ip_subnet",   # Binary 0.0/1.0  — /24 subnet differs from baseline
    "is_new_device",      # Binary 0.0/1.0  — device not in baseline
    "action_frequency",   # Float 0.0–1.0   — how common this action is in baseline
    "action_risk_weight", # Float 0.0–1.0   — inherent danger of this action type
]

# ---------------------------------------------------------------------------
# Static risk weights for each action type
# Actions not listed here default to LOW_RISK_WEIGHT.
# These weights are INDEPENDENT of how frequently a user performs the action.
# A BULK_DOWNLOAD that's common for a user is still inherently high-risk.
# Must stay in sync with LogAction in schemas/log.py.
# ---------------------------------------------------------------------------
_LOW_RISK_WEIGHT  = 0.1
_MED_RISK_WEIGHT  = 0.4
_HIGH_RISK_WEIGHT = 0.8
_CRIT_RISK_WEIGHT = 1.0

ACTION_RISK_WEIGHTS: Dict[str, float] = {
    # Normal operations — low inherent risk
    "LOGIN":           _LOW_RISK_WEIGHT,
    "LOGOUT":          _LOW_RISK_WEIGHT,
    "FILE_READ":       _LOW_RISK_WEIGHT,
    "FILE_WRITE":      _MED_RISK_WEIGHT,
    "DB_QUERY":        _LOW_RISK_WEIGHT,
    "API_CALL":        _LOW_RISK_WEIGHT,
    "EMAIL_SEND":      _LOW_RISK_WEIGHT,
    "REPORT_VIEW":     _LOW_RISK_WEIGHT,
    "SETTINGS_VIEW":   _LOW_RISK_WEIGHT,
    "MFA_VERIFY":      _LOW_RISK_WEIGHT,
    "PASSWORD_CHANGE": _MED_RISK_WEIGHT,
    # Elevated risk operations
    "FILE_DELETE":     _MED_RISK_WEIGHT,
    "CONFIG_CHANGE":   _HIGH_RISK_WEIGHT,
    "ADMIN_ACTION":    _HIGH_RISK_WEIGHT,
    # Critical / attack-indicator operations
    "BULK_DOWNLOAD":        _HIGH_RISK_WEIGHT,
    "DB_EXPORT":            _HIGH_RISK_WEIGHT,
    "DATA_EXFIL":           _CRIT_RISK_WEIGHT,
    "LATERAL_MOVE":         _CRIT_RISK_WEIGHT,
    "PRIVILEGE_ESCALATION": _CRIT_RISK_WEIGHT,
}

# How many hours away from avg_login_hour counts as "off hours"
_OFF_HOURS_THRESHOLD: float = 4.0


# ---------------------------------------------------------------------------
# Feature Extractor
# ---------------------------------------------------------------------------
class FeatureExtractor:
    """
    Converts a single ActivityLog into a fixed-length numerical feature vector
    for use with Scikit-Learn Isolation Forest.

    All public methods produce features in the order defined by FEATURE_NAMES.
    """

    @staticmethod
    def extract_features(
        log: ActivityLog,
        baseline: Optional[UserBaseline],
    ) -> Dict[str, float]:
        """
        Extracts a feature dictionary from one ActivityLog + its UserBaseline.
        Keys are always exactly those listed in FEATURE_NAMES, in the same order.

        Args:
            log:      The ActivityLog ORM instance to evaluate.
            baseline: The user's UserBaseline, or None if not yet established.
                      Missing baseline fields default to values that indicate
                      no anomaly (0.0) rather than false-positive signals.

        Returns:
            OrderedDict with keys matching FEATURE_NAMES in order.
        """
        features: Dict[str, float] = {}

        # ------------------------------------------------------------------
        # 1. Time features
        # ------------------------------------------------------------------
        log_hour = log.timestamp.hour + (log.timestamp.minute / 60.0)
        features["hour_of_day"] = log_hour

        avg_hour: Optional[float] = baseline.avg_login_hour if baseline else None

        if avg_hour is not None:
            # Circular clock distance: handles wrap-around (e.g. 23:00 vs 01:00)
            diff = abs(log_hour - avg_hour)
            features["time_deviation"] = min(diff, 24.0 - diff)
            features["is_off_hours"] = (
                1.0 if features["time_deviation"] > _OFF_HOURS_THRESHOLD else 0.0
            )
        else:
            features["time_deviation"] = 0.0
            features["is_off_hours"] = 0.0

        # ------------------------------------------------------------------
        # 2. Network features — use ipaddress module for IPv4/IPv6 safety
        # ------------------------------------------------------------------
        log_subnet = FeatureExtractor._extract_subnet(log.ip_address)
        base_subnet = (baseline.common_subnet or "") if baseline else ""

        if not base_subnet:
            features["is_new_ip_subnet"] = 0.0   # No baseline → can't determine
        else:
            features["is_new_ip_subnet"] = 0.0 if log_subnet == base_subnet else 1.0

        # ------------------------------------------------------------------
        # 3. Device features
        # ------------------------------------------------------------------
        base_device = (baseline.common_device or "") if baseline else ""

        if not base_device:
            features["is_new_device"] = 0.0
        else:
            features["is_new_device"] = (
                0.0 if log.device_fingerprint == base_device else 1.0
            )

        # ------------------------------------------------------------------
        # 4. Action features
        # ------------------------------------------------------------------
        typical_actions: Dict[str, float] = {}
        if baseline and baseline.typical_actions_json:
            typical_actions = baseline.typical_actions_json

        # Frequency: how common is this action in the user's baseline?
        # 0.0 = never seen before = highly anomalous signal
        features["action_frequency"] = float(
            typical_actions.get(log.action, 0.0)
        )

        # Risk weight: inherent danger of this action type (static lookup)
        features["action_risk_weight"] = ACTION_RISK_WEIGHTS.get(
            log.action, _MED_RISK_WEIGHT
        )

        return features

    @staticmethod
    def to_feature_vector(features: Dict[str, float]) -> np.ndarray:
        """
        Converts a feature dictionary into a 1-D numpy array in the order
        defined by FEATURE_NAMES. This is what Isolation Forest receives.

        Args:
            features: Dict produced by extract_features().

        Returns:
            np.ndarray of shape (len(FEATURE_NAMES),) with dtype float64.

        Raises:
            KeyError: If a required feature name is missing from the dict.
        """
        return np.array(
            [features[name] for name in FEATURE_NAMES],
            dtype=np.float64,
        )

    @staticmethod
    def to_dataframe(features_list: List[Dict[str, float]]) -> pd.DataFrame:
        """
        Converts a list of feature dicts into a Pandas DataFrame with columns
        ordered by FEATURE_NAMES. Used for batch training in baseline.py.

        Args:
            features_list: List of dicts produced by extract_features().

        Returns:
            pd.DataFrame with shape (n, len(FEATURE_NAMES)).
        """
        return pd.DataFrame(features_list, columns=FEATURE_NAMES)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_subnet(ip_address: Optional[object]) -> str:
        """
        Extracts the /24 subnet prefix from an IP address for comparison.
        Handles both IPv4 and IPv6 safely using the ipaddress module.
        asyncpg may return IPv4Address objects instead of plain strings —
        this method handles both.

        Args:
            ip_address: IP address as a string, IPv4Address, or IPv6Address.

        Returns:
            For IPv4: first 3 octets joined by '.' (e.g. '192.168.1').
            For IPv6: first 4 groups (e.g. '2001:db8:85a3:0').
            Empty string if ip_address is None or unparseable.
        """
        if not ip_address:
            return ""
        try:
            addr = ipaddress.ip_address(str(ip_address))
            if isinstance(addr, ipaddress.IPv4Address):
                return ".".join(str(addr).split(".")[:3])
            # IPv6 — use first 4 groups as subnet approximation
            return ":".join(str(addr).split(":")[:4])
        except ValueError:
            logger.warning("Could not parse IP address for subnet extraction: %s", ip_address)
            return ""