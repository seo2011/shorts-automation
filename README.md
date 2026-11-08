# Shorts Automation AI

미국 추천 시간에 맞춰 쇼츠를 자동으로 제작·업로드하는 완전 자동화 시스템.

## 구성
- 주제 탐색 (역사 미스터리 / 실화 범죄 / 기묘한 우연)
- AI 각본 작성 (NVIDIA NGC LLM)
- 이미지 생성 (Stable Diffusion / Replicate)
- TTS 음성 생성 (Coqui XTTS v2)
- 영상 합성 (MoviePy + 켄번 효과 + 자막)
- YouTube 예약 업로드 (GitHub Actions 크론)
- 성과 분석 및 자기 개선 루프 (Supabase)

## 폴더 구조
```
shorts_automation/
├── .github/workflows/daily-shorts.yml  # GitHub Actions 크론 (매일 UTC 15시)
├── shorts_pipeline/                    # 파이프라인 코드
│   ├── config.py                       # 설정 관리
│   ├── database.py                     # Supabase 클라이언트
│   ├── models.py                       # 데이터 모델
│   ├── topic_research.py               # 주제 탐색
│   ├── script_writer.py                # 각본 작성
│   ├── image_generator.py              # 이미지 생성
│   ├── tts_generator.py                # TTS 음성 생성
│   ├── video_composer.py               # 영상 합성
│   ├── youtube_uploader.py             # YouTube 업로드
│   ├── performance_analyzer.py         # 성과 수집
│   ├── prompt_optimizer.py             # 프롬프트 자기 개선
│   └── run_daily.py                    # 메인 실행 진입점
├── data/speakers/                      # TTS 참조 화자 오디오
├── assets/fonts/                       # 자막 폰트
├── logs/                               # 실행 로그
├── output/                             # 생성된 영상/이미지/오디오
├── supabase_schema.sql                 # DB 스키마
├── .env.example                        # 환경변수 템플릿
├── requirements.txt                    # Python 의존성
└── setup_guide.md                      # 설정 가이드
```

## 시작 방법
`setup_guide.md`를 참고하세요.
