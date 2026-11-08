from .config import settings
from .models import ScriptScene, TTSResult
from pathlib import Path
from typing import List
import asyncio
import json
import subprocess

import edge_tts


class TTSGenerator:
    """Edge TTS 기반 음성 생성기.

    - 모델 다운로드 불필요 (수 초 내 생성)
    - WordBoundary 이벤트로 단어별 타임스탬프 확보
    """

    def __init__(self):
        self.voice = settings.tts_voice
        self.rate = settings.tts_rate
        self.output_dir = Path(settings.output_dir) / "audio"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_for_script(
        self, scenes: List[ScriptScene], video_id: str
    ) -> TTSResult:
        full_text = " ".join([s.narration for s in scenes]).strip()
        output_path = self.output_dir / f"{video_id}_narration.mp3"

        word_boundaries = []

        async def _run():
            communicate = edge_tts.Communicate(
                full_text,
                self.voice,
                rate=self.rate,
                boundary="WordBoundary",
            )
            with open(output_path, "wb") as f:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        f.write(chunk["data"])
                    elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                        start = chunk["offset"] / 10_000_000
                        end = (chunk["offset"] + chunk["duration"]) / 10_000_000
                        word_boundaries.append(
                            {"word": chunk["text"], "start": start, "end": end}
                        )

        asyncio.run(_run())

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError("Edge TTS 음성 생성 실패 (빈 파일)")

        duration = self._get_audio_duration(output_path, word_boundaries)

        return TTSResult(
            audio_path=str(output_path),
            duration_seconds=duration,
            word_timestamps=word_boundaries,
        )

    def _get_audio_duration(self, path: Path, boundaries: List[dict]) -> float:
        # ffprobe 우선, 실패 시 WordBoundary 마지막 시점 사용
        try:
            out = subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "quiet",
                    "-print_format",
                    "json",
                    "-show_format",
                    str(path),
                ],
                stderr=subprocess.DEVNULL,
                timeout=30,
            )
            data = json.loads(out)
            return float(data["format"]["duration"])
        except Exception:
            if boundaries:
                return float(boundaries[-1]["end"]) + 0.2
            return 0.0


tts_generator = TTSGenerator()
