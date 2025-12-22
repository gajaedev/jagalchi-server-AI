from __future__ import annotations

from typing import List

from ai_core.nlp.text_utils import jaccard_similarity, tokenize


def density_cluster(texts: List[str], threshold: float = 0.35) -> List[List[str]]:
    clusters: List[List[str]] = []
    for text in texts:
        tokens = tokenize(text)
        placed = False
        for cluster in clusters:
            rep = cluster[0]
            if jaccard_similarity(tokens, tokenize(rep)) >= threshold:
                cluster.append(text)
                placed = True
                break
        if not placed:
            clusters.append([text])
    clusters.sort(key=lambda cluster: len(cluster), reverse=True)
    return clusters
