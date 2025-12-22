from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional

from jagalchi_ai.ai_core.repository.mock_data import TAG_HIERARCHY


class TagGraph:
    """태그 계층 그래프."""

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
