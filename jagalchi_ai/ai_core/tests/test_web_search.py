import unittest

from jagalchi_ai.ai_core.clients.exa_client import ExaResult
from jagalchi_ai.ai_core.clients.tavily_client import TavilyResult
from jagalchi_ai.ai_core.core.snapshot import SnapshotStore
from jagalchi_ai.ai_core.retrieval.web_search import WebSearchService


class FakeTavilyClient:
    def __init__(self) -> None:
        self.calls = 0

    def available(self) -> bool:
        return True

    def search(self, query: str, max_results: int = 5, include_raw_content: bool = False) -> list[TavilyResult]:
        self.calls += 1
        return [
            TavilyResult(
                title="React Docs",
                url="https://react.dev",
                content="React 공식 문서 요약",
                score=0.91,
                published_date="2025-01-01",
            )
        ]


class DisabledTavilyClient:
    def available(self) -> bool:
        return False

    def search(self, query: str, max_results: int = 5, include_raw_content: bool = False) -> list[TavilyResult]:
        raise AssertionError("검색이 호출되면 안 됩니다.")


class FakeExaClient:
    def __init__(self) -> None:
        self.calls = 0

    def available(self) -> bool:
        return True

    def search(self, query: str, max_results: int = 5) -> list[ExaResult]:
        self.calls += 1
        return [
            ExaResult(
                title="React Docs",
                url="https://react.dev",
                content="React Exa 요약",
                score=0.95,
                published_date="2025-01-02",
            )
        ]


class DisabledExaClient:
    def available(self) -> bool:
        return False

    def search(self, query: str, max_results: int = 5) -> list[ExaResult]:
        raise AssertionError("검색이 호출되면 안 됩니다.")


class WebSearchTests(unittest.TestCase):
    def test_web_search_cache_hit(self) -> None:
        store = SnapshotStore()
        tavily = FakeTavilyClient()
        exa = FakeExaClient()
        service = WebSearchService(tavily_client=tavily, exa_client=exa, snapshot_store=store)
        first = service.search("react docs", top_k=1)
        second = service.search("react docs", top_k=1)
        self.assertEqual(tavily.calls, 1)
        self.assertEqual(exa.calls, 1)
        self.assertEqual(first, second)
        self.assertEqual(first[0]["source"], "exa")
        self.assertEqual(store.hits, 1)

    def test_web_search_unavailable(self) -> None:
        service = WebSearchService(
            tavily_client=DisabledTavilyClient(),
            exa_client=DisabledExaClient(),
        )
        results = service.search("react docs", top_k=1)
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
