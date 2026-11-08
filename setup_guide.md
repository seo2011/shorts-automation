# 🚀 설정 가이드 (오직 당신만 수행)

아래 단계를 순서대로 수행하세요. 코드는 이미 모두 작성되어 있습니다.

## 1단계: GitHub 저장소 생성

1. https://github.com 에서 새 저장소 생성 (Public 권장)
2. 저장소 이름: `shorts-automation`
3. 로컬에 클론:
   ```bash
   git clone https://github.com/yourname/shorts-automation.git
   cd shorts-automation
   ```
4. 이 폴더의 모든 파일을 복사해서 붙여넣기

## 2단계: Supabase 프로젝트 생성

1. https://supabase.com 에서 새 프로젝트 생성
2. Settings → API 에서 다음 복사:
   - `Project URL` → `SUPABASE_URL`
   - `service_role` 키 → `SUPABASE_SERVICE_KEY` (anon 키 아님!)
3. SQL Editor에서 `supabase_schema.sql` 전체 복사해서 실행
4. Database → Extensions에서 `uuid-ossp`, `pgcrypto` 활성화

## 3단계: YouTube API + OAuth 설정 (1회)

1. https://console.cloud.google.com 에서 새 프로젝트 생성
2. APIs & Services → YouTube Data API v3 활성화
3. OAuth 동의 화면 설정 (External, 테스트 사용자 본인 이메일 추가)
4. Credentials → OAuth 2.0 Client ID 생성 (Web application)
   - Authorized redirect URIs: `http://localhost:8080/callback`
5. 클라이언트 시크릿 JSON 다운로드
6. 아래 스크립트로 리프레시 토큰 발급 (로컬에서 1회만 실행):
   ```python
   from google_auth_oauthlib.flow import InstalledAppFlow
   flow = InstalledAppFlow.from_client_secrets_file(
       "client_secret.json",
       scopes=["https://www.googleapis.com/auth/youtube.upload"]
   )
   creds = flow.run_local_server(port=8080, access_type="offline", prompt="consent")
   print("REFRESH_TOKEN:", creds.refresh_token)
   print("CLIENT_ID:", creds.client_id)
   print("CLIENT_SECRET:", creds.client_secret)
   ```

## 4단계: NVIDIA NGC API 키

1. https://build.nvidia.com 에서 API 키 발급
2. 사용 가능한 모델 확인:
   ```bash
   curl -H "Authorization: Bearer $NVIDIA_API_KEY" \
     https://integrate.api.nvidia.com/v1/models
   ```

## 5단계: GitHub Secrets 등록

GitHub 저장소 → Settings → Secrets and variables → Actions 에서 추가:

| 시크릿 | 값 |
|--------|-----|
| SUPABASE_URL | https://xxxx.supabase.co |
| SUPABASE_SERVICE_KEY | service_role 키 |
| NVIDIA_API_KEY | nvapi-... |
| NVIDIA_BASE_URL | https://integrate.api.nvidia.com/v1 |
| NVIDIA_MODEL | meta/llama-3.1-70b-instruct |
| NVIDIA_TEMPERATURE | 0.7 |
| YOUTUBE_CLIENT_ID | xxx.apps.googleusercontent.com |
| YOUTUBE_CLIENT_SECRET | GOCSPX-... |
| YOUTUBE_REFRESH_TOKEN | 1//0xxx |
| YOUTUBE_CHANNEL_ID | UC... |
| TELEGRAM_BOT_TOKEN | (선택) |
| TELEGRAM_CHAT_ID | (선택) |

## 6단계: 참조 화자 오디오 준비 (XTTS용)

- `data/speakers/reference_en.wav`에 10~30초 영어 음성 파일 배치
- 없으면 Coqui 기본 화자 사용 (품질 낮음)

## 7단계: 폰트 파일 배치

- `assets/fonts/`에 NotoSansKR-Bold.ttf 등 한글/영문 폰트 배치
- https://github.com/googlefonts/noto-fonts 에서 다운로드

## 8단계: 첫 실행 테스트

```bash
# 로컬에서 테스트
python -m shorts_pipeline.run_daily
```

이후 GitHub Actions 탭에서 "Run workflow"로 수동 실행 후, 매일 UTC 15시 (KST 00시) 자동 실행됩니다.

---

## ⚠️ 제약사항 (무료 티어)

| 항목 | 제약 |
|------|------|
| GitHub Actions | 퍼블릭 저장소: 무제한 / 프라이빗: 월 2,000분 |
| Supabase | 500MB DB, 2GB 대역폭 |
| YouTube Data API | 일일 10,000 유닛 (쇼츠 ~50개 업로드 가능) |
| NVIDIA NGC | 무료 티어 내 호출 한도 |

---

## 📞 문제 발생 시

Telegram 알림을 설정하면 실패 시 메시지가 전송됩니다. GitHub Actions의 "Actions" 탭에서 상세 로그를 확인할 수 있습니다.
