from __future__ import annotations

import os
import re
from enum import Enum
from typing import Any, Dict, Iterable, List, Sequence
from urllib.parse import parse_qsl, urlencode, urlparse

from django.conf import settings

KOREAN_LEARNING_BOOST_DOMAINS = {
    "velog.io",
    "tistory.com",
    "naver.com",
    "inflearn.com",
    "wikidocs.net",
    "school.programmers.co.kr",
}

NEUTRAL_HIGH_QUALITY_BOOST_DOMAINS = {
    "docs.python.org",
    "react.dev",
    "developer.mozilla.org",
}

SHORT_SNIPPET_MIN_LENGTH = 20
TRACKING_QUERY_KEYS = {"fbclid", "gclid", "igshid", "ref", "source"}
KOREAN_CHAR_PATTERN = re.compile(r"[가-힣]")
MINUTES_PATTERN = re.compile(r"\b(\d{1,3})\s*(?:분|min(?:ute)?s?)\b", re.IGNORECASE)


class SearchLang(str, Enum):
    KO_ONLY = "ko_only"
    KO_FIRST = "ko_first"
    GLOBAL = "global"


def normalize_search_lang(value: str | SearchLang | None) -> SearchLang:
    if isinstance(value, SearchLang):
        return value
    normalized = str(value or SearchLang.KO_FIRST.value).strip().lower()
    if normalized == SearchLang.KO_ONLY.value:
        return SearchLang.KO_ONLY
    if normalized == SearchLang.GLOBAL.value:
        return SearchLang.GLOBAL
    return SearchLang.KO_FIRST


def get_domain_blacklist() -> List[str]:
    raw = getattr(settings, "AI_SEARCH_DOMAIN_BLACKLIST", "")
    if isinstance(raw, str):
        values = raw.split(",")
    elif isinstance(raw, Iterable):
        values = [str(item) for item in raw]
    else:
        env_value = os.getenv("AI_SEARCH_DOMAIN_BLACKLIST", "")
        values = env_value.split(",")
    return _normalize_domains(values)


def apply_result_quality(
    items: List[Dict[str, Any]],
    *,
    query: str,
    top_k: int,
    lang: str | SearchLang | None,
    snippet_fields: Sequence[str] = ("content", "snippet"),
    domain_blacklist: Sequence[str] | None = None,
) -> List[Dict[str, Any]]:
    mode = normalize_search_lang(lang)
    blacklist = _normalize_domains(domain_blacklist) if domain_blacklist is not None else get_domain_blacklist()

    deduped: Dict[str, Dict[str, Any]] = {}
    for index, item in enumerate(items):
        url = str(item.get("url") or "").strip()
        if not url:
            continue

        domain = extract_domain(url)
        if not domain:
            continue
        if _is_blacklisted(domain, blacklist):
            continue

        snippet = _extract_text(item, snippet_fields)
        title = str(item.get("title") or "")
        text_blob = f"{title} {snippet}".strip()
        is_korean = _is_korean_item(domain, text_blob)
        if mode == SearchLang.KO_ONLY and not is_korean:
            continue

        base_score = float(item.get("score") or 0.0)
        adjusted_score = base_score + _domain_boost(domain)
        if mode == SearchLang.KO_FIRST and is_korean:
            adjusted_score += 0.12
        if snippet and len(snippet.strip()) < SHORT_SNIPPET_MIN_LENGTH:
            adjusted_score -= 0.03
        adjusted_score = round(max(0.0, min(1.0, adjusted_score)), 4)

        canonical = canonicalize_url(url)
        enriched = dict(item)
        enriched["score"] = adjusted_score
        enriched["why_recommended"] = _build_reason(domain, is_korean)
        enriched["difficulty"] = _infer_difficulty(text_blob)
        enriched["estimated_minutes"] = _infer_estimated_minutes(text_blob)
        enriched["_canonical_url"] = canonical
        enriched["_is_korean"] = 1 if is_korean else 0
        enriched["_snippet_len"] = len(snippet.strip()) if snippet else 0
        enriched["_order"] = -index

        existing = deduped.get(canonical)
        if existing is None:
            deduped[canonical] = enriched
            continue

        existing_rank = _rank_tuple(existing, mode)
        incoming_rank = _rank_tuple(enriched, mode)
        if incoming_rank > existing_rank:
            deduped[canonical] = enriched

    ranked = list(deduped.values())
    ranked.sort(key=lambda item: _rank_tuple(item, mode), reverse=True)
    ranked = _drop_short_snippets_if_possible(ranked, top_k=top_k)

    final_items = ranked[:top_k]
    for item in final_items:
        item.pop("_canonical_url", None)
        item.pop("_is_korean", None)
        item.pop("_snippet_len", None)
        item.pop("_order", None)
    return final_items


def canonicalize_url(url: str) -> str:
    raw = str(url or "").strip()
    if not raw:
        return ""
    parsed = _parse_url(raw)
    if not parsed:
        return raw.lower()

    domain = extract_domain(raw)
    if not domain:
        return raw.lower()

    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    if path != "/" and path.endswith("/"):
        path = path[:-1]

    filtered_qs = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=False):
        key_lower = key.strip().lower()
        if key_lower.startswith("utm_") or key_lower in TRACKING_QUERY_KEYS:
            continue
        filtered_qs.append((key, value))
    filtered_qs.sort(key=lambda pair: (pair[0], pair[1]))
    query = urlencode(filtered_qs, doseq=True)

    return f"{domain}{path}" + (f"?{query}" if query else "")


