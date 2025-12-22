from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional

from jagalchi_ai.ai_core.repository.mock_data import TAG_HIERARCHY


class TagGraph:
    """태그 계층 그래프."""

    def __init__(self, hierarchy: Optional[Dict[str, List[str]]] = None) -> None:
        """
        태그 계층 그래프를 초기화합니다.

        @param {Optional[Dict[str, List[str]]]} hierarchy - 부모-자식 매핑.
        @returns {None} 그래프를 구성합니다.
        """
        self._children = defaultdict(list)
        self._parents = defaultdict(list)
        hierarchy = hierarchy or TAG_HIERARCHY
        for parent, children in hierarchy.items():
            for child in children:
                self.add_edge(parent, child)

    def add_edge(self, parent: str, child: str) -> None:
        """
        태그 간 부모-자식 관계를 추가합니다.

        @param {str} parent - 부모 태그.
        @param {str} child - 자식 태그.
        @returns {None} 그래프에 엣지를 추가합니다.
        """
        self._children[parent].append(child)
        self._parents[child].append(parent)

    def expand(self, tag: str) -> List[str]:
        """
        태그의 하위 태그를 모두 확장합니다.

        @param {str} tag - 기준 태그.
        @returns {List[str]} 확장된 태그 목록.
        """
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
        """
        태그의 부모 태그를 반환합니다.

        @param {str} tag - 기준 태그.
        @returns {List[str]} 부모 태그 목록.
        """
        return self._parents.get(tag, [])
