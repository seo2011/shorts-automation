from typing import List
from .config import settings
from .models import TopicResearchResult, TopicCategory
from .database import db
from openai import OpenAI
import json

client = OpenAI(api_key=settings.nvidia_api_key, base_url=settings.nvidia_base_url)


def get_topic_prompt():
    active = db.get_active_prompt("topic_research")
    if active:
        return active["system_prompt"], active["prompt_template"]

    system = """당신은 미국 시청자들이 열광하는 쇼츠 주제를 발굴하는 전문 리서처입니다.
대상: 미국 18-45세, 역사/미스터리/실화 범죄/기묘한 우연에 관심 많은 층
포맷: 30초 쇼츠 (약 80단어 내외), 강렬한 훅 필수"""

    template = """다음 카테고리 중 하나에서 **미국인들이 가장 좋아할 만한** 주제 1개를 추천하세요:

카테고리:
1. historical_mystery: 해결되지 않은 역사적 미스터리, 사라진 문명, 기묘한 고고학적 발견
2. true_crime: 기묘한 미제 사건, 연쇄살인마의 기이한 패턴, 법의학으로 풀린 오래된 사건
3. coincidence: 소름 돋는 우연의 일치, 예언적 꿈, 평행우주 같은 실화

선정 기준:
- 미국인들에게 친숙하거나 관심이 높은 소재
- 30초 안에 "와..." 소리가 나오게 전달 가능
- 시각적으로 흥미로운 이미지 소재가 많음
- 댓글 유도 포인트 명확

최근 업로드한 주제들 (중복 피함):
{recent_topics}

상위 성과 영상들의 공통 패턴:
{top_patterns}

JSON으로만 응답하세요:
{
    "topic_title": "구체적 주제명",
    "category": "historical_mystery|true_crime|coincidence",
    "hook": "첫 3초 훅 문장",
    "why_viral": "이 주제가 바이럴 될 이유 3가지",
    "key_points": ["핵심 포인트 1", "핵심 포인트 2", "핵심 포인트 3", "핵심 포인트 4"],
    "source_urls": [],
    "estimated_interest_score": 85
}"""
    return system, template


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
    prompt = template.format(recent_topics=recent_topics, top_patterns=top_patterns)

    response = client.chat.completions.create(
        model=settings.nvidia_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=settings.nvidia_temperature,
        max_tokens=1000,
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)
    return TopicResearchResult(**result)


def generate_multiple_topics(count: int = 3) -> List[TopicResearchResult]:
    topics = []
    for _ in range(count):
        try:
            topics.append(research_topic())
        except Exception as e:
            print(f"주제 생성 실패: {e}")
    return sorted(topics, key=lambda x: x.estimated_interest_score, reverse=True)
