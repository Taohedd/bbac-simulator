"""
Machine learning risk scoring for the BBAC Simulator analytics module.
Uses Scikit-Learn Isolation Forest to detect behavioural anomalies and
maps the raw anomaly score to a 0–100 risk scale.

Architecture note:
  This implementation uses ONE global model trained on the combined feature
  vectors of all users. This is appropriate for an academic simulator.
  A production system would train a per-user model so that deviation is
  measured against each user's own baseline rather than a population average.

Column order contract:
  FEATURE_NAMES is imported from feature_extractor.py and used for ALL
  array construction. Never build a numpy array or DataFrame from a raw
  dict — always go through FeatureExtractor.to_feature_vector() or
  FeatureExtractor.to_dataframe() to guarantee consistent column order.
"""

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from config import settings
from modules.analytics.feature_extractor import (
    FEATURE_NAMES,
    FeatureExtractor,
)

logger = logging.getLogger(__name__)


class RiskScorer:
    """
    Trains an Isolation Forest model on historical feature data and computes
    0–100 risk scores for incoming activity log feature vectors.

    Lifecycle:
        scorer.train(features_df)         # called by analytics engine
        score = scorer.compute_score(features_dict)
        scorer.reset()                    # called on simulation restart
    """

    def __init__(self) -> None:
        self._model: Optional[IsolationForest] = None
        self.is_trained: bool = False

        # Observed score range from training — used for robust normalisation.
        # Isolation Forest decision_function range is NOT guaranteed to be
        # [-0.5, 0.5]. We measure actual min/max on training data instead.
        self._score_min: float = -0.5   # Updated after each train() call
        self._score_max: float =  0.5   # Updated after each train() call

        # Training metadata — exposed via get_status()
        self._training_sample_count: int = 0

        self._init_model()

    def _init_model(self) -> None:
        """Initialises or re-initialises the Isolation Forest with current settings."""
        self._model = IsolationForest(
            n_estimators=settings.ML_N_ESTIMATORS,         # from config — not hardcoded
            contamination=settings.ML_CONTAMINATION_RATE,
            random_state=42,                               # reproducibility
            n_jobs=-1,                                     # use all available CPUs
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def train(self, features_df: pd.DataFrame) -> bool:
        """
        Trains the Isolation Forest on historical feature data.
        features_df must have columns in FEATURE_NAMES order — use
        FeatureExtractor.to_dataframe() to build it correctly.

        Args:
            features_df: DataFrame of shape (n_samples, len(FEATURE_NAMES)).

        Returns:
            True if training succeeded, False if skipped due to insufficient data.
        """
        if features_df.empty or len(features_df) < settings.ML_MIN_LOGS_FOR_BASELINE:
            logger.warning(
                "Training skipped — %d samples below minimum %d.",
                len(features_df), settings.ML_MIN_LOGS_FOR_BASELINE,
            )
            self.is_trained = False
            return False

        # Enforce column order contract
        features_df = features_df[FEATURE_NAMES]

        self._model.fit(features_df)
        self.is_trained = True
        self._training_sample_count = len(features_df)

        # Measure actual score range on training data for robust normalisation.
        # Using the training set itself avoids hardcoding a [-0.5, 0.5] assumption
        # that may not hold for this specific data distribution.
        raw_scores = self._model.decision_function(features_df)
        self._score_min = float(raw_scores.min())
        self._score_max = float(raw_scores.max())

        logger.info(
            "Isolation Forest trained on %d samples. "
            "Score range: [%.4f, %.4f].",
            self._training_sample_count,
            self._score_min,
            self._score_max,
        )
        return True

    def compute_score(self, features: Dict[str, float]) -> float:
        """
        Computes a 0–100 risk score for a single feature dictionary.

        0  = completely normal behaviour
        100 = maximally anomalous behaviour

        If the model is not yet trained, falls back to the heuristic scorer.

        Args:
            features: Dict produced by FeatureExtractor.extract_features().

        Returns:
            Float risk score in [0.0, 100.0].
        """
        if not self.is_trained:
            logger.debug("Model not trained — using heuristic fallback scorer.")
            return self._heuristic_score(features)

        # Build a correctly ordered 2-D array (shape: 1 × n_features)
        # Using to_feature_vector() guarantees FEATURE_NAMES column order.
        vector = FeatureExtractor.to_feature_vector(features).reshape(1, -1)

        # decision_function: positive = inlier (normal), negative = outlier (anomalous)
        raw_score: float = float(self._model.decision_function(vector)[0])

        # Normalise against the observed training range so the 0–100 scale
        # uses the full range rather than a hardcoded [-0.5, 0.5] assumption.
        # Invert so that anomalies (low raw score) map to HIGH risk values.
        score_range = self._score_max - self._score_min
        if score_range < 1e-9:
            # Degenerate case: all training scores identical — return midpoint
            return 50.0

        # Invert: low raw_score → high risk
        normalised = (self._score_max - raw_score) / score_range

        # Scale to 0–100 and clamp
        risk_score = max(0.0, min(100.0, normalised * 100.0))
        return round(float(risk_score), 2)

    def reset(self) -> None:
        """
        Resets the scorer to an untrained state.
        Called by the simulation API when a fresh simulation is started
        so stale training data from a previous run does not contaminate results.
        """
        self._init_model()
        self.is_trained = False
        self._training_sample_count = 0
        self._score_min = -0.5
        self._score_max =  0.5
        logger.info("RiskScorer reset — model cleared.")

    def get_status(self) -> Dict[str, object]:
        """
        Returns the current scorer state for the simulation status API route.
        """
        return {
            "is_trained": self.is_trained,
            "training_sample_count": self._training_sample_count,
            "score_range": {
                "min": round(self._score_min, 4),
                "max": round(self._score_max, 4),
            },
            "contamination_rate": settings.ML_CONTAMINATION_RATE,
            "n_estimators": settings.ML_N_ESTIMATORS,
            "feature_count": len(FEATURE_NAMES),
            "features": FEATURE_NAMES,
        }

    # ------------------------------------------------------------------
    # Heuristic fallback — used when model is not yet trained
    # ------------------------------------------------------------------

    def _heuristic_score(self, features: Dict[str, float]) -> float:
        """
        Rule-based risk scoring for the cold-start period before the ML
        model has sufficient training data.

        Uses all features defined in FEATURE_NAMES including is_off_hours
        and action_risk_weight, which are strong signals even without ML.

        Returns:
            Float risk score in [0.0, 100.0].
        """
        score = 5.0  # Small base risk for any activity

        # Time deviation — up to 25 points (max deviation = 12 hours)
        time_dev = features.get("time_deviation", 0.0)
        score += (time_dev / 12.0) * 25.0

        # Off-hours access — additional 15 point penalty on top of time deviation
        if features.get("is_off_hours", 0.0) > 0.5:
            score += 15.0

        # New IP subnet — 20 point penalty
        if features.get("is_new_ip_subnet", 0.0) > 0.5:
            score += 20.0

        # New device — 20 point penalty
        if features.get("is_new_device", 0.0) > 0.5:
            score += 20.0

        # Rare action (frequency < 5%) — up to 10 point penalty
        action_freq = features.get("action_frequency", 0.1)
        if action_freq < 0.05:
            score += 10.0
        elif action_freq < 0.10:
            score += 5.0

        # Inherent action risk weight — up to 10 point penalty
        # action_risk_weight is 0.1 (low) to 1.0 (critical)
        action_risk = features.get("action_risk_weight", 0.1)
        score += action_risk * 10.0

        return round(min(100.0, score), 2)


# ---------------------------------------------------------------------------
# Global singleton — imported by the analytics engine
# ---------------------------------------------------------------------------
risk_scorer = RiskScorer()