from __future__ import annotations

from typing import Dict, List

from jagalchi_ai.ai_core.common.nlp.text_utils import extractive_summary, tokenize


class CoveVerifier:
    """근거 기반 답변 검증기."""
    def verify(self, draft: str, evidence: List[Dict[str, str]]) -> Dict[str, object]:
        sentences = [s for s in draft.split(".") if s.strip()]
        verified = []
        unverified = []
        evidence_tokens = []
        for item in evidence:
            evidence_tokens.extend(tokenize(item.get("snippet", "")))

        for sentence in sentences:
            tokens = set(tokenize(sentence))
            if tokens and tokens.intersection(evidence_tokens):
                verified.append(sentence.strip())
            else:
                unverified.append(sentence.strip())

        revised = draft
        if unverified:
            revised = extractive_summary(". ".join(verified), max_sentences=2)

        return {
            "verified_sentences": verified,
            "unverified_sentences": unverified,
            "revised_answer": revised,
        }
