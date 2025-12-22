from __future__ import annotations

import math
from collections import Counter
from typing import Dict, Iterable, List

from jagalchi_ai.ai_core.common.nlp.text_utils import extractive_summary, tokenize
from jagalchi_ai.ai_core.domain.document import Document
from jagalchi_ai.ai_core.domain.retrieval_item import RetrievalItem


class BM25Index:
    """BM25 기반 문서 검색 인덱스."""

    def __init__(self) -> None:
        self._docs: Dict[str, Document] = {}
        self._doc_freq: Counter = Counter()
        self._doc_len: Dict[str, int] = {}
        self._avg_len = 0.0

    def add_documents(self, documents: Iterable[Document]) -> None:
        for doc in documents:
            tokens = tokenize(doc.text)
            if not tokens:
                continue
            self._docs[doc.doc_id] = doc
            self._doc_len[doc.doc_id] = len(tokens)
            self._doc_freq.update(set(tokens))
        self._avg_len = sum(self._doc_len.values()) / max(len(self._doc_len), 1)

    def search(self, query: str, top_k: int = 5, k1: float = 1.5, b: float = 0.75) -> List[RetrievalItem]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
        scores: Dict[str, float] = {}
        for doc_id, doc in self._docs.items():
            doc_tokens = tokenize(doc.text)
            if not doc_tokens:
                continue
            tf = Counter(doc_tokens)
            score = 0.0
            for term in query_tokens:
                if term not in tf:
                    continue
                df = self._doc_freq.get(term, 0)
                idf = math.log((len(self._docs) - df + 0.5) / (df + 0.5) + 1)
                numerator = tf[term] * (k1 + 1)
                denominator = tf[term] + k1 * (1 - b + b * (len(doc_tokens) / (self._avg_len or 1)))
                score += idf * (numerator / denominator)
            if score > 0:
                scores[doc_id] = score
        ranked = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)[:top_k]
        results = []
        for doc_id, score in ranked:
            doc = self._docs[doc_id]
            results.append(
                RetrievalItem(
                    source=doc.metadata.get("source", "bm25"),
                    item_id=doc_id,
                    score=score,
                    snippet=extractive_summary(doc.text),
                    metadata=doc.metadata,
                )
            )
        return results
