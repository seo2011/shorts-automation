"""LLM 호출 유틸리티.

전략: 추론(reasoning)은 최대한 켜둔다. 응답이 비어 있거나 JSON 파싱이 실패할 때만
단계적으로 추론을 끄거나 다른 모델로 전환한다.
"""

from typing import Any, Dict, List, Optional

from .utils import parse_json_response


class LLMError(RuntimeError):
    pass


def chat_json(
    client,
    primary_model: str,
    fallback_model: Optional[str],
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 2000,
) -> Dict[str, Any]:
    """JSON을 반환하는 채팅 호출. 실패 단계:

    1. primary + 추론 ON (max_tokens)
    2. primary + 추론 ON (max_tokens x2, 출력 잘림 대비)
    3. primary + 추론 OFF (max_tokens)
    4. fallback + 추론 ON (max_tokens x2)
    5. fallback + 추론 OFF (max_tokens)
    """
    plans = [
        (primary_model, max_tokens, True),
        (primary_model, max_tokens * 2, True),
        (primary_model, max_tokens, False),
    ]
    if fallback_model and fallback_model != primary_model:
        plans += [
            (fallback_model, max_tokens * 2, True),
            (fallback_model, max_tokens, False),
        ]

    last_error: Optional[Exception] = None
    for model, tokens, thinking in plans:
        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": tokens,
        }
        if not thinking:
            kwargs["extra_body"] = {"chat_template_kwargs": {"enable_thinking": False}}

        mode = "reasoning ON" if thinking else "reasoning OFF"
        try:
            response = client.chat.completions.create(**kwargs)
            content = (response.choices[0].message.content or "").strip()
            if not content:
                last_error = ValueError(f"{model} ({mode}): empty response")
                print(f"  [llm] {last_error} -> 다음 시도")
                continue
            result = parse_json_response(content)
            print(f"  [llm] 성공: {model} ({mode}, max_tokens={tokens})")
            return result
        except Exception as e:
            last_error = e
            print(f"  [llm] 실패 {model} ({mode}): {e} -> 다음 시도")
            continue

    raise LLMError(f"모든 LLM 시도 실패: {last_error}")
