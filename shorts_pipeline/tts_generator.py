from .config import settings
from .models import ScriptScene, TTSResult
from pathlib import Path
import torch
import torchaudio
from TTS.api import TTS
from typing import List, Dict, Any


class TTSGenerator:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"TTS device: {self.device}")

        self.tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(self.device)

        self.speaker_wav = Path(settings.tts_speaker_wav)
        if not self.speaker_wav.exists():
            print(f"참조 화자 파일 없음: {self.speaker_wav}, 기본 화자 사용")
            self.speaker_wav = None

        self.output_dir = Path(settings.output_dir) / "audio"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_for_script(
        self, scenes: List[ScriptScene], video_id: str
    ) -> TTSResult:
        full_text = " ".join([s.narration for s in scenes])
        output_path = self.output_dir / f"{video_id}_narration.wav"

        if self.speaker_wav:
            self.tts.tts_to_file(
                text=full_text,
                file_path=str(output_path),
                speaker_wav=str(self.speaker_wav),
                language=settings.tts_language,
                speed=settings.tts_speed,
            )
        else:
            self.tts.tts_to_file(
                text=full_text,
                file_path=str(output_path),
                language=settings.tts_language,
                speed=settings.tts_speed,
            )

        duration = self._get_audio_duration(output_path)
        words = full_text.split()
        word_duration = duration / len(words) if words else 0

        timestamps = []
        current_time = 0.0
        for word in words:
            timestamps.append(
                {
                    "word": word,
                    "start": round(current_time, 3),
                    "end": round(current_time + word_duration, 3),
                }
            )
            current_time += word_duration

        return TTSResult(
            audio_path=str(output_path),
            duration_seconds=duration,
            word_timestamps=timestamps,
        )

    def _get_audio_duration(self, path: Path) -> float:
        info = torchaudio.info(str(path))
        return info.num_frames / info.sample_rate


tts_generator = TTSGenerator()
