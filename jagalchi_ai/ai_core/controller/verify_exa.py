from __future__ import annotations

from jagalchi_ai.ai_core.client import ExaSearchClient


def main() -> None:
    """
    Exa API 검색이 가능한지 확인하고 샘플 결과를 출력합니다.

    @returns {None} 표준 출력으로 결과를 표시합니다.
    """
    client = ExaSearchClient()
    if not client.available():
        print("EXA_API_KEY가 설정되지 않았습니다.")
        return
    results = client.search("React 공식 문서", max_results=3)
    if not results:
        print("검색 결과가 없습니다.")
        return
    for result in results:
        print(f"{result.title} | {result.url} | score={result.score}")


if __name__ == "__main__":
    main()
