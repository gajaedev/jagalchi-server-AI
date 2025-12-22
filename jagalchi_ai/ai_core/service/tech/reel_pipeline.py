from __future__ import annotations

import re
from typing import Dict, List, Optional

from jagalchi_ai.ai_core.client import GeminiClient
from jagalchi_ai.ai_core.common.nlp.text_utils import extractive_summary
from jagalchi_ai.ai_core.domain.document import Document
from jagalchi_ai.ai_core.domain.reel_result import ReelResult
from jagalchi_ai.ai_core.service.retrieval.bm25_index import BM25Index


_LICENSE_WHITELIST = {"MIT", "Apache-2.0", "BSD", "GPL", "MPL"}


class ReelPipeline:
    """REEL 기반 메타데이터 추출 파이프라인."""

    def __init__(self, llm_client: Optional[GeminiClient] = None) -> None:
        """
        REEL 파이프라인을 초기화합니다.

        @param {Optional[GeminiClient]} llm_client - LLM 클라이언트.
        @returns {None} 내부 클라이언트를 설정합니다.
        """
        self._llm_client = llm_client or GeminiClient()

    def extract(self, sources: List[Dict[str, str]]) -> ReelResult:
        """
        문서 소스에서 핵심 메타데이터를 추출합니다.

        @param {List[Dict[str, str]]} sources - 문서 소스 목록.
        @returns {ReelResult} 메타데이터 및 근거 요약.
        """
        documents = [
            Document(doc_id=f"doc:{idx}", text=source["content"], metadata={"title": source["title"]})
            for idx, source in enumerate(sources)
        ]
        index = BM25Index()
        index.add_documents(documents)

        evidence = []
        for query in ["license", "version", "dependency", "release"]:
            hits = index.search(query, top_k=1)
            for hit in hits:
                evidence.append({"query": query, "snippet": hit.snippet})

        metadata = _extract_metadata(sources)
        metadata = self._validate(metadata)

        if self._llm_client.available():
            prompt = _build_prompt(sources)
            response = self._llm_client.generate_json(prompt)
            if response.data:
                metadata.update({key: response.data.get(key) for key in metadata})

        return ReelResult(metadata=metadata, evidence=evidence)

    def _validate(self, metadata: Dict[str, Optional[str]]) -> Dict[str, Optional[str]]:
        """
        메타데이터의 라이선스 필드를 검증합니다.

        @param {Dict[str, Optional[str]]} metadata - 메타데이터 딕셔너리.
        @returns {Dict[str, Optional[str]]} 정제된 메타데이터.
        """
        license_name = metadata.get("license") or ""
        if license_name and license_name not in _LICENSE_WHITELIST:
            metadata["license"] = "unknown"
        return metadata


def _extract_metadata(sources: List[Dict[str, str]]) -> Dict[str, Optional[str]]:
    """
    소스 문서에서 라이선스/버전/언어 정보를 추출합니다.

    @param {List[Dict[str, str]]} sources - 문서 소스 목록.
    @returns {Dict[str, Optional[str]]} 추출된 메타데이터.
    """
    content = " ".join(source["content"] for source in sources)
    license_match = re.search(r"License[:\s]+([A-Za-z0-9\-\.]+)", content, re.IGNORECASE)
    version_match = re.search(r"v?(\d+\.\d+(?:\.\d+)?)", content)
    language_match = re.search(r"Language[:\s]+([A-Za-z0-9\-\.]+)", content, re.IGNORECASE)
    return {
        "license": license_match.group(1).upper() if license_match else None,
        "latest_version": version_match.group(1) if version_match else None,
        "language": language_match.group(1) if language_match else None,
    }


def _build_prompt(sources: List[Dict[str, str]]) -> str:
    """
    LLM에 전달할 요약 기반 프롬프트를 생성합니다.

    @param {List[Dict[str, str]]} sources - 문서 소스 목록.
    @returns {str} 프롬프트 문자열.
    """
    summaries = [extractive_summary(source["content"]) for source in sources]
    return (
        "다음 요약을 참고해 기술의 language, license, latest_version을 JSON으로 반환해줘. "
        f"요약: {summaries}"
    )
