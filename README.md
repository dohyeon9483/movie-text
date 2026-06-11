# 영상 음성 변환기 (MP4 to Text Converter)

MP4 영상 파일을 자동으로 텍스트로 변환해주는 웹 애플리케이션입니다.

## 🌟 주요 기능

### 1. 두 가지 변환 모드
**🎤 마이크로 녹음하기**
- 실시간 음성 녹음
- 브라우저에서 직접 녹음 (MediaRecorder API)
- 녹음 시간 실시간 표시
- 녹음 완료 후 즉시 텍스트 변환

**📁 파일 업로드하기**
- 영상 파일: MP4, MOV, AVI, MKV, WebM
- 음성 파일: MP3, WAV, M4A, FLAC, OGG, AAC, WMA, Opus
- 텍스트 파일: TXT (직접 업로드)
- 여러 파일 동시 업로드 가능
- 드래그 앤 드롭 지원

### 2. AI 요약 기능 (Gemini API)
- 🎯 **일반 요약**: 범용적인 내용 요약
- 📋 **회의록**: 안건, 논의사항, 결정사항 정리
- 📚 **강의 요약**: 핵심 개념, 예시, 요점 정리
- 🎥 **영상/유튜브 요약**: 주요 내용, 타임라인, 핵심 메시지
- 💬 **일상 대화 요약**: 대화 흐름, 주요 토픽 정리

### 3. 파일 관리 대시보드
- 📊 모든 파일 목록 조회
- 🔍 파일 검색 기능
- 📥 원본/요약본 선택 다운로드
- 🗑️ 파일 삭제
- 💾 자동 저장 (JSON 데이터베이스)

### 고급 기능
- 🤖 OpenAI Whisper를 이용한 고품질 한국어 음성 인식
- 📊 11단계의 상세한 진행 상황 표시
- ⚡ Server-Sent Events를 통한 실시간 진행 상황 업데이트
- 💻 깔끔하고 직관적인 모던 UI

## 설치 방법

### 1. Gemini API 키 설정 (선택 사항)

AI 요약 기능을 사용하려면 Gemini API 키가 필요합니다.

**✨ 추천 방법: 웹 UI에서 직접 입력**
1. 애플리케이션을 실행한 후
2. 상단의 **⚙️ 설정** 버튼 클릭
3. **Gemini API 키** 입력란에 API 키 입력
4. **저장** 버튼 클릭

