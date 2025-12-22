import re
from collections import Counter
from typing import Iterable, List

from sklearn.feature_extraction.text import HashingVectorizer

_WORD_RE = re.compile(r"[\w\-\+\.]+", re.UNICODE)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_VECTORIZER_CACHE: dict[int, HashingVectorizer] = {}


def normalize_text(text: str) -> str:
    """
    @param text 정규화할 원문.
    @returns 공백을 정리한 문자열.
    """
    return " ".join(text.strip().split())


def tokenize(text: str) -> List[str]:
    """
    @param text 토큰화할 문자열.
    @returns 소문자 토큰 리스트.
    """
    return [token.lower() for token in _WORD_RE.findall(text)]


def token_counts(text: str) -> Counter:
    """
    @param text 토큰 빈도 계산 대상 문자열.
    @returns 토큰 빈도 Counter.
    """
    return Counter(tokenize(text))


def jaccard_similarity(a: Iterable[str], b: Iterable[str]) -> float:
    """
    @param a 토큰 시퀀스 A.
    @param b 토큰 시퀀스 B.
    @returns Jaccard 유사도(0~1).
    """
    set_a = set(a)
    set_b = set(b)
    if not set_a and not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union else 0.0


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    @param vec_a 벡터 A.
    @param vec_b 벡터 B.
    @returns 코사인 유사도(0~1).
    """
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = sum(a * a for a in vec_a) ** 0.5
    norm_b = sum(b * b for b in vec_b) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def extract_sentences(text: str) -> List[str]:
    """
    @param text 문장 분리 대상 문자열.
    @returns 문장 리스트.
    """
    cleaned = normalize_text(text)
    if not cleaned:
        return []
    return _SENTENCE_SPLIT_RE.split(cleaned)


def extractive_summary(text: str, max_sentences: int = 2) -> str:
    """
    @param text 요약 대상 문자열.
    @param max_sentences 최대 문장 수.
    @returns 길이 기반 추출 요약 문자열.
    """
    sentences = extract_sentences(text)
    if not sentences:
        return ""
    if len(sentences) <= max_sentences:
        return " ".join(sentences)
    scored = sorted(sentences, key=len, reverse=True)
    selected = scored[:max_sentences]
    ordered = [s for s in sentences if s in selected]
    return " ".join(ordered)


def cheap_embed(text: str, dim: int = 32) -> List[float]:
    """
    @param text 임베딩할 문자열.
    @param dim 임베딩 차원.
    @returns 해시 기반 경량 임베딩 벡터.
    """
    if not text.strip():
        return [0.0] * dim
    vectorizer = _get_vectorizer(dim)
    dense = vectorizer.transform([text]).toarray()
    return dense[0].tolist() if len(dense) else [0.0] * dim


def _get_vectorizer(dim: int) -> HashingVectorizer:
    """
    @param dim 해시 벡터 차원.
    @returns 캐시된 HashingVectorizer.
    """
    cached = _VECTORIZER_CACHE.get(dim)
    if cached:
        return cached
    vectorizer = HashingVectorizer(
        n_features=dim,
        alternate_sign=False,
        norm="l2",
        tokenizer=tokenize,
        token_pattern=None,
        lowercase=False,
    )
    _VECTORIZER_CACHE[dim] = vectorizer
    return vectorizer
