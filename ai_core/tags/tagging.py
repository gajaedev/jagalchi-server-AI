from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional

from ai_core.core.mock_data import TAG_HIERARCHY, TECH_STACKS
from ai_core.nlp.text_utils import cheap_embed, cosine_similarity, tokenize


class TagGraph:
    def __init__(self, hierarchy: Optional[Dict[str, List[str]]] = None) -> None:
        self._children = defaultdict(list)
        self._parents = defaultdict(list)
        hierarchy = hierarchy or TAG_HIERARCHY
        for parent, children in hierarchy.items():
            for child in children:
                self.add_edge(parent, child)

    def add_edge(self, parent: str, child: str) -> None:
        self._children[parent].append(child)
        self._parents[child].append(parent)

    def expand(self, tag: str) -> List[str]:
        expanded = set()
        stack = [tag]
        while stack:
            current = stack.pop()
            for child in self._children.get(current, []):
                if child not in expanded:
                    expanded.add(child)
                    stack.append(child)
        return sorted(expanded)

    def parents(self, tag: str) -> List[str]:
        return self._parents.get(tag, [])


class AutoTagger:
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
                alias_scores = [
                    cosine_similarity(text_vec, cheap_embed(alias)) for alias in tech.aliases
                ]
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
