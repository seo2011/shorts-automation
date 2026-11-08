import json
import re
from typing import Any, Dict


def parse_json_response(text: str) -> Dict[str, Any]:
    """LLM 응답에서 JSON 객체를 안정적으로 추출한다.

    - ```json ... ``` 코드펜스 제거
    - 앞뒤 설명 문장이 섞여 있어도 첫 JSON 객체만 추출
    """
    if not text:
        raise ValueError("빈 응답")

    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.S)
        if match:
            return json.loads(match.group(0))
        raise
