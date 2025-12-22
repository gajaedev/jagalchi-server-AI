from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from jagalchi_ai.ai_core.core.mock_data import EVENT_LOGS
from jagalchi_ai.ai_core.coach.survival_analysis import CoxModel
from jagalchi_ai.ai_core.core.types import EventLog


class BehaviorModel:
    def __init__(self, events: Optional[List[EventLog]] = None) -> None:
        self._events = events or EVENT_LOGS
        self._cox = CoxModel()

    def assess(self, user_id: str, days: int = 30) -> Dict[str, object]:
        cutoff = datetime.utcnow() - timedelta(days=days)
        events = [event for event in self._events if event.user_id == user_id and event.created_at >= cutoff]
        motivation = _motivation_score(events, days)
        ability = _ability_score(events)
        prompt_hour = _best_prompt_hour(events)
        dropout_risk = self._cox.hazard({"motivation": motivation, "ability": ability, "gap": 0.2})
        return {
            "motivation": round(motivation, 2),
            "ability": round(ability, 2),
            "prompt_hour": prompt_hour,
            "dropout_risk": round(dropout_risk, 4),
        }


def _motivation_score(events: List[EventLog], days: int) -> float:
    if not events:
        return 0.3
    active_days = len({event.created_at.date() for event in events})
    return min(1.0, active_days / max(days, 1))


def _ability_score(events: List[EventLog]) -> float:
    progress_events = sum(1 for event in events if event.event_type in {"rec_click", "record_feedback_view"})
    return min(1.0, progress_events / max(len(events), 1))


def _best_prompt_hour(events: List[EventLog]) -> int:
    if not events:
        return 20
    hours = Counter(event.created_at.hour for event in events)
    return hours.most_common(1)[0][0]
