from __future__ import annotations

import math
from typing import Dict, List, Optional

from jagalchi_ai.ai_core.client import GeminiClient
from jagalchi_ai.ai_core.common.nlp.text_utils import extract_sentences, tokenize


def textrank_sentences(text: str, top_n: int = 2) -> List[str]:
    """
    @param text 요약 대상 원문.
    @param top_n 선택할 문장 수.
    @returns TextRank 기반 상위 문장 리스트.
    """
    sentences = extract_sentences(text)
    if not sentences:
        return []
    if len(sentences) <= top_n:
        return sentences

    similarity = _sentence_similarity(sentences)
    scores = _pagerank(similarity)
    ranked = sorted(range(len(sentences)), key=lambda idx: scores[idx], reverse=True)
    selected = sorted(ranked[:top_n])
    return [sentences[idx] for idx in selected]


def hybrid_summary(text: str, llm_client: Optional[GeminiClient] = None, top_n: int = 2) -> str:
    """
    @param text 요약 대상 원문.
    @param llm_client LLM 클라이언트(있으면 문장화 보정).
    @param top_n 추출 요약 문장 수.
    @returns 추출+LLM 보정 요약 문자열.
    """
    extractive = " ".join(textrank_sentences(text, top_n=top_n))
    if not llm_client or not llm_client.available():
        return extractive
    prompt = (
        "다음 요약 후보를 참고해 핵심만 자연스럽게 한 문단으로 요약해줘. "
        f"요약 후보: {extractive}"
    )
    response = llm_client.generate_text(prompt)
    return response.strip() or extractive


def map_reduce_summary(texts: List[str], llm_client: Optional[GeminiClient] = None) -> str:
    """
    @param texts 요약 대상 텍스트 리스트.
    @param llm_client LLM 클라이언트(있으면 최종 보정).
    @returns Map-Reduce 요약 문자열.
    """
    if not texts:
        return ""
    mapped = [" ".join(textrank_sentences(text, top_n=2)) for text in texts]
    reduced = " ".join(mapped)
    return hybrid_summary(reduced, llm_client=llm_client, top_n=2)


def _sentence_similarity(sentences: List[str]) -> List[List[float]]:
    """
    @param sentences 문장 리스트.
    @returns 문장 간 유사도 행렬.
    """
    tokens = [set(tokenize(sentence)) for sentence in sentences]
    size = len(sentences)
    matrix = [[0.0 for _ in range(size)] for _ in range(size)]
    for i in range(size):
        for j in range(size):
            if i == j:
                continue
            intersection = tokens[i] & tokens[j]
            union = tokens[i] | tokens[j]
            matrix[i][j] = len(intersection) / max(len(union), 1)
    return matrix


def _pagerank(similarity: List[List[float]], damping: float = 0.85, iterations: int = 20) -> Dict[int, float]:
    """
    @param similarity 유사도 행렬.
    @param damping 감쇠 계수.
    @param iterations 반복 횟수.
    @returns 문장 인덱스별 PageRank 점수.
    """
    size = len(similarity)
    scores = {idx: 1.0 / size for idx in range(size)}
    for _ in range(iterations):
        next_scores = {idx: (1 - damping) / size for idx in range(size)}
        for i in range(size):
            norm = sum(similarity[i]) or 1.0
            for j in range(size):
                next_scores[j] += damping * (similarity[i][j] / norm) * scores[i]
        scores = next_scores
    return scores
