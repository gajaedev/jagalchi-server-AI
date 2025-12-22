from __future__ import annotations

from typing import List


def ips_estimate(rewards: List[float], propensities: List[float]) -> float:
    if len(rewards) != len(propensities):
        raise ValueError("Rewards and propensities length mismatch")
    total = 0.0
    for reward, prop in zip(rewards, propensities):
        if prop <= 0:
            continue
        total += reward / prop
    return total / max(len(rewards), 1)
