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
                "privacyStatus": "public",
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
        print(f"업로드 완료: {youtube_id}")

        if thumbnail_path and Path(thumbnail_path).exists():
            self.youtube.thumbnails().set(
                videoId=youtube_id,
                media_body=MediaFileUpload(thumbnail_path, mimetype="image/jpeg"),
            ).execute()
            print("썸네일 업로드 완료")

        if "#shorts" not in " ".join(tags).lower():
            self.youtube.videos().update(
                part="snippet",
                body={
                    "id": youtube_id,
                    "snippet": {
                        "title": title,
                        "description": description + "\n\n#Shorts",
                        "tags": tags + ["Shorts"],
                        "categoryId": "24",
                    },
                },
            ).execute()

        return UploadResult(
            youtube_id=youtube_id,
            url=f"https://youtube.com/shorts/{youtube_id}",
            status="published",
        )


youtube_uploader = YouTubeUploader()
