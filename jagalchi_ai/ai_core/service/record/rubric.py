import re
from typing import Dict, List

from jagalchi_ai.ai_core.domain.learning_record import LearningRecord
from jagalchi_ai.ai_core.domain.link_meta import LinkMeta


_GOAL_KEYWORDS = ["목표", "goal", "달성", "의도"]
_PROBLEM_KEYWORDS = ["문제", "이슈", "bug", "error", "실패"]
_SOLUTION_KEYWORDS = ["해결", "fix", "개선", "조치", "원인"]
_NEXT_KEYWORDS = ["다음", "next", "추가", "계획"]

_ERROR_PATTERN = re.compile(r"(error|exception|traceback|fail|failed|500|404)", re.IGNORECASE)


def evidence_level(record: LearningRecord) -> int:
    if not record.memo.strip() and not record.links:
        return 0
    if record.memo.strip() and not record.links:
        return 1
    if any(link.status_code for link in record.links):
        if any(_is_verified(link) for link in record.links):
            return 3
        return 2
    return 2


def structure_score(record: LearningRecord) -> int:
    memo = record.memo.lower()
    sections = [
        _contains_any(memo, _GOAL_KEYWORDS),
        _contains_any(memo, _PROBLEM_KEYWORDS),
        _contains_any(memo, _SOLUTION_KEYWORDS),
        _contains_any(memo, _NEXT_KEYWORDS),
    ]
    return int(sum(sections) / len(sections) * 100)


def specificity_score(record: LearningRecord) -> int:
    memo = record.memo
    digit_hits = len(re.findall(r"\d+", memo))
    error_hits = 1 if _ERROR_PATTERN.search(memo) else 0
    keyword_hits = sum(token in memo.lower() for token in ["latency", "throughput", "query", "schema", "timeout"])
    raw_score = digit_hits * 10 + error_hits * 20 + keyword_hits * 10
    return min(raw_score, 100)


def reproducibility_score(links: List[LinkMeta]) -> int:
    if not links:
        return 0
    valid = sum(1 for link in links if _is_verified(link))
    return int(valid / len(links) * 100)


def quality_score(scores: Dict[str, int]) -> int:
    evidence = scores.get("evidence_level", 0) / 3
    structure = scores.get("structure_score", 0) / 100
    specificity = scores.get("specificity_score", 0) / 100
    reproducibility = scores.get("reproducibility_score", 0) / 100
    weighted = evidence * 0.3 + structure * 0.25 + specificity * 0.25 + reproducibility * 0.2
    return int(weighted * 100)


def score_record(record: LearningRecord) -> Dict[str, int]:
    scores = {
        "evidence_level": evidence_level(record),
        "structure_score": structure_score(record),
        "specificity_score": specificity_score(record),
        "reproducibility_score": reproducibility_score(record.links),
    }
    scores["quality_score"] = quality_score(scores)
    return scores


def _contains_any(text: str, keywords: List[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _is_verified(link: LinkMeta) -> bool:
    return link.is_public and link.status_code and 200 <= link.status_code < 300
