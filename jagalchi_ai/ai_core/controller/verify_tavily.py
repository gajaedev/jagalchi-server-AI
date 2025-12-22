"""
=============================================================================
Tavily 클라이언트 검증 스크립트 (Verification Script)
=============================================================================

이 스크립트는 `TavilySearchClient`의 정상 동작 여부를 검증합니다.
동기 및 비동기 검색 기능을 모두 테스트하고, 결과를 출력합니다.

실행 방법:
    python -m jagalchi_ai.ai_core.controller.verify_tavily

전제 조건:
    1. .env 파일에 `TAVILY_API_KEY`가 설정되어 있어야 합니다.
    2. 필요한 패키지가 설치되어 있어야 합니다 (`pip install -r requirements.txt`).
"""

import asyncio
import logging
import os
import sys
import time
from pathlib import Path

# 프로젝트 루트 경로 추가 (모듈 임포트용)
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
sys.path.append(str(project_root))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("TavilyVerifier")

try:
    from jagalchi_ai.ai_core.client.tavily_client import (
        TavilySearchClient,
        TavilySearchOptions,
        SearchDepth,
        SearchTopic
    )
    from dotenv import load_dotenv
except ImportError as e:
    logger.error(f"필수 모듈을 임포트할 수 없습니다: {e}")
    logger.error("가상환경이 활성화되어 있는지, 패키지가 설치되었는지 확인해주세요.")
    sys.exit(1)


def print_separator(title: str):
    """
    콘솔 출력 구분선을 표시합니다.

    @param {str} title - 구분선에 표시할 제목.
    @returns {None} 출력만 수행합니다.
    """
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}")


def print_result(result):
    """
    검색 결과 한 건을 보기 좋은 형식으로 출력합니다.

    @param {object} result - Tavily 결과 객체.
    @returns {None} 출력만 수행합니다.
    """
    print(f"- [{result.score:.2f}] {result.title}")
    print(f"  URL: {result.url}")
    print(f"  Content: {result.content[:100]}...")


def verify_sync_search(client: TavilySearchClient):
    """
    동기 검색 기능을 검증합니다.

    @param {TavilySearchClient} client - Tavily 검색 클라이언트.
    @returns {None} 검증 로그를 출력합니다.
    """
    print_separator("1. 동기 검색 테스트 (Synchronous)")
    
    query = "Python 3.12 새로운 기능"
    logger.info(f"검색 시작: '{query}'")
    
    start_time = time.time()
    results = client.search(query, max_results=3, search_depth=SearchDepth.BASIC)
    duration = time.time() - start_time
    
    logger.info(f"검색 완료 ({duration:.2f}초)")
    
    if not results:
        logger.warning("검색 결과가 없습니다.")
        return

    for r in results:
        print_result(r)


async def verify_async_search(client: TavilySearchClient):
    """
    비동기 검색 기능을 검증합니다.

    @param {TavilySearchClient} client - Tavily 검색 클라이언트.
    @returns {None} 검증 로그를 출력합니다.
    """
    print_separator("2. 비동기 검색 테스트 (Asynchronous)")
    
    query = "Django 비동기 뷰 튜토리얼"
    logger.info(f"비동기 검색 시작: '{query}'")
    
    start_time = time.time()
    # 비동기 메서드 호출
    results = await client.search_async(
        query, 
        max_results=3, 
        search_depth=SearchDepth.BASIC
    )
    duration = time.time() - start_time
    
    logger.info(f"비동기 검색 완료 ({duration:.2f}초)")
    
    if not results:
        logger.warning("검색 결과가 없습니다.")
        return

    for r in results:
        print_result(r)


def verify_news_search(client: TavilySearchClient):
    """
    뉴스 검색 기능을 검증합니다.

    @param {TavilySearchClient} client - Tavily 검색 클라이언트.
    @returns {None} 검증 로그를 출력합니다.
    """
    print_separator("3. 뉴스 검색 테스트")
    
    query = "인공지능 최신 뉴스"
    logger.info(f"뉴스 검색 시작: '{query}' (최근 3일)")
    
    results = client.search_news(query, days=3, max_results=3)
    
    if not results:
        logger.warning("최근 뉴스 결과가 없습니다.")
        return

    for r in results:
        print_result(r)
        if r.published_date:
            print(f"  Date: {r.published_date}")


async def main():
    """
    Tavily 검색 기능을 동기/비동기로 검증합니다.

    @returns {None} 표준 출력으로 검증 결과를 표시합니다.
    """
    # 환경변수 로드
    load_dotenv()
    
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        logger.error("❌ TAVILY_API_KEY가 환경변수에 설정되지 않았습니다.")
        logger.info(".env 파일을 생성하고 API 키를 입력해주세요.")
        return

    # 클라이언트 초기화
    client = TavilySearchClient()
    
    if not client.available:
        logger.error("❌ Tavily 클라이언트를 사용할 수 없는 상태입니다.")
        return

    logger.info("✅ Tavily 클라이언트 초기화 성공")

    # 테스트 실행
    try:
        verify_sync_search(client)
        await verify_async_search(client)
        verify_news_search(client)
        
        print_separator("검증 완료")
        logger.info("모든 테스트가 성공적으로 수행되었습니다.")
        
    except Exception as e:
        logger.error(f"❌ 테스트 중 오류 발생: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
