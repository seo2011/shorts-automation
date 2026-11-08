from supabase import create_client, Client
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
import uuid
from .config import settings
from .models import (
    TopicCategory,
    VideoStatus,
    TopicResearchResult,
    ScriptResult,
    ScriptScene,
    ImageGenerationResult,
    TTSResult,
    VideoCompositionResult,
    UploadResult,
    PipelineRunResult,
    VideoMetricsSnapshot,
)


class Database:
    def __init__(self):
        self.client: Client = create_client(
            settings.supabase_url, settings.supabase_service_key
        )

    # ===== Videos =====
    def create_video(self, topic: TopicResearchResult, script: ScriptResult) -> str:
        video_id = str(uuid.uuid4())
        data = {
            "id": video_id,
            "title": script.title,
            "description": script.description,
            "tags": script.tags,
            "topic_category": topic.category.value,
            "topic_title": topic.topic_title,
            "script_text": "\n".join([s.narration for s in script.scenes]),
            "hook_text": script.hook_text,
            "structure_json": {
                "scenes": [s.model_dump() for s in script.scenes],
                "hashtags": script.hashtags,
            },
            "duration_seconds": int(script.total_duration),
            "status": VideoStatus.DRAFT.value,
            "scheduled_at": datetime.utcnow().isoformat(),
        }
        self.client.table("videos").insert(data).execute()
        return video_id

    def update_video_status(self, video_id: str, status: VideoStatus, **kwargs):
        data = {"status": status.value, "updated_at": datetime.utcnow().isoformat()}
        data.update(kwargs)
        self.client.table("videos").update(data).eq("id", video_id).execute()

    def update_video_youtube_id(
        self, video_id: str, youtube_id: str, published_at: datetime
    ):
        self.client.table("videos").update(
            {
                "youtube_id": youtube_id,
                "status": VideoStatus.PUBLISHED.value,
                "published_at": published_at.isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
        ).eq("id", video_id).execute()

    def update_video_paths(self, video_id: str, video_path: str, thumbnail_path: str):
        self.client.table("videos").update(
            {
                "video_path": video_path,
                "thumbnail_path": thumbnail_path,
                "updated_at": datetime.utcnow().isoformat(),
            }
        ).eq("id", video_id).execute()

    def get_video(self, video_id: str) -> Optional[Dict]:
        try:
            res = (
                self.client.table("videos")
                .select("*")
                .eq("id", video_id)
                .maybe_single()
                .execute()
            )
            return res.data if res and res.data else None
        except Exception:
            return None

    def get_recent_published(self, limit: int = 20) -> List[Dict]:
        res = (
            self.client.table("videos")
            .select("*")
            .eq("status", VideoStatus.PUBLISHED.value)
            .order("published_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []

    def get_top_performers(self, limit: int = 5, days: int = 30) -> List[Dict]:
        """최근 N일간 조회수 합계 기준 상위 영상 (RPC 없이 조회)"""
        since = (datetime.utcnow() - timedelta(days=days)).date().isoformat()
        videos = (
            self.client.table("videos")
            .select(
                "id,title,topic_title,topic_category,hook_text,youtube_id,published_at"
            )
            .eq("status", VideoStatus.PUBLISHED.value)
            .execute()
        ).data or []

        results = []
        for v in videos:
            metrics = (
                self.client.table("video_metrics")
                .select("views")
                .eq("video_id", v["id"])
                .gte("date", since)
                .execute()
            ).data or []
            total_views = sum(int(m.get("views") or 0) for m in metrics)
            v["total_views"] = total_views
            results.append(v)

        results.sort(key=lambda x: x.get("total_views", 0), reverse=True)
        return results[:limit]

    # ===== Metrics =====
    def upsert_metrics(self, metrics: VideoMetricsSnapshot):
        data = {
            "video_id": metrics.video_id,
            "date": metrics.date,
            "views": metrics.views,
            "likes": metrics.likes,
            "comments": metrics.comments,
            "shares": metrics.shares,
            "subscribers_gained": metrics.subscribers_gained,
            "avg_view_duration_seconds": metrics.avg_view_duration,
            "retention_graph": metrics.retention_graph,
            "ctr": metrics.ctr,
            "impression_count": metrics.impressions,
            "traffic_sources": metrics.traffic_sources,
        }
        self.client.table("video_metrics").upsert(
            data, on_conflict="video_id,date"
        ).execute()

    def get_metrics_for_video(self, video_id: str, days: int = 30) -> List[Dict]:
        since = (date.today() - timedelta(days=days)).isoformat()
        res = (
            self.client.table("video_metrics")
            .select("*")
            .eq("video_id", video_id)
            .gte("date", since)
            .order("date")
            .execute()
        )
        return res.data or []

    # ===== Prompt Versions =====
    def get_active_prompt(self, component: str) -> Optional[Dict]:
        try:
            res = (
                self.client.table("prompt_versions")
                .select("*")
                .eq("component", component)
                .eq("is_active", True)
                .maybe_single()
                .execute()
            )
            return res.data if res and res.data else None
        except Exception:
            return None

    def create_prompt_version(
        self,
        component: str,
        prompt_template: str,
        system_prompt: str,
        model_name: str,
        temperature: float,
        version: int,
        notes: str = "",
    ) -> str:
        prompt_id = str(uuid.uuid4())
        data = {
            "id": prompt_id,
            "component": component,
            "version": version,
            "prompt_template": prompt_template,
            "system_prompt": system_prompt,
            "model_name": model_name,
            "temperature": temperature,
            "notes": notes,
            "is_active": False,
        }
        self.client.table("prompt_versions").insert(data).execute()
        return prompt_id

    def activate_prompt(self, component: str, version: int):
        self.client.table("prompt_versions").update({"is_active": False}).eq(
            "component", component
        ).execute()
        self.client.table("prompt_versions").update({"is_active": True}).eq(
            "component", component
        ).eq("version", version).execute()

    def update_prompt_performance(self, prompt_id: str, score: float):
        self.client.table("prompt_versions").update({"performance_score": score}).eq(
            "id", prompt_id
        ).execute()

    # ===== Pipeline Runs =====
    def log_run_start(self, run_id: str, github_run_url: str) -> str:
        log_id = str(uuid.uuid4())
        data = {
            "id": log_id,
            "run_id": run_id,
            "status": "running",
            "started_at": datetime.utcnow().isoformat(),
            "github_run_url": github_run_url,
            "steps_completed": [],
        }
        self.client.table("pipeline_runs").insert(data).execute()
        return log_id

    def log_run_step(self, log_id: str, step: str):
        res = (
            self.client.table("pipeline_runs")
            .select("steps_completed")
            .eq("id", log_id)
            .single()
            .execute()
        )
        steps = res.data.get("steps_completed", []) if res.data else []
        steps.append(step)
        self.client.table("pipeline_runs").update({"steps_completed": steps}).eq(
            "id", log_id
        ).execute()

    def log_run_complete(
        self,
        log_id: str,
        status: str,
        video_id: Optional[str] = None,
        error_step: Optional[str] = None,
        error_details: Optional[str] = None,
    ):
        duration = 0
        res = (
            self.client.table("pipeline_runs")
            .select("started_at")
            .eq("id", log_id)
            .single()
            .execute()
        )
        if res.data:
            start = datetime.fromisoformat(
                res.data["started_at"].replace("Z", "+00:00")
            )
            duration = int((datetime.utcnow() - start).total_seconds())

        self.client.table("pipeline_runs").update(
            {
                "status": status,
                "video_id": video_id,
                "completed_at": datetime.utcnow().isoformat(),
                "duration_seconds": duration,
                "error_step": error_step,
                "error_details": error_details,
            }
        ).eq("id", log_id).execute()


db = Database()
