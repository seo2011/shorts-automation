from typing import List
from .config import settings
from .models import TopicResearchResult, ScriptResult, ScriptScene, TopicCategory
from .database import db
from .utils import parse_json_response
from openai import OpenAI
import json

client = OpenAI(api_key=settings.nvidia_api_key, base_url=settings.nvidia_base_url)


def get_script_prompt(category: TopicCategory):
    active = db.get_active_prompt("script_writer")
    if active:
        return active["system_prompt"], active["prompt_template"]

    base_system = """당신은 30초 쇼츠 대본 작가입니다. 미국 시청자 대상, 강렬한 훅과 빠른 템포 필수."""

    category_instructions = {
        TopicCategory.HISTORICAL_MYSTERY: """
        구조: 훅(3초) → 배경 설정(5초) → 기묘한 사실 나열(15초) → 미해결 미스터리/여운(7초)
        톤: 신비로움, 지적 호기심 자극
        """,
        TopicCategory.TRUE_CRIME: """
        구조: 훅(3초) → 사건 개요(5초) → 기이한 패턴/단서(15초) → 현재 상황/미제 여부(7초)
        톤: 긴장감, 소름
        """,
        TopicCategory.COINCIDENCE: """
        구조: 훅(3초) → 첫 번째 우연(7초) → 두 번째/세 번째 우연(13초) → 확률/해석(7초)
        톤: 경이로움, 충격
        """,
    }

    template = f"""주제: {{topic_title}}
카테고리: {{category}}
훅: {{hook}}
핵심 포인트: {{key_points}}

다음 제약으로 30초 쇼츠 대본을 작성하세요:
- 총 단어 수: {settings.max_script_words}단어 이하
- 씬 수: {settings.images_per_video}개
- 각 씬: 나레이션 + 이미지 프롬프트 + 지속시간
- 첫 문장 = 훅
- 마지막 문장: 시청자 행동 유도 (댓글, 구독, 공유 중 1개)

JSON으로만 응답:
{{
    "title": "쇼츠 제목 (50자 내외, 클릭 유도)",
    "description": "설명란 텍스트 (해시태그 포함, 200자 내외)",
    "tags": ["태그1", "태그2", "태그3", "태그4", "태그5"],
    "hashtags": ["#Shorts", "#History", "#Mystery"],
    "hook_text": "최종 훅 문장",
    "scenes": [
        {{
            "scene_number": 1,
            "narration": "나레이션 텍스트",
            "image_prompt": "Stable Diffusion용 영어 프롬프트",
            "duration_seconds": 3.5,
            "visual_description": "화면 구성 설명"
        }}
    ],
    "total_duration": 30.0,
    "total_words": 75
}}"""

    system = base_system + category_instructions.get(category, "")
    return system, template


def write_script(topic: TopicResearchResult) -> ScriptResult:
    system, template = get_script_prompt(topic.category)
    prompt = template.format(
        topic_title=topic.topic_title,
        category=topic.category.value,
        hook=topic.hook,
        key_points=", ".join(topic.key_points),
    )

    response = client.chat.completions.create(
        model=settings.nvidia_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=settings.nvidia_temperature,
        max_tokens=1500,
    )

    result = parse_json_response(response.choices[0].message.content)
    scenes = [ScriptScene(**s) for s in result["scenes"]]
    result["scenes"] = scenes
    return ScriptResult(**result)
