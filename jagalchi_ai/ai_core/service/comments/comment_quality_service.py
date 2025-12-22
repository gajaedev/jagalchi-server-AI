from __future__ import annotations

from typing import Dict

from jagalchi_ai.ai_core.common.nlp.text_utils import cheap_embed, cosine_similarity


class CommentQualityService:
    """코멘트 품질 및 감정 스코어링."""

    def __init__(self, relevance_threshold: float = 0.3) -> None:
        self._threshold = relevance_threshold

    def check_relevance(self, comment_text: str, tech_text: str) -> bool:
        comment_vec = cheap_embed(comment_text)
        tech_vec = cheap_embed(tech_text)
        similarity = cosine_similarity(comment_vec, tech_vec)
        return similarity >= self._threshold

    def sentiment_score(self, comment_text: str) -> float:
        negative_words = {"hate", "stupid", "바보", "쓰레기", "최악"}
        positive_words = {"thanks", "great", "좋아요", "감사"}
        tokens = set(comment_text.lower().split())
        score = 0.0
        score -= len(tokens & negative_words) * 0.2
        score += len(tokens & positive_words) * 0.1
        return round(score, 2)

    def aspect_sentiment(self, comment_text: str) -> Dict[str, float]:
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
        relevant = self.check_relevance(comment_text, tech_text)
        sentiment = self.sentiment_score(comment_text)
        aspects = self.aspect_sentiment(comment_text)
        return {
            "is_irrelevant": not relevant,
            "toxicity_score": max(-sentiment, 0.0),
            "aspect_sentiment": aspects,
            "action": "flag" if not relevant or sentiment < -0.3 else "allow",
        }