def extract_domain(url: str) -> str:
    parsed = _parse_url(url)
    if not parsed:
        return ""
    domain = (parsed.netloc or "").lower().strip()
    if not domain and parsed.path and "://" not in url:
        domain = parsed.path.lower().strip()
    if "@" in domain:
        domain = domain.split("@", 1)[-1]
    if ":" in domain:
        domain = domain.split(":", 1)[0]
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def legacy_dedupe_sort(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: Dict[str, Dict[str, Any]] = {}
    for item in results:
        url = str(item.get("url") or "").strip().lower()
        if not url:
            continue
        score = float(item.get("score") or 0.0)
        current = seen.get(url)
        if current is None or score > float(current.get("score") or 0.0):
            seen[url] = item
    merged = list(seen.values())
    merged.sort(key=lambda value: float(value.get("score") or 0.0), reverse=True)
    return merged


def _rank_tuple(item: Dict[str, Any], mode: SearchLang) -> tuple:
    korean_priority = int(item.get("_is_korean", 0)) if mode == SearchLang.KO_FIRST else 0
    return (
        float(item.get("score") or 0.0),
        korean_priority,
        int(item.get("_snippet_len", 0)),
        int(item.get("_order", 0)),
    )


def _extract_text(item: Dict[str, Any], fields: Sequence[str]) -> str:
    for field in fields:
        value = str(item.get(field) or "").strip()
        if value:
            return value
    return ""


def _is_korean_item(domain: str, text: str) -> bool:
    if KOREAN_CHAR_PATTERN.search(text):
        return True
    if domain.endswith(".kr"):
        return True
    return _domain_in_set(domain, KOREAN_LEARNING_BOOST_DOMAINS)


def _domain_boost(domain: str) -> float:
    if _domain_in_set(domain, KOREAN_LEARNING_BOOST_DOMAINS):
        return 0.24
    if _domain_in_set(domain, NEUTRAL_HIGH_QUALITY_BOOST_DOMAINS):
        return 0.18
    return 0.0


def _build_reason(domain: str, is_korean: bool) -> str:
    if _domain_in_set(domain, KOREAN_LEARNING_BOOST_DOMAINS):
        return "국내 학습 플랫폼"
    if _domain_in_set(domain, NEUTRAL_HIGH_QUALITY_BOOST_DOMAINS):
        return "공식 문서"
    if is_korean:
        return "한글 자료"
    return "주제 관련 자료"


def _infer_difficulty(text: str) -> str:
    lowered = (text or "").lower()
    if not lowered:
        return "unknown"

    advanced_keywords = ["고급", "심화", "advanced", "internals", "최적화", "optimization", "deep dive"]
    beginner_keywords = ["입문", "기초", "초보", "tutorial", "튜토리얼", "beginner", "getting started"]
    intermediate_keywords = ["중급", "intermediate", "실전", "best practice", "패턴", "실무"]

    if any(keyword in lowered for keyword in advanced_keywords):
        return "advanced"
    if any(keyword in lowered for keyword in beginner_keywords):
        return "beginner"
    if any(keyword in lowered for keyword in intermediate_keywords):
        return "intermediate"
    return "unknown"


def _infer_estimated_minutes(text: str) -> int | None:
    clean = (text or "").strip()
    if not clean:
        return None

    match = MINUTES_PATTERN.search(clean)
    if match:
        minutes = int(match.group(1))
        if 3 <= minutes <= 240:
            return minutes

    length = len(clean)
    if length < SHORT_SNIPPET_MIN_LENGTH:
        return None
    if length < 120:
        return 10
    if length < 260:
        return 15
    if length < 500:
        return 25
    return 40


def _drop_short_snippets_if_possible(items: List[Dict[str, Any]], *, top_k: int) -> List[Dict[str, Any]]:
    if len(items) <= top_k:
        return items
    long_items = [item for item in items if int(item.get("_snippet_len", 0)) >= SHORT_SNIPPET_MIN_LENGTH]
    if len(long_items) >= top_k:
        return long_items
    return items


def _parse_url(url: str):
    value = str(url or "").strip()
    if not value:
        return None
    if "://" not in value:
        value = f"https://{value}"
    try:
        return urlparse(value)
    except Exception:
        return None


def _normalize_domains(values: Sequence[str] | None) -> List[str]:
    if not values:
        return []
    normalized: List[str] = []
    for value in values:
        domain = extract_domain(str(value))
        if domain:
            normalized.append(domain)
            continue
        cleaned = str(value).strip().lower()
        if cleaned:
            normalized.append(cleaned)
    return sorted(set(normalized))


def _is_blacklisted(domain: str, blacklist: Sequence[str]) -> bool:
    return any(_domain_match(domain, blocked) for blocked in blacklist)


def _domain_in_set(domain: str, domain_set: Sequence[str]) -> bool:
    return any(_domain_match(domain, candidate) for candidate in domain_set)


def _domain_match(domain: str, candidate: str) -> bool:
    left = (domain or "").strip().lower()
    right = (candidate or "").strip().lower()
    if not left or not right:
        return False
    if left == right:
        return True
    return left.endswith(f".{right}")
