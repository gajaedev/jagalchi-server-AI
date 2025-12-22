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
        """
        기본 계수를 초기화합니다.

        @returns {None} coefficients가 없을 때 기본값을 설정합니다.
        """
        if self.coefficients is None:
            self.coefficients = {"motivation": -0.8, "ability": -0.6, "gap": 0.4}

    def hazard(self, features: Dict[str, float]) -> float:
        """
        주어진 특성으로 위험도를 계산합니다.

        @param {Dict[str, float]} features - 모델 입력 특성.
        @returns {float} 위험도 값.
        """
        linear = sum(self.coefficients.get(key, 0.0) * value for key, value in features.items())
        return self.baseline_hazard * math.exp(linear)

    def survival_probability(self, features: Dict[str, float], time: float) -> float:
        """
        특정 시간까지의 생존 확률을 계산합니다.

        @param {Dict[str, float]} features - 모델 입력 특성.
        @param {float} time - 시간 값.
        @returns {float} 생존 확률.
        """
        hazard = self.hazard(features)
        return math.exp(-hazard * time)
