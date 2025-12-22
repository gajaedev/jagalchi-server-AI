from __future__ import annotations

from typing import Dict, List, Optional

from jagalchi_ai.ai_core.common.nlp.text_utils import cheap_embed, cosine_similarity, tokenize
from jagalchi_ai.ai_core.repository.mock_data import TECH_STACKS
from jagalchi_ai.ai_core.service.tags.tag_graph import TagGraph


class AutoTagger:
    """룰 기반 태그 자동 생성기."""

    def __init__(self, tag_graph: Optional[TagGraph] = None) -> None:
        self._tag_graph = tag_graph or TagGraph()

    def tag_text(self, text: str) -> List[Dict[str, object]]:
        tokens = tokenize(text)
        lowered = text.lower()
        text_vec = cheap_embed(text)
        tags = []
        for tech in TECH_STACKS.values():
            hits = sum(tokens.count(alias.lower()) for alias in tech.aliases)
            if hits == 0:
                hits = sum(1 for alias in tech.aliases if alias.lower() in lowered)
            if hits == 0:
                alias_scores = [cosine_similarity(text_vec, cheap_embed(alias)) for alias in tech.aliases]
                if alias_scores and max(alias_scores) >= 0.6:
                    hits = 1
            if hits == 0:
                continue
            confidence = min(0.5 + hits / max(len(tokens), 1), 1.0)
            tags.append(
                {
                    "tech_slug": tech.slug,
                    "type": _infer_tag_type(text, tech.aliases),
                    "confidence": round(confidence, 2),
                }
            )
        return tags

    def expand_query(self, tag: str) -> List[str]:
        return self._tag_graph.expand(tag)


def _infer_tag_type(text: str, aliases: List[str]) -> str:
    lowered = text.lower()
    for alias in aliases:
        if f"{alias} deprecated" in lowered or "deprecated" in lowered or "legacy" in lowered:
            return "deprecated"
        if f"{alias} 대안" in lowered or "alternative" in lowered:
            return "alternative"
    if any(alias in lowered for alias in aliases):
        return "core"
    return "optional"
