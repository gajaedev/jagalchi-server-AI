from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from django.conf import settings
from django.core.management.base import BaseCommand

from jagalchi_ai.ai_core.service.recommendation.resource_recommender import (
    legacy_merge_items,
    _merge_items,
)
from jagalchi_ai.ai_core.service.retrieval.search_quality import (
    SearchLang,
    apply_result_quality,
    extract_domain,
    legacy_dedupe_sort,
)


QUERIES = [
    "python async tutorial",
    "react useEffect dependency array",
    "장고 ORM 성능 최적화",
]


class Command(BaseCommand):
    help = "검색 품질 개선 전/후 비교 리포트를 생성합니다."

    def handle(self, *args, **options):
        report_path = Path(settings.BASE_DIR) / "docs" / "search-quality-before-after.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)

        sections = [
            "# Search Quality Before/After",
            "",
            f"- generated_at: {datetime.utcnow().isoformat()}Z",
            "- mode_before: legacy ranking",
            "- mode_after: ko_first quality ranking",
            "",
        ]

        for query in QUERIES:
            dataset = _build_dataset(query)
            web_before = legacy_dedupe_sort(dataset["web"])[:5]
            web_after = apply_result_quality(
                dataset["web"],
                query=query,
                top_k=5,
                lang=SearchLang.KO_FIRST,
                snippet_fields=("content",),
                domain_blacklist=[],
            )

            resource_web_items = [
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "source": item.get("source", "apify"),
                    "score": float(item.get("score") or 0.0),
                    "snippet": item.get("content", ""),
                }
                for item in dataset["web"]
            ]
            resource_before = legacy_merge_items(resource_web_items, dataset["local"], top_k=5)
            resource_after = _merge_items(
                resource_web_items,
                dataset["local"],
                query=query,
                top_k=5,
                lang=SearchLang.KO_FIRST,
            )

            sections.extend(
                [
                    f"## Query: {query}",
                    "",
                    "### Web Search",
                    "",
                    "#### Before (Top 5)",
                    _to_table(web_before),
                    "",
                    "#### After (Top 5)",
                    _to_table(web_after),
                    "",
                    "### Resource Recommendation",
                    "",
                    "#### Before (Top 5)",
                    _to_table(resource_before),
                    "",
                    "#### After (Top 5)",
                    _to_table(resource_after),
                    "",
                ]
            )

        report_path.write_text("\n".join(sections).strip() + "\n", encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Generated report: {report_path}"))


def _to_table(items: List[Dict[str, Any]]) -> str:
    lines = [
        "| rank | title | domain | score | why_recommended | difficulty | estimated_minutes |",
        "| --- | --- | --- | ---: | --- | --- | ---: |",
    ]
    for index, item in enumerate(items, start=1):
        title = str(item.get("title", "")).replace("|", " ")
        domain = extract_domain(str(item.get("url", "")))
        score = round(float(item.get("score") or 0.0), 4)
        why = str(item.get("why_recommended", "-")).replace("|", " ")
        difficulty = str(item.get("difficulty", "-"))
        minutes = item.get("estimated_minutes")
        minutes_text = "-" if minutes is None else str(minutes)
        lines.append(
            f"| {index} | {title} | {domain} | {score} | {why} | {difficulty} | {minutes_text} |"
        )
    return "\n".join(lines)


def _build_dataset(query: str) -> Dict[str, List[Dict[str, Any]]]:
    if query == "python async tutorial":
        return {
            "web": [
                _web("Python Async Tutorial", "https://example.com/python-async", "Beginner async tutorial", 0.92),
                _web("파이썬 비동기 입문", "https://velog.io/@kdev/python-async", "한글 입문 자료로 설명합니다", 0.61),
                _web("asyncio — Asynchronous I/O", "https://docs.python.org/3/library/asyncio.html?utm_source=search", "Official documentation for asyncio and event loop usage", 0.71),
                _web("asyncio — Asynchronous I/O", "https://docs.python.org/3/library/asyncio.html", "Official documentation duplicate", 0.69),
                _web("파이썬 async 실전", "https://mydev.tistory.com/42", "실전 사례 중심으로 정리한 한글 글", 0.58),
                _web("Async tips", "https://medium.com/x/async", "짧은글", 0.8),
            ],
            "local": [
                _local("Wikidocs 파이썬 코딩도장", "https://wikidocs.net/book/1", 0.74, "파이썬 기초부터 비동기 개념까지 다룹니다"),
                _local("Programmers 코딩테스트 연습", "https://school.programmers.co.kr/learn/challenges", 0.67, "실전 연습 문제"),
            ],
        }

    if query == "react useEffect dependency array":
        return {
            "web": [
                _web("useEffect complete guide", "https://random.dev/react-useeffect", "Complete guide with examples", 0.9),
                _web("React useEffect", "https://react.dev/reference/react/useEffect", "Official React docs for dependency array behavior", 0.72),
                _web("React useEffect 의존성 배열 정리", "https://velog.io/@frontend/useeffect-deps", "한글 자료로 실수 패턴 정리", 0.62),
                _web("MDN Closures", "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Closures", "Understanding closures and stale state", 0.65),
                _web("의존성 배열 한 줄 요약", "https://blog.naver.com/reactdeps", "요약", 0.66),
            ],
            "local": [
                _local("Inflearn React Hook 강의", "https://inflearn.com/course/react-hooks", 0.7, "useEffect 의존성 배열 실습"),
                _local("React 공식 튜토리얼", "https://react.dev/learn", 0.68, "기초부터 단계별 학습"),
            ],
        }

    return {
        "web": [
            _web("Django ORM performance tips", "https://example.com/django-orm-performance", "Advanced optimization checklist", 0.91),
            _web("장고 ORM 성능 최적화 가이드", "https://wikidocs.net/orm-opt", "한글로 explain, select_related, prefetch_related 설명", 0.68),
            _web("Django QuerySet API reference", "https://docs.python.org/3/library/sqlite3.html", "Database fundamentals and optimization references", 0.64),
            _web("장고 N+1 문제 해결", "https://mybackend.tistory.com/101", "실전 N+1 해결법", 0.63),
            _web("장고 ORM 성능 체크리스트", "https://velog.io/@django/perf-orm", "실무 최적화 항목 정리", 0.6),
            _web("ORM perf memo", "https://medium.com/django/perf", "짧은글", 0.79),
        ],
        "local": [
            _local("Django 성능 최적화 인프런", "https://inflearn.com/course/django-performance", 0.69, "ORM 최적화 실습 강의"),
            _local("Programmers SQL/DB 학습", "https://school.programmers.co.kr/learn/courses/30/parts/17044", 0.66, "데이터베이스 성능 기초"),
        ],
    }


def _web(title: str, url: str, content: str, score: float) -> Dict[str, Any]:
    return {
        "title": title,
        "url": url,
        "content": content,
        "score": score,
        "source": "apify",
    }


def _local(title: str, url: str, score: float, snippet: str) -> Dict[str, Any]:
    return {
        "title": title,
        "url": url,
        "source": "resource",
        "score": score,
        "snippet": snippet,
    }
