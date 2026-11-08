from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Supabase
    supabase_url: str = Field(..., validation_alias="SUPABASE_URL")
    supabase_service_key: str = Field(..., validation_alias="SUPABASE_SERVICE_KEY")

    # NVIDIA NGC (OpenAI 호환)
    nvidia_api_key: str = Field(..., validation_alias="NVIDIA_API_KEY")
    nvidia_base_url: str = Field(
        default="https://integrate.api.nvidia.com/v1",
        validation_alias="NVIDIA_BASE_URL",
    )
    nvidia_model: str = Field(
        default="meta/llama-3.1-70b-instruct", validation_alias="NVIDIA_MODEL"
    )
    nvidia_temperature: float = Field(
        default=0.7, validation_alias="NVIDIA_TEMPERATURE"
    )

    # Image Generation
    replicate_api_token: Optional[str] = Field(
        default=None, validation_alias="REPLICATE_API_TOKEN"
    )
    sdxl_api_url: Optional[str] = Field(default=None, validation_alias="SDXL_API_URL")

    # YouTube
    youtube_client_id: str = Field(..., validation_alias="YOUTUBE_CLIENT_ID")
    youtube_client_secret: str = Field(..., validation_alias="YOUTUBE_CLIENT_SECRET")
    youtube_refresh_token: str = Field(..., validation_alias="YOUTUBE_REFRESH_TOKEN")
    youtube_channel_id: Optional[str] = Field(
        default=None, validation_alias="YOUTUBE_CHANNEL_ID"
    )

    # Telegram
    telegram_bot_token: Optional[str] = Field(
        default=None, validation_alias="TELEGRAM_BOT_TOKEN"
    )
    telegram_chat_id: Optional[str] = Field(
        default=None, validation_alias="TELEGRAM_CHAT_ID"
    )

    # Paths
    data_dir: str = Field(default="data")
    assets_dir: str = Field(default="assets")
    logs_dir: str = Field(default="logs")
    speakers_dir: str = Field(default="data/speakers")
    fonts_dir: str = Field(default="assets/fonts")
    output_dir: str = Field(default="output")

    # Pipeline Settings
    target_duration_seconds: int = Field(default=30)
    images_per_video: int = Field(default=8)
    words_per_minute: int = Field(default=160)
    max_script_words: int = Field(default=80)

    # TTS Settings
    tts_language: str = Field(default="en")
    tts_speaker_wav: str = Field(default="data/speakers/reference_en.wav")
    tts_speed: float = Field(default=1.0)

    # Video Composition
    video_width: int = Field(default=1080)
    video_height: int = Field(default=1920)
    video_fps: int = Field(default=30)
    ken_burns_zoom_factor: float = Field(default=1.15)
    subtitle_font_size: int = Field(default=48)
    subtitle_color: str = Field(default="white")
    subtitle_stroke_color: str = Field(default="black")
    subtitle_stroke_width: int = Field(default=3)

    # Scheduling (UTC 기준)
    upload_hour_utc: int = Field(default=15)
    upload_minute_utc: int = Field(default=0)

    # Analysis
    min_performance_score: float = Field(default=50.0)
    top_performers_count: int = Field(default=5)


settings = Settings()

for path in [
    settings.data_dir,
    settings.assets_dir,
    settings.logs_dir,
    settings.speakers_dir,
    settings.fonts_dir,
    settings.output_dir,
]:
    os.makedirs(path, exist_ok=True)
