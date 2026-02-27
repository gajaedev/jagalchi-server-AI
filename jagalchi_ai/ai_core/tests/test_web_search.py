import unittest

from django.test import override_settings

from jagalchi_ai.ai_core.repository.snapshot_store import SnapshotStore
from jagalchi_ai.ai_core.service.retrieval.web_search_service import SearchEngine, SearchLang, WebSearchService


class FakeApifyResult:
    def __init__(self, title: str, url: str, content: str, score: float, published_date: str) -> None:
        self.title = title
        self.url = url
        self.content = content
        self.score = score
        self.published_date = published_date


class FakeApifyClient:
    def __init__(self, results: list[FakeApifyResult] | None = None) -> None:
        self.calls = 0
        self.actor = "apify/google-search-scraper"
        self._results = results or [
            FakeApifyResult(
                title="React Docs",
                url="https://react.dev",
                content="React 공식 문서 요약",
                score=0.91,
                published_date="2025-01-01",
            )
        ]

    @property
    def available(self) -> bool:
        return True

    def search(self, query: str, max_results: int = 5, country_code: str = "KR", language_code: str = "ko"):
        self.calls += 1
        return self._results[:max_results]


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

    def test_lang_ko_only_filters_non_korean_results(self) -> None:
        apify = FakeApifyClient(
            results=[
                FakeApifyResult(
                    title="Python async tutorial",
                    url="https://example.com/python-async",
                    content="Beginner async article",
                    score=0.95,
                    published_date="2025-01-01",
                ),
                FakeApifyResult(
                    title="파이썬 비동기 튜토리얼",
                    url="https://velog.io/@dev/python-async",
                    content="한글로 설명한 입문 자료",
                    score=0.62,
                    published_date="2025-01-01",
                ),
                FakeApifyResult(
                    title="장고 ORM 성능 최적화",
                    url="https://myblog.tistory.com/42",
                    content="실전 최적화 사례 정리",
                    score=0.54,
                    published_date="2025-01-01",
                ),
            ]
        )
        service = WebSearchService(apify_client=apify, snapshot_store=SnapshotStore())
        results = service.search(
            "python async tutorial",
            top_k=5,
            use_cache=False,
            lang=SearchLang.KO_ONLY,
        )
        self.assertEqual(len(results), 2)
        self.assertTrue(all("example.com" not in item["url"] for item in results))

    def test_domain_boost_ordering_in_ko_first(self) -> None:
        apify = FakeApifyClient(
            results=[
                FakeApifyResult(
                    title="Python async tutorial",
                    url="https://random.dev/async",
                    content="Good overview tutorial",
                    score=0.83,
                    published_date="2025-01-01",
                ),
                FakeApifyResult(
                    title="Python asyncio docs",
                    url="https://docs.python.org/3/library/asyncio.html",
                    content="Official guide",
                    score=0.72,
                    published_date="2025-01-01",
                ),
                FakeApifyResult(
                    title="파이썬 비동기 입문",
                    url="https://velog.io/@mentor/async",
                    content="한글 입문 자료",
                    score=0.6,
                    published_date="2025-01-01",
                ),
            ]
        )
        service = WebSearchService(apify_client=apify, snapshot_store=SnapshotStore())
        results = service.search(
            "python async tutorial",
            top_k=3,
            use_cache=False,
            lang=SearchLang.KO_FIRST,
        )
        self.assertEqual(len(results), 3)
        self.assertIn("velog.io", results[0]["url"])
        self.assertIn("docs.python.org", results[1]["url"])

    @override_settings(AI_SEARCH_DOMAIN_BLACKLIST=["blocked.com"])
    def test_blacklist_excludes_domain(self) -> None:
        apify = FakeApifyClient(
            results=[
                FakeApifyResult(
                    title="Blocked result",
                    url="https://blocked.com/python",
                    content="길이가 충분한 설명 텍스트입니다.",
                    score=0.95,
                    published_date="2025-01-01",
                ),
                FakeApifyResult(
                    title="React docs",
                    url="https://react.dev/learn",
                    content="Official React documentation",
                    score=0.5,
                    published_date="2025-01-01",
                ),
            ]
        )
        service = WebSearchService(apify_client=apify, snapshot_store=SnapshotStore())
        results = service.search(
            "react tutorial",
            top_k=5,
            use_cache=False,
            lang=SearchLang.GLOBAL,
        )
        urls = [item["url"] for item in results]
        self.assertTrue(all("blocked.com" not in url for url in urls))
        self.assertTrue(any("react.dev" in url for url in urls))

    def test_results_include_quality_fields(self) -> None:
        service = WebSearchService(apify_client=FakeApifyClient(), snapshot_store=SnapshotStore())
        results = service.search("react docs", top_k=1, use_cache=False)
        self.assertIn("why_recommended", results[0])
        self.assertIn("difficulty", results[0])
        self.assertIn("estimated_minutes", results[0])


if __name__ == "__main__":
    unittest.main()
