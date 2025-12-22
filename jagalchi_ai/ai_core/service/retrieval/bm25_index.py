from __future__ import annotations

from typing import Iterable, List

from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document as LangchainDocument

from jagalchi_ai.ai_core.common.nlp.text_utils import extractive_summary
from jagalchi_ai.ai_core.domain.document import Document
from jagalchi_ai.ai_core.domain.retrieval_item import RetrievalItem


class BM25Index:
    """BM25 기반 문서 검색 인덱스."""

    def __init__(self) -> None:
        self._docs: List[LangchainDocument] = []
        self._retriever: BM25Retriever | None = None

    def add_documents(self, documents: Iterable[Document]) -> None:
        for doc in documents:
            if not doc.text:
                continue
            metadata = {**doc.metadata, "doc_id": doc.doc_id, "snippet": extractive_summary(doc.text)}
            self._docs.append(LangchainDocument(page_content=doc.text, metadata=metadata))
        if self._docs:
            self._retriever = BM25Retriever.from_documents(self._docs)

    @property
    def retriever(self) -> BM25Retriever | None:
        return self._retriever

    def search(self, query: str, top_k: int = 5) -> List[RetrievalItem]:
        if not self._retriever:
            return []
        self._retriever.k = top_k
        docs = self._retriever.invoke(query)
        results: List[RetrievalItem] = []
        for idx, doc in enumerate(docs):
            metadata = doc.metadata or {}
            item_id = metadata.get("doc_id", f"bm25_{idx}")
            results.append(
                RetrievalItem(
                    source=metadata.get("source", "bm25"),
                    item_id=item_id,
                    score=1.0 / (idx + 1),
                    snippet=metadata.get("snippet", extractive_summary(doc.page_content)),
                    metadata=metadata,
                )
            )
        return results
