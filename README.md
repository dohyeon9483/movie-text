# Movie Text

영상, SRT, 강의 슬라이드 자료를 작업 단위로 관리하고 자막, 음성, 더빙 영상, 강의 영상을 생성하는 로컬 FastAPI 애플리케이션입니다.

## 주요 기능

- 영상/음성 파일 업로드 후 Whisper 기반 SRT 추출
- 한국어 SRT 보정, 영어 SRT 번역
- SRT 기반 TTS 음성 생성
- 원본 영상과 생성 음성 합성
- 자막 번인 영상 생성
- 자막+더빙 최종 영상 생성
- 발표 장표와 장표별 대본 엑셀 기반 강의 영상 생성
- 이미지, HTML, PDF 슬라이드 입력 지원
- 간단한 영상 편집: 자르기, 앞/뒤 영상 붙이기, LogoIntro 일괄 삽입
- 생성 산출물 관리와 일괄 다운로드
- AI 사용량과 예상 비용 조회

참고: AI 영상 자동 생성 기능은 실험 단계라 현재 UI에서는 숨겨져 있습니다. 백엔드 코드는 남아 있으므로 추후 개선 후 다시 노출할 수 있습니다.

## 기술 스택

- Backend: FastAPI, Uvicorn
- Speech-to-text: OpenAI Whisper local model
- TTS: Gemini TTS, Google Cloud Text-to-Speech
- Text AI: Gemini
- Media processing: FFmpeg, pydub
- HTML slide rendering: Playwright Chromium
- PDF slide rendering: PyMuPDF
- Spreadsheet parsing: openpyxl
- Frontend: HTML, CSS, JavaScript
- Storage: SQLite plus local media/artifact folders

## 설치

Python 3.10 이상을 권장합니다.

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
```

FFmpeg가 필요합니다.

```bash
ffmpeg -version
```

Windows에서는 FFmpeg를 PATH에 추가하거나 Chocolatey를 사용할 수 있습니다.

```bash
choco install ffmpeg
```

## 실행

```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

또는:

```bash
python start_server.py
```

브라우저에서 접속합니다.

```text
http://127.0.0.1:8000
```

## 환경 설정

`.env` 파일은 저장소에 포함하지 않습니다. 필요 시 로컬에서 직접 생성합니다.

```env
GEMINI_PROVIDER=vertex_ai
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=secrets/google-service-account.json
GEMINI_TEXT_MODEL=gemini-2.5-flash
GEMINI_TTS_MODEL=gemini-2.5-flash-tts
TTS_PROVIDER=gemini
WHISPER_MODEL=large-v3
VEO_MODEL=veo-3.1-fast-generate-001
VEO_LOCATION=us-central1
VEO_ASPECT_RATIO=9:16
VEO_RESOLUTION=720p
```

Google Cloud 서비스 계정 JSON은 `secrets/` 같은 로컬 전용 경로에 두고 Git에 올리지 않습니다.

자세한 Vertex AI 설정 방법은 [SETUP_VERTEX_AI.md](SETUP_VERTEX_AI.md)를 참고하세요.

## 강의 슬라이드 영상 생성

강의 영상 생성은 다음 입력을 사용합니다.

- 슬라이드 파일: `.png`, `.jpg`, `.jpeg`, `.html`, `.htm`, `.pdf`
- 장표별 대본 엑셀: `.xlsx`

엑셀은 `slides` 시트 하나를 사용합니다.

| column | name | description |
| --- | --- | --- |
| A | `slide_no` | 슬라이드 순서 번호 |
| B | `slide_file` | 업로드한 슬라이드 이미지, HTML 장표, PDF 페이지 참조 |
| C | `script` | 해당 장표에서 읽을 전체 대사 |

예시:

| slide_no | slide_file | script |
| ---: | --- | --- |
| 1 | `3-1-1-1-kr.png` | 안녕하세요. 이번 강의에서는 데이터 분석 흐름을 살펴보겠습니다. |
| 2 | `lecture_deck.html#1` | HTML 한 파일 안에 여러 장표가 있다면 파일명 뒤에 번호를 붙입니다. |
| 3 | `lecture_deck.html#2` | 서버는 해당 HTML 장표를 PNG로 렌더링한 뒤 영상 생성 흐름에 연결합니다. |
| 4 | `lecture_slides.pdf#1` | PDF 파일도 페이지 번호를 붙여 사용할 수 있습니다. |

