from __future__ import annotations

from typing import List

from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer


def density_cluster(texts: List[str], threshold: float = 0.35) -> List[List[str]]:
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
