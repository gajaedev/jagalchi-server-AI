from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from ai_core.nlp.text_utils import cheap_embed, extractive_summary, tokenize
from ai_core.core.types import RetrievalItem
from ai_core.retrieval.vector_store import VectorStore


@dataclass
class Document:
    doc_id: str
    text: str
    metadata: Dict[str, str]


class BM25Index:
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


class HybridRetriever:
    def __init__(self, retrievers: List[tuple[str, callable]], weights: Optional[Dict[str, float]] = None) -> None:
        self._retrievers = retrievers
        self._weights = weights or {}

    def search(self, query: str, top_k: int = 5) -> List[RetrievalItem]:
        combined: Dict[str, RetrievalItem] = {}
        for name, retriever in self._retrievers:
            weight = self._weights.get(name, 1.0)
            items = retriever(query, top_k)
            for item in items:
                existing = combined.get(item.item_id)
                scored = item.score * weight
                if existing:
                    existing.score += scored
                else:
                    combined[item.item_id] = RetrievalItem(
                        source=item.source,
                        item_id=item.item_id,
                        score=scored,
                        snippet=item.snippet,
                        metadata=item.metadata,
                    )
        ranked = sorted(combined.values(), key=lambda i: i.score, reverse=True)
        return ranked[:top_k]


class VectorRetriever:
    def __init__(self, store: VectorStore, namespace: str = "") -> None:
        self._store = store
        self._namespace = namespace

    def search(self, query: str, top_k: int = 5) -> List[RetrievalItem]:
        vector = cheap_embed(query)
        filters = {"namespace": self._namespace} if self._namespace else None
        items = self._store.query(vector, top_k=top_k, filters=filters)
        results = []
        for item in items:
            results.append(
                RetrievalItem(
                    source=item.metadata.get("source", "vector"),
                    item_id=item.item_id,
                    score=1.0,
                    snippet=item.metadata.get("snippet", ""),
                    metadata=item.metadata,
                )
            )
        return results


class GraphRetriever:
    def __init__(self, adjacency: Dict[str, List[str]], node_text: Dict[str, str]) -> None:
        self._adjacency = adjacency
        self._node_text = node_text

    def search(self, node_id: str, top_k: int = 5) -> List[RetrievalItem]:
        related = self._adjacency.get(node_id, [])[:top_k]
        results = []
        for related_id in related:
            text = self._node_text.get(related_id, "")
            results.append(
                RetrievalItem(
                    source="graph",
                    item_id=related_id,
                    score=1.0,
                    snippet=extractive_summary(text),
                    metadata={"source": "graph"},
                )
            )
        return results
