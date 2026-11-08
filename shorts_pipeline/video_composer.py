from .config import settings
from .models import (
    ScriptScene,
    ImageGenerationResult,
    TTSResult,
    VideoCompositionResult,
)
from pathlib import Path
from typing import List
from moviepy.editor import (
    ImageClip,
    AudioFileClip,
    TextClip,
    CompositeVideoClip,
    concatenate_videoclips,
    ColorClip,
    VideoClip,
)
from PIL import Image, ImageDraw, ImageFont
import numpy as np


class VideoComposer:
    def __init__(self):
        self.output_dir = Path(settings.output_dir) / "videos"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.font_path = self._get_font_path()

    def _get_font_path(self) -> str:
        font_dir = Path(settings.fonts_dir)
        for pattern in ["*Noto*Sans*.ttf", "*Noto*Sans*.otf", "*.ttf", "*.otf"]:
            fonts = list(font_dir.glob(pattern))
            if fonts:
                return str(fonts[0])
        return "DejaVu-Sans"

    def compose(
        self,
        scenes: List[ScriptScene],
        images: List[ImageGenerationResult],
        tts: TTSResult,
        video_id: str,
        hook_text: str,
    ) -> VideoCompositionResult:
        video_path = self.output_dir / f"{video_id}.mp4"
        thumbnail_path = self.output_dir / f"{video_id}_thumb.jpg"

        audio_clip = AudioFileClip(tts.audio_path)
        total_duration = audio_clip.duration

        # LLM이 만든 씬 길이를 실제 음성 길이에 맞춰 비율 조정
        raw_total = sum(max(s.duration_seconds, 0.5) for s in scenes) or 1.0
        scale = total_duration / raw_total
        scene_durations = [max(s.duration_seconds, 0.5) * scale for s in scenes]

        clips = []
        for scene, img_result, scene_duration in zip(scenes, images, scene_durations):
            img_clip = self._create_ken_burns_clip(
                img_result.local_path,
                scene_duration,
                zoom_factor=settings.ken_burns_zoom_factor,
            )
            subtitle_clip = self._create_subtitle_clip(
                scene.narration,
                scene_duration,
                video_size=(settings.video_width, settings.video_height),
            )
            composite = CompositeVideoClip(
                [img_clip, subtitle_clip],
                size=(settings.video_width, settings.video_height),
            )
            composite = composite.set_duration(scene_duration)
            clips.append(composite)

        final_video = concatenate_videoclips(clips, method="compose")
        final_video = final_video.set_audio(audio_clip)

        self._create_thumbnail(
            images[0].local_path, scenes[0].narration[:50], thumbnail_path
        )

        final_video.write_videofile(
            str(video_path),
            fps=settings.video_fps,
            codec="libx264",
            audio_codec="aac",
            bitrate="5000k",
            threads=4,
            preset="medium",
            logger=None,
        )

        file_size_mb = video_path.stat().st_size / (1024 * 1024)

        return VideoCompositionResult(
            video_path=str(video_path),
            thumbnail_path=str(thumbnail_path),
            duration_seconds=total_duration,
            file_size_mb=round(file_size_mb, 2),
        )

    def _create_ken_burns_clip(
        self, image_path: str, duration: float, zoom_factor: float = 1.15
    ):
        img = Image.open(image_path)
        img_w, img_h = img.size
        target_w, target_h = settings.video_width, settings.video_height
        target_ratio = target_w / target_h
        img_ratio = img_w / img_h

        if img_ratio > target_ratio:
            new_h = target_h
            new_w = int(img_ratio * new_h)
        else:
            new_w = target_w
            new_h = int(new_w / img_ratio)

        img = img.resize((new_w, new_h), Image.LANCZOS)
        zoom_w = int(target_w * zoom_factor)
        zoom_h = int(target_h * zoom_factor)
        img_zoomed = img.resize((zoom_w, zoom_h), Image.LANCZOS)

        # 메모리 절약: 프레임을 미리 만들지 않고 요청 시점에 계산
        def make_frame(t):
            progress = min(max(t / max(duration, 0.001), 0.0), 1.0)
            eased = progress * progress * (3 - 2 * progress)
            x = int((zoom_w - target_w) * eased * 0.5)
            y = int((zoom_h - target_h) * eased * 0.3)
            frame = img_zoomed.crop((x, y, x + target_w, y + target_h))
            return np.array(frame)

        clip = VideoClip(make_frame, duration=duration)
        return clip

    def _create_subtitle_clip(
        self, text: str, duration: float, video_size: tuple
    ) -> TextClip:
        wrapped = self._wrap_text(text, max_chars_per_line=28)

        txt_clip = TextClip(
            wrapped,
            fontsize=settings.subtitle_font_size,
            color=settings.subtitle_color,
            font=self.font_path,
            stroke_color=settings.subtitle_stroke_color,
            stroke_width=settings.subtitle_stroke_width,
            method="caption",
            size=(video_size[0] - 100, None),
            align="center",
        )
        txt_clip = txt_clip.set_position(("center", video_size[1] - 150 - txt_clip.h))
        txt_clip = txt_clip.set_duration(duration)

        bg_clip = ColorClip(
            size=(txt_clip.w + 40, txt_clip.h + 20), color=(0, 0, 0), duration=duration
        ).set_opacity(0.6)
        bg_clip = bg_clip.set_position(
            ("center", video_size[1] - 150 - txt_clip.h - 10)
        )

        return CompositeVideoClip([bg_clip, txt_clip])

    def _wrap_text(self, text: str, max_chars_per_line: int = 28) -> str:
        words = text.split()
        lines = []
        current = []
        current_len = 0

        for word in words:
            if current_len + len(word) + 1 > max_chars_per_line:
                lines.append(" ".join(current))
                current = [word]
                current_len = len(word)
            else:
                current.append(word)
                current_len += len(word) + 1
        if current:
            lines.append(" ".join(current))

        return "\n".join(lines)

    def _create_thumbnail(self, image_path: str, title_text: str, output_path: Path):
        img = Image.open(image_path).resize(
            (settings.video_width, settings.video_height), Image.LANCZOS
        )
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 120))
        img = img.convert("RGBA")
        img = Image.alpha_composite(img, overlay)

        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype(self.font_path, 72)
        except Exception:
            font = ImageFont.load_default()

        wrapped = self._wrap_text(title_text, max_chars_per_line=18)
        bbox = draw.multiline_textbbox(
            (0, 0),
            wrapped,
            font=font,
            align="center",
            stroke_width=3,
            stroke_fill="black",
        )
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (img.width - text_w) // 2
        y = (img.height - text_h) // 2

        draw.multiline_text(
            (x, y),
            wrapped,
            font=font,
            fill="white",
            align="center",
            stroke_width=3,
            stroke_fill="black",
        )
        img.convert("RGB").save(output_path, quality=95)


video_composer = VideoComposer()
