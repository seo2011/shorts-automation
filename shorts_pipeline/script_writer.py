from typing import List
from .config import settings
from .models import TopicResearchResult, ScriptResult, ScriptScene, TopicCategory
from .database import db
from .llm import chat_json
from .utils import parse_json_response
from openai import OpenAI
import json

client = OpenAI(api_key=settings.nvidia_api_key, base_url=settings.nvidia_base_url)


def get_script_prompt(category: TopicCategory):
    active = db.get_active_prompt("script_writer")
    if active:
        return active["system_prompt"], active["prompt_template"]

    base_system = """You are a 30-second YouTube Shorts scriptwriter for a US audience.
Strong hooks, fast pacing, and a clear payoff.
CRITICAL: Write the title, description, tags, hashtags, hook and ALL narration in ENGLISH only. Never use any other language.
Also write every "image_prompt" in English (it is fed to an AI image model)."""

    category_instructions = {
        TopicCategory.HISTORICAL_MYSTERY: """
        Structure: hook (3s) -> setup (5s) -> list of strange facts (15s) -> unresolved mystery (7s)
        Tone: mysterious, intellectually curious
        """,
        TopicCategory.TRUE_CRIME: """
        Structure: hook (3s) -> case overview (5s) -> strange pattern/clues (15s) -> current status (7s)
        Tone: tense, chilling
        """,
        TopicCategory.COINCIDENCE: """
        Structure: hook (3s) -> first coincidence (7s) -> second/third coincidence (13s) -> probability/meaning (7s)
        Tone: astonishing, mind-blowing
        """,
    }

    template = f"""Topic: {{topic_title}}
Category: {{category}}
Hook: {{hook}}
Key points: {{key_points}}

Write a 30-second Shorts script with these constraints:
- Total narration: {settings.max_script_words} words or fewer
- Number of scenes: {settings.images_per_video}
- Each scene contains: narration, image_prompt, duration_seconds
- The very first sentence of scene 1 IS the hook
- The last sentence asks the viewer to comment, subscribe, or share
- Narration must be natural spoken English, short and punchy sentences
- image_prompt must describe a vertical 9:16 cinematic still, no text in the image

Respond with ONLY valid JSON. Every string must be in English:
{{
    "title": "Shorts title in English (about 50 characters, click-worthy)",
    "description": "description text in English with hashtags (about 200 characters)",
    "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
    "hashtags": ["#Shorts", "#History", "#Mystery"],
    "hook_text": "final hook sentence in English",
    "scenes": [
        {{
            "scene_number": 1,
            "narration": "narration text in English",
            "image_prompt": "English prompt for an AI image model, vertical cinematic composition",
            "duration_seconds": 3.5,
            "visual_description": "what the viewer sees on screen"
        }}
    ],
    "total_duration": 30.0,
    "total_words": 75
}}"""

    system = base_system + category_instructions.get(category, "")
    return system, template


def _normalize_script_result(data: dict) -> dict:
    """LLM 대본 출력의 누락/형식 오류를 보정한다."""
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("대본에 scenes 배열이 없습니다")

    normalized_scenes = []
    for idx, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            continue
        narration = scene.get("narration") or scene.get("text") or ""
        if isinstance(narration, list):
            narration = " ".join(str(x) for x in narration)
        if not str(narration).strip():
            continue

        image_prompt = (
            scene.get("image_prompt")
            or scene.get("visual")
            or "cinematic vertical scene, dramatic lighting"
        )
        if isinstance(image_prompt, list):
            image_prompt = ", ".join(str(x) for x in image_prompt)

        try:
            duration = float(scene.get("duration_seconds", 3.75))
        except (TypeError, ValueError):
            duration = 3.75

        normalized_scenes.append(
            {
                "scene_number": idx,
                "narration": str(narration).strip(),
                "image_prompt": str(image_prompt),
                "duration_seconds": max(duration, 0.5),
                "visual_description": str(scene.get("visual_description") or ""),
            }
        )

    if not normalized_scenes:
        raise ValueError("유효한 씬이 없습니다")

    data["scenes"] = normalized_scenes
    data["title"] = str(data.get("title") or "Untitled Mystery")

    for key in ("description", "hook_text"):
        value = data.get(key, "")
        if isinstance(value, list):
            value = " ".join(str(v) for v in value)
        data[key] = str(value or "")

    for key in ("tags", "hashtags"):
        value = data.get(key)
        if isinstance(value, str):
            data[key] = [value]
        elif isinstance(value, list):
            data[key] = [str(v) for v in value]
        else:
            data[key] = []

    total_words = data.get("total_words")
    if not isinstance(total_words, (int, float)) or total_words <= 0:
        total_words = sum(len(s["narration"].split()) for s in normalized_scenes)
    data["total_words"] = int(total_words)

    total_duration = data.get("total_duration")
    if not isinstance(total_duration, (int, float)) or total_duration <= 0:
        total_duration = sum(s["duration_seconds"] for s in normalized_scenes)
    data["total_duration"] = float(total_duration)

    if not data["hook_text"]:
        data["hook_text"] = normalized_scenes[0]["narration"][:100]

    return data


def write_script(topic: TopicResearchResult) -> ScriptResult:
    system, template = get_script_prompt(topic.category)
    prompt = (
        template.replace("{topic_title}", topic.topic_title)
        .replace("{category}", topic.category.value)
        .replace("{hook}", topic.hook)
        .replace("{key_points}", ", ".join(topic.key_points))
    )

    response = client.chat.completions.create(
        model=settings.nvidia_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=settings.nvidia_temperature,
        max_tokens=4000,
    )

    result = _normalize_script_result(
        chat_json(
            client,
            primary_model=settings.nvidia_model,
            fallback_model=settings.nvidia_model_fast,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            temperature=settings.nvidia_temperature,
            max_tokens=4000,
        )
    )
    scenes = [ScriptScene(**s) for s in result["scenes"]]
    result["scenes"] = scenes
    return ScriptResult(**result)
