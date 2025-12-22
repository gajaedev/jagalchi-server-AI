import hashlib
import json
from typing import Any


def stable_hash_text(text: str) -> str:
    """
    @param text 해시 대상 문자열.
    @returns SHA-256 해시 문자열.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def stable_hash_json(payload: Any) -> str:
    """
    @param payload 해시 대상 JSON 직렬화 가능한 데이터.
    @returns 정렬/정규화된 JSON 기준 SHA-256 해시 문자열.
    """
    canonical = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return stable_hash_text(canonical)
