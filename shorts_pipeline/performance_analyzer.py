from .config import settings
from .database import db
from .models import VideoMetricsSnapshot
from datetime import date, timedelta
from typing import List, Dict, Any
import requests


class PerformanceAnalyzer:
    def __init__(self):
        self.youtube_api_key = getattr(settings, "youtube_api_key", None)

    def collect_metrics_for_recent_videos(self, days_back: int = 7):
        videos = db.get_recent_published(limit=20)

        for video in videos:
            if not video.get("youtube_id"):
                continue

            existing = db.get_metrics_for_video(video["id"], days=1)
            last_date = existing[-1]["date"] if existing else None
            today = date.today().isoformat()

            if last_date == today:
                continue

            metrics = self._fetch_video_stats(video["youtube_id"])
            if metrics:
                metrics["video_id"] = video["id"]
                metrics["date"] = today
                db.upsert_metrics(VideoMetricsSnapshot(**metrics))

    def _fetch_video_stats(self, youtube_id: str) -> Dict[str, Any] | None:
        if not self.youtube_api_key:
            return None

        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            "part": "statistics,contentDetails",
            "id": youtube_id,
            "key": self.youtube_api_key,
        }

        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", [])
            if not items:
                return None

            stats = items[0]["statistics"]
            return {
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
                "shares": 0,
                "subscribers_gained": 0,
                "avg_view_duration": 0,
                "retention_graph": {},
                "ctr": 0,
                "impressions": 0,
                "traffic_sources": {},
            }
        except Exception as e:
            print(f"지표 수집 실패 ({youtube_id}): {e}")
            return None

    def analyze_top_performers(self, limit: int = 5, days: int = 30) -> List[Dict]:
        top_videos = db.get_top_performers(limit=limit, days=days)
        return top_videos

    def calculate_performance_score(self, video_id: str) -> float:
        metrics = db.get_metrics_for_video(video_id, days=30)
        if not metrics:
            return 0.0

        latest = metrics[-1]
        views = latest.get("views", 0)
        likes = latest.get("likes", 0)
        comments = latest.get("comments", 0)
        ctr = latest.get("ctr", 0)
        avg_duration = latest.get("avg_view_duration_seconds", 0)

        score = (
            min(views / 10000, 1) * 30
            + min(likes / max(views * 0.02, 1), 1) * 20
            + min(comments / max(views * 0.005, 1), 1) * 15
            + min(ctr / 10, 1) * 20
            + min(avg_duration / 25, 1) * 15
        )
        return round(score, 2)


performance_analyzer = PerformanceAnalyzer()