HTML 장표 규칙:

- HTML 파일이 단일 장표라면 `slide.html`처럼 파일명만 씁니다.
- HTML 파일 안에 여러 장표가 있다면 `deck.html#1`, `deck.html#2`처럼 1부터 시작하는 장표 번호를 붙입니다.
- 서버는 `section.slide`, `.slide`, `[data-slide]`를 장표로 인식합니다.

PDF 장표 규칙:

- PDF 파일이 단일 페이지라면 `slide.pdf`처럼 파일명만 씁니다.
- PDF 파일 안에 여러 페이지가 있다면 `deck.pdf#1`, `deck.pdf#2`처럼 1부터 시작하는 페이지 번호를 붙입니다.

처리 흐름:

1. 엑셀의 장표별 대본으로 TTS 음성을 생성합니다.
2. HTML/PDF 슬라이드가 있으면 PNG로 렌더링합니다.
3. 생성된 음성을 Whisper로 다시 분석해 실제 타임코드를 얻습니다.
4. 최종 SRT의 시간은 Whisper 결과를 사용합니다.
5. 최종 SRT의 텍스트는 Whisper 텍스트가 아니라 엑셀 원문을 기준으로 다시 매칭합니다.
6. 생성된 음성 길이에 맞춰 슬라이드 영상과 자막/음성을 합성합니다.

이 구조는 Whisper가 `Gemini`를 `Gemina`처럼 잘못 받아쓰는 경우에도 최종 자막 텍스트가 엑셀 원문을 따르도록 하기 위한 것입니다.

## 영상 편집

영상 편집 탭에서는 자막/더빙 작업 없이 편집용 영상을 업로드해 간단한 후처리를 수행합니다.

- 선택 구간 자르기
- 앞/뒤 영상 붙이기
- 기본 `assets/video_editor/LogoIntro.mp4` 일괄 삽입

`LogoIntro.mp4`는 기본 앱 에셋으로 저장소에 포함됩니다.

## AI 사용량과 예상 비용

설정 탭에서 기간을 지정해 AI 사용 이벤트와 예상 비용을 확인할 수 있습니다.

기록 대상:

- Gemini 텍스트 요청
- Gemini TTS 요청
- Google Cloud TTS 요청
- 이미지/영상 생성 요청 메타데이터

비용은 API 사용량 메타데이터 또는 내부 추정치 기반의 예상값입니다.

## 테스트

```bash
python -m py_compile main.py database.py ai_usage.py lecture_timeline.py srt_utils.py video_utils.py test_media_features.py
python -m unittest test_media_features.py
```

## Git에 포함하지 않는 파일

아래 항목은 실행 중 자동 생성되는 로컬 파일이므로 Git에 포함하지 않습니다.

- `.env`
- `secrets/`
- `uploads/`
- `media/`
- `outputs/`
- `thumbnails/`
- `files_db.sqlite`
- `files_db.json`
- `server_*.log`, `*_log.txt`
- `__pycache__/`

## 프로젝트 구조

```text
.
├── main.py
├── database.py
├── ai_usage.py
├── lecture_timeline.py
├── srt_utils.py
├── video_utils.py
├── static/
│   ├── index.html
│   ├── script.js
│   └── style.css
├── assets/
│   └── video_editor/
│       └── LogoIntro.mp4
├── scripts/
│   └── generate_voice_samples_assets.py
├── test_media_features.py
├── requirements.txt
├── start_server.py
└── run.bat
```

## 주의사항

- Whisper 모델은 처음 실행할 때 다운로드 시간이 걸릴 수 있습니다.
- GPU가 있으면 Whisper 음성 인식에 GPU를 사용할 수 있고, 없으면 CPU로 실행됩니다.
- Gemini/Google Cloud 기반 TTS는 원격 API를 사용하므로 로컬 GPU를 사용하지 않습니다.
- HTML 슬라이드 렌더링에는 Playwright Chromium 설치가 필요합니다.
- PDF 슬라이드 렌더링에는 PyMuPDF 설치가 필요합니다.
- 긴 영상과 큰 오디오 파일은 처리 시간이 오래 걸릴 수 있습니다.
- GitHub에 올리기 전 `.env`, 서비스 계정 JSON, 생성 영상/음성 파일이 포함되지 않았는지 확인하세요.
