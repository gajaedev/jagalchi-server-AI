from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict


@dataclass
class CoxModel:
    """Cox 비례위험 모델(간단 버전)."""

    baseline_hazard: float = 0.02
    coefficients: Dict[str, float] = None

    def __post_init__(self) -> None:
        if self.coefficients is None:
            self.coefficients = {"motivation": -0.8, "ability": -0.6, "gap": 0.4}

    def hazard(self, features: Dict[str, float]) -> float:
        linear = sum(self.coefficients.get(key, 0.0) * value for key, value in features.items())
        return self.baseline_hazard * math.exp(linear)

    def survival_probability(self, features: Dict[str, float], time: float) -> float:
        hazard = self.hazard(features)
        return math.exp(-hazard * time)
