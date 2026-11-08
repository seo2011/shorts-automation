import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from shorts_pipeline.config import settings
from shorts_pipeline.database import db
from shorts_pipeline.topic_research import generate_multiple_topics
from shorts_pipeline.script_writer import write_script
from shorts_pipeline.image_generator import image_generator
from shorts_pipeline.tts_generator import tts_generator
from shorts_pipeline.video_composer import video_composer
from shorts_pipeline.youtube_uploader import youtube_uploader
from shorts_pipeline.performance_analyzer import performance_analyzer
from shorts_pipeline.prompt_optimizer import prompt_optimizer
from shorts_pipeline.models import VideoStatus
from rich.console import Console
from rich.panel import Panel

console = Console()


def send_telegram(message: str):
    if settings.telegram_bot_token and settings.telegram_chat_id:
        import requests

        try:
            requests.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                json={
                    "chat_id": settings.telegram_chat_id,
                    "text": message,
                    "parse_mode": "HTML",
                },
                timeout=10,
            )
        except Exception:
            pass


def main():
    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    github_run_url = f"https://github.com/{os.environ.get('GITHUB_REPOSITORY', 'local')}/actions/runs/{run_id}"

    console.print(
        Panel.fit(
            f"🎬 Shorts Daily Pipeline Started\nRun ID: {run_id}", style="bold blue"
        )
    )
    send_telegram(f"🎬 <b>Shorts 파이프라인 시작</b>\nRun: {run_id}")

    log_id = db.log_run_start(run_id, github_run_url)
    video_id = None
    steps_completed = []
    error_step = None
    error_details = None

    try:
        # 1. 주제 탐색
        console.print("[yellow]1/7 주제 탐색 중...[/yellow]")
        db.log_run_step(log_id, "topic_research")
        topics = generate_multiple_topics(count=3)
        if not topics:
            raise Exception("주제 생성 실패")
        topic = topics[0]
        console.print(
            f"  ✅ 선정: {topic.topic_title} ({topic.estimated_interest_score}점)"
        )
        steps_completed.append("topic")

        # 2. 비디오 레코드 생성 (초안)
        console.print("[yellow]2/7 대본 작성 중...[/yellow]")
        db.log_run_step(log_id, "script_writing")
        script = write_script(topic)
        video_id = db.create_video(topic, script)
        db.update_video_status(video_id, VideoStatus.SCRIPTING)
        console.print(
            f"  ✅ 대본 완료: {script.total_words}단어, {len(script.scenes)}씬"
        )
        steps_completed.append("script")

        # 3. 이미지 생성
        console.print("[yellow]3/7 이미지 생성 중...[/yellow]")
        db.log_run_step(log_id, "image_generation")
        db.update_video_status(video_id, VideoStatus.GENERATING_IMAGES)
        images = image_generator.generate_all(script.scenes, video_id)
        console.print(f"  ✅ 이미지 {len(images)}장 생성 완료")
        steps_completed.append("images")

        # 4. TTS 생성
        console.print("[yellow]4/7 음성 생성 중...[/yellow]")
        db.log_run_step(log_id, "tts_generation")
        db.update_video_status(video_id, VideoStatus.GENERATING_TTS)
        tts = tts_generator.generate_for_script(script.scenes, video_id)
        console.print(f"  ✅ 음성 생성: {tts.duration_seconds:.1f}초")
        steps_completed.append("tts")

        # 5. 영상 합성
        console.print("[yellow]5/7 영상 합성 중...[/yellow]")
        db.log_run_step(log_id, "video_composition")
        db.update_video_status(video_id, VideoStatus.COMPOSING_VIDEO)
        video_result = video_composer.compose(
            script.scenes, images, tts, video_id, script.hook_text
        )
        db.update_video_paths(
            video_id, video_result.video_path, video_result.thumbnail_path
        )
        console.print(
            f"  ✅ 영상 완성: {video_result.duration_seconds:.1f}초, {video_result.file_size_mb:.1f}MB"
        )
        steps_completed.append("video")

        # 6. YouTube 업로드
        console.print("[yellow]6/7 YouTube 업로드 중...[/yellow]")
        db.log_run_step(log_id, "youtube_upload")
        db.update_video_status(video_id, VideoStatus.UPLOADING)
        upload_result = youtube_uploader.upload(
            video_path=video_result.video_path,
            thumbnail_path=video_result.thumbnail_path,
            title=script.title,
            description=script.description,
            tags=script.tags,
            video_id=video_id,
        )
        db.update_video_youtube_id(
            video_id, upload_result.youtube_id, datetime.utcnow()
        )
        console.print(f"  ✅ 업로드 완료: {upload_result.url}")
        steps_completed.append("upload")

        # 7. 성과 수집
        console.print("[yellow]7/7 성과 지표 수집 중...[/yellow]")
        db.log_run_step(log_id, "metrics_collection")
        performance_analyzer.collect_metrics_for_recent_videos(days_back=7)
        steps_completed.append("metrics")

        # 성공
        db.log_run_complete(log_id, "success", video_id=video_id)
        console.print(Panel.fit("✅ 파이프라인 완전 성공!", style="bold green"))
        send_telegram(
            f"✅ <b>파이프라인 성공</b>\n영상: {script.title}\nURL: {upload_result.url}"
        )

    except Exception as e:
        error_step = error_step or "unknown"
        error_details = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        console.print(Panel.fit(f"❌ 파이프라인 실패: {e}", style="bold red"))
        send_telegram(
            f"❌ <b>파이프라인 실패</b>\nStep: {error_step}\nError: {str(e)[:200]}"
        )
        db.log_run_complete(
            log_id,
            "failed",
            video_id=video_id,
            error_step=error_step,
            error_details=error_details,
        )
        sys.exit(1)

    finally:
        # 주간 프롬프트 최적화 (일요일만 실행)
        if datetime.utcnow().weekday() == 6:
            console.print("[cyan]주간 프롬프트 최적화 실행...[/cyan]")
            prompt_optimizer.run_optimization_cycle()


if __name__ == "__main__":
    main()
