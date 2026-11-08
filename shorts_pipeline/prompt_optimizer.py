from .config import settings
from .database import db
from .llm import chat_json
from .performance_analyzer import performance_analyzer
from .utils import parse_json_response
from openai import OpenAI
import json

client = OpenAI(api_key=settings.nvidia_api_key, base_url=settings.nvidia_base_url)


class PromptOptimizer:
    def __init__(self):
        self.components = [
            "topic_research",
            "script_writer",
            "hook_generator",
            "title_generator",
        ]

    def run_optimization_cycle(self):
        top_videos = performance_analyzer.analyze_top_performers(
            limit=settings.top_performers_count, days=30
        )

        if len(top_videos) < 3:
            print("분석할 데이터 부족 (최소 3개 영상 필요)")
            return

        for component in self.components:
            self._optimize_component(component, top_videos)

    def _optimize_component(self, component: str, top_videos: list):
        active = db.get_active_prompt(component)
        if not active:
            return

        current_prompt = active["prompt_template"]
        current_version = active["version"]

        examples = self._extract_examples(component, top_videos)

        system = f"""당신은 프롬프트 엔지니어입니다. 현재 {component} 프롬프트를 분석하고,
상위 성과 영상들의 패턴을 반영해 개선된 버전을 작성하세요."""

        prompt = f"""현재 프롬프트 (v{current_version}):
{current_prompt}

상위 {len(top_videos)}개 영상의 {component} 산출물 패턴:
{json.dumps(examples, ensure_ascii=False, indent=2)}

개선된 프롬프트 템플릿을 JSON으로만 응답:
{{
    "prompt_template": "개선된 템플릿 ({{변수}} 플레이스홀더 유지)",
    "system_prompt": "개선된 시스템 프롬프트",
    "temperature": 0.7,
    "notes": "주요 변경사항 요약"
}}"""

        try:
            result = chat_json(
                client,
                primary_model=settings.nvidia_model,
                fallback_model=settings.nvidia_model_fast,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=2000,
            )
            new_version = current_version + 1
            prompt_id = db.create_prompt_version(
                component=component,
                prompt_template=result["prompt_template"],
                system_prompt=result["system_prompt"],
                model_name=settings.nvidia_model,
                temperature=result.get("temperature", settings.nvidia_temperature),
                version=new_version,
                notes=result.get("notes", ""),
            )
            print(f"[{component}] v{new_version} 생성됨: {prompt_id}")
            print(f"  변경사항: {result.get('notes')}")

        except Exception as e:
            print(f"[{component}] 프롬프트 최적화 실패: {e}")

    def _extract_examples(self, component: str, top_videos: list) -> dict:
        examples = {"hooks": [], "structures": [], "titles": [], "topics": []}

        for v in top_videos:
            if component == "topic_research":
                examples["topics"].append(
                    {
                        "title": v.get("topic_title"),
                        "category": v.get("topic_category"),
                        "hook": v.get("hook_text"),
                        "score": v.get("performance_score", 0),
                    }
                )
            elif component == "script_writer":
                structure = v.get("structure_json", {})
                examples["structures"].append(
                    {
                        "scene_count": len(structure.get("scenes", [])),
                        "hook": v.get("hook_text"),
                    }
                )
            elif component == "hook_generator":
                examples["hooks"].append(v.get("hook_text"))
            elif component == "title_generator":
                examples["titles"].append(v.get("title"))

        return examples


prompt_optimizer = PromptOptimizer()
