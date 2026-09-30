"""Comment theme analysis — uses OpenAI when configured, else rule-based fallback."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from app.config import get_settings

POSITIVE_WORDS = {
    "good", "great", "excellent", "supportive", "helpful", "clear", "strong",
    "leadership", "motivates", "respect", "fair", "positive", "communicates",
    "trust", "inspiring", "reliable", "professional",
}
IMPROVE_WORDS = {
    "improve", "improvement", "better", "delay", "unclear", "poor", "lack",
    "missing", "slow", "micromanage", "communication", "feedback", "listen",
    "pressure", "unfair", "inconsistent", "late", "confusing",
}


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z']+", text.lower())


def _rule_based(comments: list[str]) -> dict[str, Any]:
    pos_hits: Counter[str] = Counter()
    imp_hits: Counter[str] = Counter()
    recurring: Counter[str] = Counter()
    for c in comments:
        tokens = _tokenize(c)
        recurring.update(t for t in tokens if len(t) > 4)
        for t in tokens:
            if t in POSITIVE_WORDS:
                pos_hits[t] += 1
            if t in IMPROVE_WORDS:
                imp_hits[t] += 1

    strengths = [w for w, _ in pos_hits.most_common(5)] or ["No clear strength keywords detected"]
    improvements = [w for w, _ in imp_hits.most_common(5)] or ["No clear improvement keywords detected"]
    topics = [w for w, _ in recurring.most_common(8)]
    summary = (
        f"Analyzed {len(comments)} comments. "
        f"Common positive signals: {', '.join(strengths[:3])}. "
        f"Improvement areas: {', '.join(improvements[:3])}."
    )
    return {
        "themes": {
            "strengths": strengths,
            "improvement_areas": improvements,
            "recurring_topics": topics,
            "common_positive_feedback": strengths[:3],
            "repeated_concerns": improvements[:3],
            "method": "rule_based",
        },
        "summary": summary,
    }


def _openai_analysis(comments: list[str]) -> dict[str, Any] | None:
    settings = get_settings()
    if not settings.openai_api_key:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        joined = "\n---\n".join(comments[:80])
        prompt = (
            "Summarize employee feedback comments for management. "
            "Do not invent conclusions. Return JSON with keys: "
            "strengths (list), improvement_areas (list), recurring_topics (list), "
            "common_positive_feedback (list), repeated_concerns (list), summary (string). "
            "Keep meaning faithful to source comments.\n\nComments:\n" + joined
        )
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        import json

        data = json.loads(resp.choices[0].message.content or "{}")
        themes = {
            "strengths": data.get("strengths", []),
            "improvement_areas": data.get("improvement_areas", []),
            "recurring_topics": data.get("recurring_topics", []),
            "common_positive_feedback": data.get("common_positive_feedback", []),
            "repeated_concerns": data.get("repeated_concerns", []),
            "method": "openai",
        }
        return {"themes": themes, "summary": data.get("summary", "")}
    except Exception:
        return None


def analyze_comments(comments: list[str]) -> dict[str, Any]:
    cleaned = [c.strip() for c in comments if c and c.strip()]
    if not cleaned:
        return {
            "themes": {
                "strengths": [],
                "improvement_areas": [],
                "recurring_topics": [],
                "common_positive_feedback": [],
                "repeated_concerns": [],
                "method": "none",
            },
            "summary": "No comments available for analysis.",
        }
    ai = _openai_analysis(cleaned)
    if ai:
        return ai
    return _rule_based(cleaned)
