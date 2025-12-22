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
        self._threshold = change_threshold

    def checksum(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def semantic_diff(self, before: str, after: str) -> DocChange:
        before_clean = _strip_html(before)
        after_clean = _strip_html(after)
        ratio = SequenceMatcher(None, before_clean, after_clean).ratio()
        change_ratio = 1 - ratio
        changed = change_ratio >= self._threshold
        summary = extractive_summary(after_clean)
        return DocChange(changed=changed, change_ratio=round(change_ratio, 4), summary=summary)


def _strip_html(text: str) -> str:
    return _TAG_RE.sub(" ", text).strip()
