"""Versioned calibration policies for System-1 decisions.

Confidence is evidence, not authority. Calibration thresholds vary by
model, question schema, language, and risk class.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

DEFAULT_CALIBRATION_ID = "calib-v1-20261002"


@dataclass(frozen=True)
class CalibrationProfile:
    """Threshold settings for a specific model, language, and schema combination."""

    calibration_id: str
    model: str
    language: str
    schema_version: str = "1.0.0"
    base_thresholds: Dict[str, float] = field(default_factory=dict)
    risk_multipliers: Dict[str, float] = field(default_factory=dict)

    def threshold_for(self, question_id: str, risk_class: str = "standard") -> float:
        """Calculate required confidence threshold."""
        base = self.base_thresholds.get(question_id, 0.70)
        multiplier = self.risk_multipliers.get(risk_class, 1.0)
        # Bounded in [0.1, 0.99]
        return min(0.99, max(0.1, base * multiplier))


# Canonical calibrated profiles for Hermes Work System-1
PROFILES: Dict[str, CalibrationProfile] = {
    # English profile
    f"{DEFAULT_CALIBRATION_ID}:multilingual:en": CalibrationProfile(
        calibration_id=DEFAULT_CALIBRATION_ID,
        model="multilingual",
        language="en",
        base_thresholds={
            "capability_family": 0.65,
            "preferred_candidate": 0.60,
            "needs_system2": 0.75,
            "ambiguity_kind": 0.70,
            "progress_class": 0.65,
            "known_recovery_path": 0.70,
        },
        risk_multipliers={
            "read_only": 0.90,
            "standard": 1.0,
            "mutation": 1.15,
            "destructive": 1.30,
        },
    ),
    # Portuguese profile (explicit multilingual routing)
    f"{DEFAULT_CALIBRATION_ID}:multilingual:pt": CalibrationProfile(
        calibration_id=DEFAULT_CALIBRATION_ID,
        model="multilingual",
        language="pt",
        base_thresholds={
            "capability_family": 0.65,
            "preferred_candidate": 0.60,
            "needs_system2": 0.75,
            "ambiguity_kind": 0.70,
            "progress_class": 0.65,
            "known_recovery_path": 0.70,
        },
        risk_multipliers={
            "read_only": 0.90,
            "standard": 1.0,
            "mutation": 1.15,
            "destructive": 1.30,
        },
    ),
}


class CalibrationPolicy:
    """Evaluates whether a decision satisfies required confidence gates."""

    def __init__(
        self,
        calibration_id: str = DEFAULT_CALIBRATION_ID,
        profiles: Optional[Dict[str, CalibrationProfile]] = None,
    ):
        self.calibration_id = calibration_id
        self._profiles = profiles or PROFILES

    def get_profile(self, model: str, language: str) -> CalibrationProfile:
        """Resolve the matching calibration profile or fallback to multilingual:en."""
        key = f"{self.calibration_id}:{model}:{language}"
        if key in self._profiles:
            return self._profiles[key]
        fallback_key = f"{self.calibration_id}:multilingual:en"
        return self._profiles.get(fallback_key, CalibrationProfile(
            calibration_id=self.calibration_id,
            model=model,
            language=language,
            base_thresholds={"default": 0.70},
            risk_multipliers={"standard": 1.0},
        ))

    def evaluate_confidence(
        self,
        question_id: str,
        confidence_value: float,
        model: str = "multilingual",
        language: str = "en",
        risk_class: str = "standard",
    ) -> bool:
        """Check if confidence_value meets the threshold for question_id and risk_class."""
        profile = self.get_profile(model, language)
        threshold = profile.threshold_for(question_id, risk_class)
        return confidence_value >= threshold


default_calibration_policy = CalibrationPolicy()
