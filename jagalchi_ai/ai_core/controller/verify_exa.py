from __future__ import annotations

from jagalchi_ai.ai_core.client import ExaSearchClient


def main() -> None:
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
