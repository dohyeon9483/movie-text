# Vertex AI Gemini 설정 가이드

이 프로젝트는 기본적으로 Vertex AI Gemini를 사용합니다. Gemini API Key 방식이 아니라 Google Cloud 프로젝트와 서비스 계정 JSON을 사용하는 방식입니다.

## 필요한 값

- Google Cloud 프로젝트 ID
- Vertex AI API 사용 설정
- 서비스 계정 JSON 파일
- 프로젝트 루트의 `.env` 설정

## 1. Google Cloud 프로젝트 ID 확인

1. [Google Cloud Console](https://console.cloud.google.com/)에 접속합니다.
2. 상단 프로젝트 선택 메뉴를 엽니다.
3. 프로젝트 목록에서 `ID` 값을 확인합니다.

예시:

| 이름 | ID |
| --- | --- |
| Movie Text TTS | `movie-text-tts` |

`.env`에는 프로젝트 이름이 아니라 ID를 넣습니다.

```env
GOOGLE_CLOUD_PROJECT=movie-text-tts
```

## 2. Vertex AI API 활성화

1. Google Cloud Console에서 프로젝트가 올바르게 선택되어 있는지 확인합니다.
2. `API 및 서비스` → `라이브러리`로 이동합니다.
3. `Vertex AI API`를 검색합니다.
4. `사용 설정`을 클릭합니다.

이미 활성화되어 있으면 관리 화면이 표시될 수 있습니다.

## 3. 서비스 계정 만들기

1. `IAM 및 관리자` → `서비스 계정`으로 이동합니다.
2. `서비스 계정 만들기`를 클릭합니다.
3. 서비스 계정 이름을 입력합니다.

예시:

```text
movie-text-tts-local
```

4. `만들고 계속`을 클릭합니다.
5. 역할에 다음 권한을 추가합니다.

```text
Vertex AI User
```

6. 나머지 단계는 기본값으로 두고 완료합니다.

## 4. 서비스 계정 JSON 키 받기

1. `IAM 및 관리자` → `서비스 계정`으로 이동합니다.
2. 방금 만든 서비스 계정을 클릭합니다.
3. 상단 `키` 탭을 엽니다.
4. `키 추가` → `새 키 만들기`를 클릭합니다.
5. 키 유형은 `JSON`을 선택합니다.
6. `만들기`를 누르면 JSON 파일이 다운로드됩니다.

## 5. JSON 파일 위치

다운로드한 JSON 파일을 프로젝트 안의 `secrets/` 폴더에 둡니다.

예시:

```text
C:\Users\Admin\Desktop\기타\moive-text\movie-text\secrets\google-service-account.json
```

`secrets/` 폴더는 `.gitignore`에 포함되어 있으므로 GitHub에 올라가지 않습니다.

## 6. .env 설정

프로젝트 루트에 `.env` 파일을 만들고 다음 값을 설정합니다.

```env
GEMINI_PROVIDER=vertex_ai
GOOGLE_CLOUD_PROJECT=movie-text-tts
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=secrets/google-service-account.json

GEMINI_TEXT_MODEL=gemini-2.5-flash
GEMINI_TTS_MODEL=gemini-2.5-flash-tts
TTS_PROVIDER=gemini

VEO_MODEL=veo-3.1-fast-generate-001
VEO_LOCATION=us-central1
VEO_ASPECT_RATIO=9:16
VEO_RESOLUTION=720p

WHISPER_MODEL=large-v3
```

## 7. 서버 재시작

`.env`를 수정한 뒤 서버를 재시작합니다.

```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

## 8. 확인 방법

서버 시작 로그에서 다음과 유사한 메시지를 확인합니다.

```text
Vertex AI Gemini connection complete. (project: movie-text-tts, location: us-central1, model: gemini-2.5-flash)
```

설정 탭이나 음성 미리듣기 기능을 실행해 API 호출이 정상 동작하는지 확인할 수 있습니다.

## 자주 나는 문제

### 프로젝트 ID가 틀린 경우

`GOOGLE_CLOUD_PROJECT`에는 프로젝트 표시 이름이 아니라 프로젝트 ID를 넣어야 합니다.

### 인증 파일 경로가 틀린 경우

`GOOGLE_APPLICATION_CREDENTIALS` 경로가 실제 JSON 파일 위치와 일치해야 합니다.

### 권한 부족

서비스 계정에 `Vertex AI User` 역할이 없으면 Gemini 또는 Veo 호출이 실패할 수 있습니다.

### 모델 접근 불가

Veo 모델은 프로젝트/리전/권한에 따라 사용할 수 있는 모델명이 달라질 수 있습니다. 기본값은 비용을 고려해 `veo-3.1-fast-generate-001`과 `720p`를 사용합니다.
