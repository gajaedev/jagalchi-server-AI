from __future__ import annotations

from typing import Dict

from jagalchi_ai.ai_core.common.nlp.text_utils import cheap_embed, cosine_similarity


class CommentQualityService:
    """코멘트 품질 및 감정 스코어링."""

    def __init__(self, relevance_threshold: float = 0.3) -> None:
        """
        코멘트 품질 평가 임계값을 설정합니다.

        @param {float} relevance_threshold - 관련성 판단 기준값.
        @returns {None} 설정값을 저장합니다.
        """
        self._threshold = relevance_threshold

    def check_relevance(self, comment_text: str, tech_text: str) -> bool:
        """
        코멘트가 기술 설명과 관련 있는지 판단합니다.

        @param {str} comment_text - 코멘트 본문.
        @param {str} tech_text - 기술/카드 설명 텍스트.
        @returns {bool} 관련성이 있으면 True.
        """
        comment_vec = cheap_embed(comment_text)
        tech_vec = cheap_embed(tech_text)
        similarity = cosine_similarity(comment_vec, tech_vec)
        return similarity >= self._threshold

    def sentiment_score(self, comment_text: str) -> float:
        """
        간단한 키워드 기반 감정 점수를 계산합니다.

        @param {str} comment_text - 코멘트 본문.
        @returns {float} 감정 점수.
        """
        negative_words = {"hate", "stupid", "바보", "쓰레기", "최악"}
        positive_words = {"thanks", "great", "좋아요", "감사"}
        tokens = set(comment_text.lower().split())
        score = 0.0
        score -= len(tokens & negative_words) * 0.2
        score += len(tokens & positive_words) * 0.1
        return round(score, 2)

    def aspect_sentiment(self, comment_text: str) -> Dict[str, float]:
        """
        코멘트에서 특정 측면의 감정을 추출합니다.

        @param {str} comment_text - 코멘트 본문.
        @returns {Dict[str, float]} 측면별 감정 점수.
        """
        aspects = {
            "content": ["내용", "설명", "문서", "가이드"],
            "difficulty": ["난이도", "어렵", "쉬움", "hard", "easy"],
            "speed": ["속도", "느림", "빠름", "latency"],
        }
        sentiments = {}
        for aspect, keywords in aspects.items():
            if any(keyword in comment_text.lower() for keyword in keywords):
                sentiments[aspect] = self.sentiment_score(comment_text)
        return sentiments

    def moderate(self, comment_text: str, tech_text: str) -> Dict[str, object]:
        """
        코멘트의 관련성/감정을 기반으로 모더레이션 결과를 생성합니다.

        @param {str} comment_text - 코멘트 본문.
        @param {str} tech_text - 비교할 기술 설명 텍스트.
        @returns {Dict[str, object]} 모더레이션 판단 결과.
        """
        relevant = self.check_relevance(comment_text, tech_text)
        sentiment = self.sentiment_score(comment_text)
        aspects = self.aspect_sentiment(comment_text)
        return {
            "is_irrelevant": not relevant,
            "toxicity_score": max(-sentiment, 0.0),
            "aspect_sentiment": aspects,
            "action": "flag" if not relevant or sentiment < -0.3 else "allow",
        }
