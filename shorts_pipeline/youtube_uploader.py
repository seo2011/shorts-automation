from .config import settings
from .models import UploadResult
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from pathlib import Path


class YouTubeUploader:
    def __init__(self):
        self.credentials = Credentials(
            token=None,
            refresh_token=settings.youtube_refresh_token,
            client_id=settings.youtube_client_id,
            client_secret=settings.youtube_client_secret,
            token_uri="https://oauth2.googleapis.com/token",
            scopes=["https://www.googleapis.com/auth/youtube.upload"],
        )
        self.youtube = build("youtube", "v3", credentials=self.credentials)

    def upload(
        self,
        video_path: str,
        thumbnail_path: str,
        title: str,
        description: str,
        tags: list,
        video_id: str,
    ) -> UploadResult:
        privacy = settings.youtube_privacy_status or "public"
        if "#shorts" not in description.lower():
            description = description + "\n\n#Shorts"
        if "Shorts" not in tags:
            tags = tags + ["Shorts"]

        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags[:30],
                "categoryId": "24",
                "defaultLanguage": "en",
                "defaultAudioLanguage": "en",
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(
            video_path, chunksize=-1, resumable=True, mimetype="video/mp4"
        )

        request = self.youtube.videos().insert(
            part="snippet,status", body=body, media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"업로드 진행: {int(status.progress() * 100)}%")

        youtube_id = response["id"]
        print(f"업로드 완료: {youtube_id} (privacy={privacy})")

        if thumbnail_path and Path(thumbnail_path).exists():
            try:
                self.youtube.thumbnails().set(
                    videoId=youtube_id,
                    media_body=MediaFileUpload(thumbnail_path, mimetype="image/jpeg"),
                ).execute()
                print("썸네일 업로드 완료")
            except Exception as e:
                print(f"썸네일 설정 건너뜀 (채널 미인증 가능): {e}")

        return UploadResult(
            youtube_id=youtube_id,
            url=f"https://youtube.com/shorts/{youtube_id}",
            status="published",
        )


youtube_uploader = YouTubeUploader()
