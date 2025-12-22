from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from jagalchi_ai.ai_core.domain.threaded_comment import ThreadedComment


class CommentThreadService:
    """Materialized Path 기반 대댓글 관리."""

    def __init__(self) -> None:
        """
        댓글 스레드 저장소를 초기화합니다.

        @returns {None} 내부 상태만 구성합니다.
        """
        self._comments: Dict[str, ThreadedComment] = {}
        self._root_count = 0

    def create_root(self, roadmap_id: str, node_id: str, body: str) -> ThreadedComment:
        """
        루트 댓글을 생성합니다.

        @param {str} roadmap_id - 로드맵 식별자.
        @param {str} node_id - 노드 식별자.
        @param {str} body - 댓글 본문.
        @returns {ThreadedComment} 생성된 루트 댓글.
        """
        self._root_count += 1
        path = str(self._root_count)
        comment = ThreadedComment(
            comment_id=f"c{self._root_count}",
            roadmap_id=roadmap_id,
            node_id=node_id,
            body=body,
            path=path,
            created_at=datetime.utcnow(),
        )
        self._comments[comment.comment_id] = comment
        return comment

    def reply(self, parent_id: str, body: str) -> ThreadedComment:
        """
        특정 댓글에 대한 답글을 생성합니다.

        @param {str} parent_id - 부모 댓글 식별자.
        @param {str} body - 답글 본문.
        @returns {ThreadedComment} 생성된 답글.
        """
        parent = self._comments[parent_id]
        sibling_count = len([c for c in self._comments.values() if c.path.startswith(parent.path + ".")])
        path = f"{parent.path}.{sibling_count + 1}"
        comment = ThreadedComment(
            comment_id=f"c{len(self._comments) + 1}",
            roadmap_id=parent.roadmap_id,
            node_id=parent.node_id,
            body=body,
            path=path,
            created_at=datetime.utcnow(),
        )
        self._comments[comment.comment_id] = comment
        return comment

    def ordered_thread(self) -> List[ThreadedComment]:
        """
        스레드를 경로 순서로 정렬하여 반환합니다.

        @returns {List[ThreadedComment]} 정렬된 댓글 목록.
        """
        return sorted(self._comments.values(), key=lambda c: c.path)
