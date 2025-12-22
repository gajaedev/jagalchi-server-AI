import unittest

from jagalchi_ai.ai_core.repository.semantic_cache import SemanticCache


class SemanticCacheTests(unittest.TestCase):
    def test_cache_hit(self) -> None:
        """
        시맨틱 캐시 히트 여부를 검증합니다.

        @returns {None} 테스트만 수행합니다.
        """
        cache = SemanticCache(threshold=0.9)
        cache.set("파이썬 설치 방법", "설치 가이드")
        entry = cache.get("파이썬 설치 방법")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.answer, "설치 가이드")


if __name__ == "__main__":
    unittest.main()
