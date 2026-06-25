# Movie Text

영상, SRT, 강의 슬라이드 자료를 작업 단위로 관리하고 자막, 음성, 더빙 영상, 강의 영상을 생성하는 로컬 FastAPI 애플리케이션입니다.

## 주요 기능

- 영상/음성 파일 업로드 후 Whisper 기반 SRT 추출
- 한국어 SRT 보정, 영어 SRT 번역
- SRT 기반 TTS 음성 생성
- 원본 영상과 생성 음성 합성
- 자막 번인 영상 생성
- 자막+더빙 최종 영상 생성
- 발표 장표와 엑셀 대본 기반 강의 영상 생성
- 간단한 영상 편집: 자르기, 앞/뒤 영상 붙이기, LogoIntro 일괄 삽입
- 생성 산출물 관리와 일괄 다운로드
- AI 사용량과 예상 비용 조회

## 기술 스택

- Backend: FastAPI, Uvicorn
- Speech-to-text: OpenAI Whisper local model
- TTS: Gemini TTS, Google Cloud Text-to-Speech
- Text AI: Gemini
- Media processing: FFmpeg, pydub
- Spreadsheet parsing: openpyxl
- Frontend: HTML, CSS, JavaScript
- Storage: SQLite plus local media/artifact folders

## 설치

Python 3.10 이상을 권장합니다.

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
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

예시:

```env
GEMINI_PROVIDER=vertex_ai
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GEMINI_TEXT_MODEL=gemini-2.5-flash
GEMINI_TTS_MODEL=gemini-2.5-flash-tts
TTS_PROVIDER=gemini
WHISPER_MODEL=large-v3
```

Google Cloud 서비스 계정 JSON은 `secrets/` 같은 로컬 전용 경로에 두고 Git에 올리지 않습니다.

## 강의 슬라이드 영상 생성

강의 영상 생성은 다음 입력을 사용합니다.

- 슬라이드 이미지: `.png`, `.jpg`, `.jpeg`
- 장표별 대본 엑셀: `.xlsx`

엑셀은 `slides` 시트 하나만 사용합니다.

| column | name | description |
| --- | --- | --- |
| A | `slide_no` | 슬라이드 순서 번호 |
| B | `slide_file` | 업로드한 슬라이드 이미지 파일명 |
| C | `script` | 해당 장표에서 읽을 전체 대사 |

예시:

| slide_no | slide_file | script |
| ---: | --- | --- |
| 1 | `3-1-1-1-kr.png` | 안녕하세요. 이번 강의에서는 데이터 분석 흐름을 살펴보겠습니다. |
| 2 | `3-1-1-2-kr.png` | 여기서는 Gemini와 Google Sheet를 활용하는 방법을 설명합니다. |

처리 흐름:

1. 엑셀의 장표별 대본으로 TTS 음성을 생성합니다.
2. 생성된 음성을 Whisper로 다시 분석해 실제 타임코드를 얻습니다.
3. 최종 SRT의 시간은 Whisper 결과를 사용합니다.
4. 최종 SRT의 텍스트는 Whisper 텍스트가 아니라 엑셀 원문을 기준으로 다시 매칭합니다.
5. 생성된 음성 길이에 맞춰 슬라이드 영상과 자막/음성을 합성합니다.

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
- `venv/`
- `media/`
- `outputs/`
- `uploads/`
- `thumbnails/`
- `files_db.sqlite`
- `server_*.log`, `*_log.txt`
- `__pycache__/`

## 프로젝트 구조

```text
.
├── main.py                 # FastAPI app and workflow orchestration
├── database.py             # SQLite file/job/artifact storage
├── ai_usage.py             # AI usage and estimated-cost tracking
├── lecture_timeline.py     # lecture XLSX template and parser
├── srt_utils.py            # SRT parsing, formatting, correction helpers
├── video_utils.py          # FFmpeg video helpers
├── static/
│   ├── index.html
│   ├── script.js
│   └── style.css
├── assets/
│   └── video_editor/
│       └── LogoIntro.mp4
├── test_media_features.py
├── requirements.txt
├── start_server.py
└── run.bat
```

## 주의사항

- Whisper 모델은 처음 실행할 때 다운로드 시간이 걸릴 수 있습니다.
- GPU가 있으면 Whisper 음성 인식에 GPU를 사용할 수 있고, 없으면 CPU로 실행됩니다.
- Gemini/Google Cloud 기반 TTS는 원격 API를 사용하므로 로컬 GPU를 사용하지 않습니다.
- 긴 영상과 큰 오디오 파일은 처리 시간이 오래 걸릴 수 있습니다.
- GitHub에 올리기 전 `.env`, 서비스 계정 JSON, 생성 영상/음성 파일이 포함되지 않았는지 확인하세요.