**API 키 발급 방법:**
1. [Google AI Studio](https://makersuite.google.com/app/apikey)에 접속
2. "Get API Key" 또는 "Create API Key" 클릭
3. 생성된 키를 복사하여 웹 UI의 설정에 입력

> **참고**: 
> - API 키는 브라우저 로컬 스토리지에 저장되어 재접속 시 자동으로 복원됩니다
> - API 키 없이도 음성 인식 기능은 정상적으로 사용 가능합니다

### 2. ffmpeg 설치 (필수)

오디오 추출을 위해 ffmpeg가 필요합니다.

**Windows:**
1. https://www.gyan.dev/ffmpeg/builds/ 에서 ffmpeg 다운로드
2. 압축 해제 후 `bin` 폴더를 환경 변수 PATH에 추가
3. 또는 Chocolatey 사용: `choco install ffmpeg`

**확인:**
```bash
ffmpeg -version
```

### 3. Python 패키지 설치

```bash
pip install -r requirements.txt
```

**참고:** Whisper 모델은 처음 실행 시 자동으로 다운로드됩니다 (약 140MB).

## 실행 방법

### 🚀 간편 실행 (추천)

#### ✅ 방법 1: run.bat 실행 (Windows)
`run.bat` 파일을 더블클릭하세요.
- 영어 메시지로 인코딩 문제 없음
- 자동으로 패키지 설치 및 서버 시작
- 브라우저 자동 실행

#### ✅ 방법 2: Python 스크립트 실행 (권장)
`start_server.py` 파일을 더블클릭하세요.
- 의존성 자동 체크
- 크로스 플랫폼 지원 (Windows/Mac/Linux)
- 브라우저 자동 실행

#### 방법 3: 명령 프롬프트에서 실행
```bash
# 패키지 설치 (처음 한 번만)
pip install -r requirements.txt

# 서버 실행
python start_server.py
```

### 📟 수동 실행 (개발자용)

```bash
python main.py
```

서버가 시작되면 브라우저에서 http://localhost:8000 으로 접속하세요.

### ⚠️ 문제 해결

**한글이 깨져서 배치 파일이 실행되지 않는 경우:**
- ✅ `run.bat` 사용 (영어 버전)
- ✅ 또는 `python start_server.py` 직접 실행

## 사용 방법

### 모드 1: 🎤 마이크로 녹음하기
1. "마이크로 녹음하기" 선택
2. "녹음 시작" 버튼 클릭 (마이크 권한 허용 필요)
3. 말씀하세요 (실시간 타이머 표시)
4. "녹음 중지" 버튼으로 녹음 완료
5. "변환 시작" 버튼으로 텍스트 변환
6. 결과 확인 및 다운로드

### 모드 2: 📁 파일 업로드하기
1. "파일 업로드하기" 선택
2. **여러 개의 영상/음성/텍스트 파일**을 한번에 드래그 앤 드롭하거나 클릭하여 업로드
   - 영상: MP4, MOV, AVI, MKV
   - 음성: MP3, WAV, M4A, FLAC 등
   - 텍스트: TXT (음성 인식 없이 바로 요약 가능)
3. 각 파일의 진행 상황을 실시간으로 확인
   - 11단계의 상세한 진행 과정 표시
   - 각 파일별 독립적인 진행률 바
4. 변환된 텍스트 확인
5. TXT 파일로 다운로드
   - 개별 다운로드: 각 파일 옆 "다운로드" 버튼 (예: video.mp4 → video.txt)
   - 전체 다운로드: "전체 다운로드" 버튼으로 모든 파일을 개별적으로 다운로드

### 모드 3: 📊 대시보드에서 파일 관리
1. 상단의 **📊 대시보드** 버튼 클릭
2. 업로드/녹음한 모든 파일 목록 확인
3. **보기** 버튼으로 파일 상세 정보 확인
   - 원본 텍스트 조회
   - 5가지 AI 요약 선택 가능:
     - 🎯 일반 요약
     - 📋 회의록
     - 📚 강의 요약
     - 🎥 영상 요약
     - 💬 대화 요약
4. **✨ 요약 생성** 버튼으로 현재 선택한 요약 타입 생성
5. **📥 다운로드** 버튼으로 원본/요약본 다운로드
6. **🗑️ 삭제** 버튼으로 파일 삭제
7. 🔍 검색창으로 파일명 검색

### ⚙️ 설정
1. 상단의 **⚙️ 설정** 버튼 클릭
2. **Gemini API 키** 입력
3. API 키 상태 확인 (설정됨/설정 안 됨)

## 기술 스택

- **백엔드:** FastAPI (Python), Server-Sent Events (SSE)
- **음성 인식:** OpenAI Whisper (로컬 모델)
- **AI 요약:** Google Gemini API
- **데이터베이스:** JSON 파일 기반 저장소
- **오디오 처리:** ffmpeg, pydub
- **프론트엔드:** HTML5, CSS3, JavaScript (MediaRecorder API)
- **실시간 통신:** SSE (Server-Sent Events)

## 프로젝트 구조

```
movie-to-txt/
├── run.bat                  # Windows 간편 실행 파일
├── start_server.py          # 크로스 플랫폼 실행 스크립트 (권장)
├── main.py                  # FastAPI 서버 (SSE 지원, API 엔드포인트)
├── database.py              # JSON 기반 파일 메타데이터 저장소
├── requirements.txt         # Python 의존성
├── README.md                # 프로젝트 설명
├── .gitignore               # Git 제외 파일 목록
├── database.json            # 파일 메타데이터 DB (자동 생성)
├── uploads/                 # 임시 업로드 폴더 (자동 생성)
└── static/                  # 프론트엔드 파일
    ├── index.html           # 메인 UI (홈/대시보드/설정)
    ├── style.css            # 모던한 디자인 스타일
    └── script.js            # 전체 프론트엔드 로직
```

## 주의사항

- 영상 길이에 따라 변환 시간이 달라집니다
- 대용량 파일은 처리 시간이 오래 걸릴 수 있습니다
- 한국어 음성에 최적화되어 있습니다
- 첫 실행 시 Whisper 모델 다운로드로 시간이 소요될 수 있습니다

## 문제 해결

### ffmpeg를 찾을 수 없다는 오류
- ffmpeg가 제대로 설치되었는지 확인
- 환경 변수 PATH에 ffmpeg가 추가되었는지 확인

### 메모리 부족 오류
- 환경 변수 `WHISPER_MODEL`을 `turbo`, `small`, `base`, `tiny` 중 하나로 설정

### 음성 인식 정확도가 낮음
- 기본값은 정확도 우선의 `large-v3`입니다
- 속도나 메모리가 부담되면 환경 변수 `WHISPER_MODEL`을 `turbo`, `medium`, `small` 중 하나로 설정
- 단, 더 많은 메모리와 처리 시간 필요

## 라이선스

MIT License

