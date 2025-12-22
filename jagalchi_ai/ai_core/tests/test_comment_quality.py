import unittest

from jagalchi_ai.ai_core.comments.comment_quality import CommentQualityService, CommentThreadService


class CommentQualityTests(unittest.TestCase):
    def test_materialized_path(self) -> None:
        thread = CommentThreadService()
        root = thread.create_root("rm_frontend", "node_js", "첫 댓글")
        reply = thread.reply(root.comment_id, "대댓글")
        self.assertTrue(reply.path.startswith(root.path + "."))

    def test_relevance(self) -> None:
        quality = CommentQualityService(relevance_threshold=0.1)
        relevant = quality.check_relevance("React hooks 사용", "React hooks는 상태를 관리한다")
        self.assertTrue(relevant)
        moderation = quality.moderate("내용이 좋아요", "React hooks는 상태를 관리한다")
        self.assertIn("aspect_sentiment", moderation)


if __name__ == "__main__":
    unittest.main()
