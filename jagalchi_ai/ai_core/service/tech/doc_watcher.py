from __future__ import annotations

import hashlib
import re
from difflib import SequenceMatcher

from jagalchi_ai.ai_core.common.nlp.text_utils import extractive_summary
from jagalchi_ai.ai_core.domain.doc_change import DocChange


_TAG_RE = re.compile(r"<[^>]+>")


class DocWatcher:
    """문서 변경 감지기."""

    def __init__(self, change_threshold: float = 0.15) -> None:
        """
        변경 감지 임계값을 설정합니다.

        @param {float} change_threshold - 변경 판단 기준값.
        @returns {None} 임계값을 저장합니다.
        """
        self._threshold = change_threshold

    def checksum(self, content: str) -> str:
        """
        문서 내용을 SHA256 해시로 요약합니다.

        @param {str} content - 문서 내용.
        @returns {str} 해시 문자열.
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def semantic_diff(self, before: str, after: str) -> DocChange:
        """
        문서의 의미적 변경 여부를 계산합니다.

        @param {str} before - 이전 문서 내용.
        @param {str} after - 변경된 문서 내용.
        @returns {DocChange} 변경 요약 결과.
        """
        before_clean = _strip_html(before)
        after_clean = _strip_html(after)
        ratio = SequenceMatcher(None, before_clean, after_clean).ratio()
        change_ratio = 1 - ratio
        changed = change_ratio >= self._threshold
        summary = extractive_summary(after_clean)
        return DocChange(changed=changed, change_ratio=round(change_ratio, 4), summary=summary)


def _strip_html(text: str) -> str:
    """
    HTML 태그를 제거하고 정리합니다.

    @param {str} text - 입력 문자열.
    @returns {str} 태그가 제거된 텍스트.
    """
    return _TAG_RE.sub(" ", text).strip()
