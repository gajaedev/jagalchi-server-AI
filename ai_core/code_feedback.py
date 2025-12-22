from __future__ import annotations

import re
from typing import Dict, List


def analyze_code(code: str) -> Dict[str, object]:
    issues: List[str] = []
    suggestions: List[str] = []

    if "TODO" in code:
        issues.append("TODO가 남아 있어 구현이 미완성일 수 있다")
        suggestions.append("TODO 항목을 해결하거나 이슈로 분리한다")

    if re.search(r"print\(", code):
        suggestions.append("디버그 출력 대신 로깅을 사용한다")

    if re.search(r"except\s*:\s*$", code, re.MULTILINE):
        issues.append("예외를 포괄적으로 처리하고 있다")
        suggestions.append("구체적인 예외 타입을 명시한다")

    return {
        "issues": issues,
        "suggestions": suggestions,
        "quality_score": max(0, 100 - len(issues) * 15 - len(suggestions) * 5),
    }
