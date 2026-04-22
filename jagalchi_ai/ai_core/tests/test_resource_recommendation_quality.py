import unittest

from jagalchi_ai.ai_core.repository.snapshot_store import SnapshotStore
from jagalchi_ai.ai_core.service.recommendation.resource_recommender import ResourceRecommendationService
from jagalchi_ai.ai_core.service.retrieval.search_quality import SearchLang


class FakeRetrieverItem:
    def __init__(self, *, title: str, url: str, score: float, snippet: str, item_id: str) -> None:
        self.metadata = {
            "title": title,
            "url": url,
            "snippet": snippet,
        }
        self.source = "resource"
        self.score = score
        self.snippet = snippet
        self.item_id = item_id


class FakeRetriever:
    def __init__(self, items: list[FakeRetrieverItem]) -> None:
        self._items = items

    def search(self, query: str, top_k: int):
        return self._items[:top_k]


class FakeWebSearch:
    def __init__(self, results: list[dict]) -> None:
        self._results = results
        self.calls: list[dict] = []

    def available(self) -> bool:
        return True

    def search(self, query: str, top_k: int = 5, recency_days=None, lang=None):
        self.calls.append(
            {
                "query": query,
                "top_k": top_k,
                "recency_days": recency_days,
                "lang": lang,
            }
        )
        return self._results[:top_k]


class ResourceRecommendationServiceForTest(ResourceRecommendationService):
    def __init__(self, *, local_results: list[FakeRetrieverItem], web_search: FakeWebSearch) -> None:
        self._local_results = local_results
        super().__init__(snapshot_store=SnapshotStore(), web_search=web_search)

    def _build_retriever(self):
        return FakeRetriever(self._local_results)


class ResourceRecommendationQualityTests(unittest.TestCase):
    def test_lang_ko_only_filters_resource_items(self) -> None:
        web_search = FakeWebSearch(
            results=[
                {
                    "title": "Python async tutorial",
                    "url": "https://example.com/python-async",
                    "content": "Beginner async guide",
                    "score": 0.9,
                    "source": "apify",
                },
                {
                    "title": "파이썬 비동기 입문",
                    "url": "https://velog.io/@dev/python-async",
                    "content": "한글 튜토리얼",
                    "score": 0.6,
                    "source": "apify",
                },
            ]
        )
        service = ResourceRecommendationServiceForTest(
            local_results=[
                FakeRetrieverItem(
                    title="Async deep dive",
                    url="https://random.dev/async",
                    score=0.85,
                    snippet="Low level internals",
                    item_id="local:1",
                ),
            ],
            web_search=web_search,
        )

        payload = service.recommend("python async tutorial", top_k=5, lang=SearchLang.KO_ONLY)
        urls = [item["url"] for item in payload["items"]]
        self.assertTrue(all("example.com" not in url for url in urls))
        self.assertTrue(any("velog.io" in url for url in urls))
        self.assertEqual(web_search.calls[0]["lang"], SearchLang.KO_ONLY)

    def test_items_include_quality_fields(self) -> None:
        web_search = FakeWebSearch(
            results=[
                {
                    "title": "React 공식 문서 useEffect",
                    "url": "https://react.dev/reference/react/useEffect",
                    "content": "공식 문서",
                    "score": 0.8,
                    "source": "apify",
                    "why_recommended": "공식 문서",
                    "difficulty": "intermediate",
                    "estimated_minutes": 20,
                }
            ]
        )
        service = ResourceRecommendationServiceForTest(local_results=[], web_search=web_search)
        payload = service.recommend("react useEffect dependency array", top_k=3, lang=SearchLang.KO_FIRST)
        self.assertTrue(payload["items"])
        item = payload["items"][0]
        self.assertIn("why_recommended", item)
        self.assertIn("difficulty", item)
        self.assertIn("estimated_minutes", item)


if __name__ == "__main__":
    unittest.main()
