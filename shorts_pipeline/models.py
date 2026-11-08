from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


class TopicCategory(str, Enum):
    HISTORICAL_MYSTERY = "historical_mystery"
    TRUE_CRIME = "true_crime"
    COINCIDENCE = "coincidence"


class VideoStatus(str, Enum):
    DRAFT = "draft"
    RESEARCHING = "researching"
    SCRIPTING = "scripting"
    GENERATING_IMAGES = "generating_images"
    GENERATING_TTS = "generating_tts"
    COMPOSING_VIDEO = "composing_video"
    UPLOADING = "uploading"
    PUBLISHED = "published"
    FAILED = "failed"


class TopicResearchResult(BaseModel):
    topic_title: str
    category: TopicCategory = TopicCategory.HISTORICAL_MYSTERY
    hook: str = ""
    why_viral: str = ""
    key_points: List[str] = []
    source_urls: List[str] = []
    estimated_interest_score: float = Field(default=75.0, ge=0, le=100)


class ScriptScene(BaseModel):
    scene_number: int = 1
    narration: str
    image_prompt: str = "cinematic vertical scene, dramatic lighting"
    duration_seconds: float = 3.75
    visual_description: str = ""


class ScriptResult(BaseModel):
    title: str
    scenes: List[ScriptScene]
    description: str = ""
    tags: List[str] = []
    hook_text: str = ""
    total_duration: float = 30.0
    total_words: int = 0
    hashtags: List[str] = []


class ImageGenerationResult(BaseModel):
    scene_number: int
    image_url: str
    local_path: Optional[str] = None
    prompt_used: str
    revised_prompt: Optional[str] = None


class TTSResult(BaseModel):
    audio_path: str
    duration_seconds: float
    word_timestamps: List[Dict[str, Any]]


class VideoCompositionResult(BaseModel):
    video_path: str
    thumbnail_path: str
    duration_seconds: float
    file_size_mb: float


class UploadResult(BaseModel):
    youtube_id: str
    url: str
    status: str


class PipelineRunResult(BaseModel):
    run_id: str
    video_id: Optional[str] = None
    status: str
    steps_completed: List[str]
    error_step: Optional[str] = None
    error_details: Optional[str] = None
    duration_seconds: float
    started_at: datetime
    completed_at: datetime


class VideoMetricsSnapshot(BaseModel):
    video_id: str
    date: str
    views: int
    likes: int
    comments: int
    shares: int
    subscribers_gained: int
    avg_view_duration: float
    retention_graph: Dict[str, float]
    ctr: float
    impressions: int
    traffic_sources: Dict[str, float]
