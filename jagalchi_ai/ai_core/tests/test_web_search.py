import unittest

from jagalchi_ai.ai_core.repository.snapshot_store import SnapshotStore
from jagalchi_ai.ai_core.service.retrieval.web_search_service import SearchEngine, WebSearchService


class FakeApifyResult:
    def __init__(self, title: str, url: str, content: str, score: float, published_date: str) -> None:
        self.title = title
        self.url = url
        self.content = content
        self.score = score
        self.published_date = published_date


class FakeApifyClient:
    def __init__(self) -> None:
        self.calls = 0
        self.actor = "apify/google-search-scraper"

    @property
    def available(self) -> bool:
        return True

    def search(self, query: str, max_results: int = 5, country_code: str = "KR", language_code: str = "ko"):
        self.calls += 1
        return [
            FakeApifyResult(
                title="React Docs",
                url="https://react.dev",
                content="React 공식 문서 요약",
                score=0.91,
                published_date="2025-01-01",
            )
        ]


class DisabledApifyClient:
    actor = "apify/google-search-scraper"

    @property
    def available(self) -> bool:
        return False

    def search(self, *args, **kwargs):
        raise AssertionError("검색이 호출되면 안 됩니다.")


class WebSearchTests(unittest.TestCase):
    def test_web_search_cache_hit(self) -> None:
        store = SnapshotStore()
        apify = FakeApifyClient()
        service = WebSearchService(apify_client=apify, snapshot_store=store)

        first = service.search("react docs", top_k=1)
        second = service.search("react docs", top_k=1)

        self.assertEqual(apify.calls, 1)
        self.assertEqual(first, second)
        self.assertEqual(first[0]["source"], "apify")
        self.assertEqual(store.hits, 1)

    def test_web_search_unavailable(self) -> None:
        service = WebSearchService(apify_client=DisabledApifyClient())
        results = service.search("react docs", top_k=1, engine=SearchEngine.APIFY)
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
