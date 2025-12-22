from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from jagalchi_ai.ai_core.domain.threaded_comment import ThreadedComment


class CommentThreadService:
    """Materialized Path 기반 대댓글 관리."""

    def __init__(self) -> None:
        self._comments: Dict[str, ThreadedComment] = {}
        self._root_count = 0

    def create_root(self, roadmap_id: str, node_id: str, body: str) -> ThreadedComment:
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
        return sorted(self._comments.values(), key=lambda c: c.path)
