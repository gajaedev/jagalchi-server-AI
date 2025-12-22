from __future__ import annotations

from typing import List

from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer


def density_cluster(texts: List[str], threshold: float = 0.35) -> List[List[str]]:
    """
    @param texts 클러스터링 대상 문장 리스트.
    @param threshold 유사도 임계값(높을수록 엄격).
    @returns 클러스터별 텍스트 묶음 리스트.
    """
    if not texts:
        return []
    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform(texts)
    eps = max(0.1, 1 - threshold)
    clustering = DBSCAN(eps=eps, min_samples=1, metric="cosine")
    labels = clustering.fit_predict(vectors)
    grouped: dict[int, List[str]] = {}
    for label, text in zip(labels, texts):
        grouped.setdefault(int(label), []).append(text)
    clusters = list(grouped.values())
    clusters.sort(key=lambda cluster: len(cluster), reverse=True)
    return clusters
