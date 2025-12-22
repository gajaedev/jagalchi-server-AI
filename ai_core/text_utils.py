import math
import re
from collections import Counter
from typing import Iterable, List


_WORD_RE = re.compile(r"[\w\-\+\.]+", re.UNICODE)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def normalize_text(text: str) -> str:
    return " ".join(text.strip().split())


def tokenize(text: str) -> List[str]:
    return [token.lower() for token in _WORD_RE.findall(text)]


def token_counts(text: str) -> Counter:
    return Counter(tokenize(text))


def jaccard_similarity(a: Iterable[str], b: Iterable[str]) -> float:
    set_a = set(a)
    set_b = set(b)
    if not set_a and not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union else 0.0


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def extract_sentences(text: str) -> List[str]:
    cleaned = normalize_text(text)
    if not cleaned:
        return []
    return _SENTENCE_SPLIT_RE.split(cleaned)


def extractive_summary(text: str, max_sentences: int = 2) -> str:
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
    tokens = tokenize(text)
    if not tokens:
        return [0.0] * dim
    vector = [0.0] * dim
    for token in tokens:
        idx = hash(token) % dim
        vector[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0.0:
        return vector
    return [v / norm for v in vector]
