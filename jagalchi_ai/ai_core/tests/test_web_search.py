import unittest

from jagalchi_ai.ai_core.client import ExaResult, TavilyResult
from jagalchi_ai.ai_core.repository.snapshot_store import SnapshotStore
from jagalchi_ai.ai_core.service.retrieval.web_search_service import WebSearchService


class FakeTavilyClient:
    def __init__(self) -> None:
        """
        테스트용 Tavily 클라이언트를 초기화합니다.

        @returns {None} 호출 카운트를 초기화합니다.
        """
        self.calls = 0

    def available(self) -> bool:
        """
        테스트 환경에서 사용 가능 여부를 반환합니다.

        @returns {bool} 항상 True.
        """
        return True

    def search(self, query: str, max_results: int = 5, include_raw_content: bool = False) -> list[TavilyResult]:
        """
        테스트용 고정 검색 결과를 반환합니다.

        @param {str} query - 검색 쿼리.
        @param {int} max_results - 최대 결과 수.
        @param {bool} include_raw_content - 본문 포함 여부.
        @returns {list[TavilyResult]} 고정된 검색 결과.
        """
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
        """
        비활성 클라이언트 상태를 반환합니다.

        @returns {bool} 항상 False.
        """
        return False

    def search(self, query: str, max_results: int = 5, include_raw_content: bool = False) -> list[TavilyResult]:
        """
        호출되면 안 되는 검색 메서드입니다.

        @param {str} query - 검색 쿼리.
        @param {int} max_results - 최대 결과 수.
        @param {bool} include_raw_content - 본문 포함 여부.
        @returns {list[TavilyResult]} 테스트 실패를 유발합니다.
        """
        raise AssertionError("검색이 호출되면 안 됩니다.")


class FakeExaClient:
    def __init__(self) -> None:
        """
        테스트용 Exa 클라이언트를 초기화합니다.

        @returns {None} 호출 카운트를 초기화합니다.
        """
        self.calls = 0

    def available(self) -> bool:
        """
        테스트 환경에서 사용 가능 여부를 반환합니다.

        @returns {bool} 항상 True.
        """
        return True

    def search(self, query: str, max_results: int = 5) -> list[ExaResult]:
        """
        테스트용 고정 검색 결과를 반환합니다.

        @param {str} query - 검색 쿼리.
        @param {int} max_results - 최대 결과 수.
        @returns {list[ExaResult]} 고정된 검색 결과.
        """
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
        """
        비활성 클라이언트 상태를 반환합니다.

        @returns {bool} 항상 False.
        """
        return False

    def search(self, query: str, max_results: int = 5) -> list[ExaResult]:
        """
        호출되면 안 되는 검색 메서드입니다.

        @param {str} query - 검색 쿼리.
        @param {int} max_results - 최대 결과 수.
        @returns {list[ExaResult]} 테스트 실패를 유발합니다.
        """
        raise AssertionError("검색이 호출되면 안 됩니다.")


class WebSearchTests(unittest.TestCase):
    def test_web_search_cache_hit(self) -> None:
        """
        캐시 히트 시 외부 호출이 중복되지 않는지 검증합니다.

        @returns {None} 테스트만 수행합니다.
        """
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
        """
        모든 외부 검색이 비활성일 때 빈 결과를 반환하는지 확인합니다.

        @returns {None} 테스트만 수행합니다.
        """
        service = WebSearchService(
            tavily_client=DisabledTavilyClient(),
            exa_client=DisabledExaClient(),
        )
        results = service.search("react docs", top_k=1)
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
