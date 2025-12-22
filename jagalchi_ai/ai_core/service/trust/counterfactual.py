from __future__ import annotations

from typing import List


def ips_estimate(rewards: List[float], propensities: List[float]) -> float:
    """
    IPS(Inverse Propensity Score) 기반으로 평균 보상을 추정합니다.

    @param {List[float]} rewards - 보상 값 목록.
    @param {List[float]} propensities - 행동 확률 목록.
    @returns {float} IPS 추정치.
    """
    if len(rewards) != len(propensities):
        raise ValueError("Rewards and propensities length mismatch")
    total = 0.0
    for reward, prop in zip(rewards, propensities):
        if prop <= 0:
            continue
        total += reward / prop
    return total / max(len(rewards), 1)
