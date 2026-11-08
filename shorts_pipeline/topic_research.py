from typing import List
from .config import settings
from .models import TopicResearchResult, TopicCategory
from .database import db
from .llm import chat_json
from .utils import parse_json_response
from openai import OpenAI
import json

client = OpenAI(api_key=settings.nvidia_api_key, base_url=settings.nvidia_base_url)


def get_topic_prompt():
    active = db.get_active_prompt("topic_research")
    if active:
        return active["system_prompt"], active["prompt_template"]

    system = """You are a professional researcher who discovers YouTube Shorts topics that US audiences love.
Target audience: Americans aged 18-45 who are hooked on history, unsolved mysteries, true crime, and bizarre coincidences.
Format: 30-second Shorts (about 80 words) with a powerful hook in the first 3 seconds.
CRITICAL: Write every field in ENGLISH only. Never use any other language."""

    template = """Recommend ONE topic from the following categories that US viewers are most likely to love:

Categories:
1. historical_mystery: unsolved historical mysteries, vanished civilizations, bizarre archaeological finds
2. true_crime: bizarre cold cases, strange serial-killer patterns, old cases cracked by forensics
3. coincidence: chilling coincidences, predictive dreams, parallel-universe-like true stories

Selection criteria:
- Subjects that are familiar to or fascinating to Americans
- Must be able to deliver a "whoa" reaction within 30 seconds
- Rich in visually striking imagery
- Clear comment-baiting angle

Recently uploaded topics (avoid duplicates):
{recent_topics}

Patterns shared by top performing videos:
{top_patterns}

Respond with ONLY valid JSON. Every string must be in English:
{
    "topic_title": "specific, concrete topic title in English",
    "category": "historical_mystery|true_crime|coincidence",
    "hook": "one punchy first-3-seconds hook sentence in English",
    "why_viral": "why this topic will go viral, 3 reasons",
    "key_points": ["key point 1", "key point 2", "key point 3", "key point 4"],
    "source_urls": [],
    "estimated_interest_score": 85
}"""
    return system, template


def _normalize_topic_result(data: dict) -> dict:
    """LLM이 스키마와 다르게 반환하는 경우를 보정한다."""
    for key in ("topic_title", "hook", "why_viral"):
        value = data.get(key)
        if isinstance(value, list):
            data[key] = " ".join(str(v).strip() for v in value)
        elif value is None:
            data[key] = ""
        elif isinstance(value, str) and not value.strip().startswith('"'):
            # 키 앞쪽에 개행/들여쓰기가 붙은 경우 보정
            data[key] = value.strip().split("\n")[-1].strip().strip('"').strip()

    key_points = data.get("key_points")
    if isinstance(key_points, str):
        data["key_points"] = [kp.strip() for kp in key_points.split(",") if kp.strip()]
    elif isinstance(key_points, list):
        data["key_points"] = [str(kp).strip() for kp in key_points if str(kp).strip()]
    else:
        data["key_points"] = []

    if not isinstance(data.get("source_urls"), list):
        data["source_urls"] = []

    try:
        score = float(data.get("estimated_interest_score", 75))
    except (TypeError, ValueError):
        score = 75.0
    data["estimated_interest_score"] = min(max(score, 0.0), 100.0)

    category = str(data.get("category", "")).strip().lower()
    if category not in {"historical_mystery", "true_crime", "coincidence"}:
        category = "historical_mystery"
    data["category"] = category
    return data


def research_topic() -> TopicResearchResult:
    recent_videos = db.get_recent_published(limit=10)
    recent_topics = (
        "\n".join(
            [f"- {v['topic_title']} ({v['topic_category']})" for v in recent_videos]
        )
        or "없음"
    )

    top_videos = db.get_top_performers(limit=5, days=30)
    top_patterns = (
        "데이터 부족"
        if not top_videos
        else "\n".join(
            [
                f"- {v['topic_title']}: 조회수 {v.get('total_views', 'N/A')}, 훅: {v.get('hook_text', '')[:50]}..."
                for v in top_videos
            ]
        )
    )

    system, template = get_topic_prompt()
    prompt = template.replace("{recent_topics}", recent_topics).replace(
        "{top_patterns}", top_patterns
    )

    response = client.chat.completions.create(
        model=settings.nvidia_model_fast,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=settings.nvidia_temperature,
        max_tokens=2000,
    )

    result = _normalize_topic_result(
        chat_json(
            client,
            primary_model=settings.nvidia_model_fast,
            fallback_model=settings.nvidia_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            temperature=settings.nvidia_temperature,
            max_tokens=2000,
        )
    )
    return TopicResearchResult(**result)


def generate_multiple_topics(count: int = 3) -> List[TopicResearchResult]:
    topics = []
    for _ in range(count):
        try:
            topics.append(research_topic())
        except Exception as e:
            print(f"주제 생성 실패: {e}")
    return sorted(topics, key=lambda x: x.estimated_interest_score, reverse=True)
