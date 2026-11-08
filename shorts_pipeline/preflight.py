"""실행 전 자격증명/연결 점검.

실패해도 파이프라인 로그에 원인이 명확히 남도록 각 항목을 개별적으로 검사한다.
"""

import sys

from shorts_pipeline.config import settings


def main() -> int:
    ok = True

    print("===== 1. Supabase =====")
    try:
        from shorts_pipeline.database import db

        for table in ("videos", "video_metrics", "prompt_versions", "pipeline_runs"):
            res = db.client.table(table).select("*").limit(1).execute()
            rows = res.data or []
            print(f"  {table}: OK (sample rows={len(rows)})")
    except Exception as e:
        ok = False
        print(f"  FAILED: {type(e).__name__}: {e}")
        print(
            "  → Supabase SQL Editor에서 supabase_schema.sql을 실행했는지 확인하세요."
        )

    print("===== 2. NVIDIA LLM =====")
    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=settings.nvidia_api_key,
            base_url=settings.nvidia_base_url,
            timeout=90,
            max_retries=1,
        )
        for label, model in (
            ("main", settings.nvidia_model),
            ("fast", settings.nvidia_model_fast),
        ):
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": "Reply with the single word OK."}
                ],
                max_tokens=50,
                temperature=0,
            )
            text = (resp.choices[0].message.content or "").strip()
            print(f"  {label} ({model}): OK, response={text[:30]!r}")
    except Exception as e:
        ok = False
        print(f"  FAILED: {type(e).__name__}: {e}")

    print("===== 3. YouTube OAuth =====")
    try:
        from google.auth.transport.requests import Request
        from shorts_pipeline.youtube_uploader import youtube_uploader

        youtube_uploader.credentials.refresh(Request())
        print("  access token: OK")
    except Exception as e:
        ok = False
        print(f"  FAILED: {type(e).__name__}: {e}")

    print("===== 4. Edge TTS =====")
    try:
        import edge_tts

        print(f"  edge-tts version: {getattr(edge_tts, '__version__', 'unknown')}")
        print(f"  voice: {settings.tts_voice}, rate: {settings.tts_rate}")
    except Exception as e:
        ok = False
        print(f"  FAILED: {type(e).__name__}: {e}")

    print("===== PREFLIGHT RESULT:", "OK" if ok else "FAILED", "=====")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
