import unittest

from jagalchi_ai.ai_core.retrieval.semantic_cache import SemanticCache


class SemanticCacheTests(unittest.TestCase):
    def test_cache_hit(self) -> None:
        cache = SemanticCache(threshold=0.9)
        cache.set("파이썬 설치 방법", "설치 가이드")
        entry = cache.get("파이썬 설치 방법")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.answer, "설치 가이드")


if __name__ == "__main__":
    unittest.main()
