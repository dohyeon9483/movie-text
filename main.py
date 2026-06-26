import os
import uuid
import json
import asyncio
import re
import base64
import subprocess
import tempfile
import wave
import io
import zipfile
import time
import shutil
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Callable, Awaitable, Any
from dotenv import load_dotenv, set_key
from pydantic import BaseModel

import whisper
import torch
import numpy as np
import ai_usage
import database as db
from openpyxl import Workbook
from lecture_timeline import (
    LECTURE_HTML_SLIDE_EXTENSIONS,
    LECTURE_IMAGE_SLIDE_EXTENSIONS,
    LECTURE_PDF_SLIDE_EXTENSIONS,
    LECTURE_SLIDE_EXTENSIONS,
    create_lecture_timeline_template,
    parse_lecture_timeline_xlsx,
    safe_upload_filename,
)
from srt_utils import (
    build_srt,
    build_srt_from_timed_items,
    clean_corrected_subtitle_text,
    format_srt_entry,
    format_srt_time,
    normalize_corrected_srt_by_index,
    normalize_corrected_srt_items,
    parse_srt,
)
import video_utils
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydub import AudioSegment, effects, silence
try:
    from google import genai as google_genai
    from google.genai import types as google_genai_types
except Exception:
    google_genai = None
    google_genai_types = None
try:
    from google.cloud import texttospeech as cloud_texttospeech
except Exception:
    cloud_texttospeech = None

import sys
print("실행 파이썬:", sys.executable)
print("torch 버전:", torch.__version__)
print("cuda 사용 가능:", torch.cuda.is_available())

def format_time(seconds: float) -> str:
    """Converts seconds to HH:MM:SS format."""
    if seconds is None:
        return "00:00:00"
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def split_subtitle_text(text: str, max_chars: Optional[int] = None) -> List[str]:
    max_chars = max_chars or SRT_MAX_CUE_CHARS
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    tokens = re.findall(r"\S+\s*", text)
    chunks = []
    current = ""
    for token in tokens:
        candidate = f"{current}{token}".strip()
        boundary = bool(re.search(r"[.!?。！？]|[.!?]\s*$|[.?!,，、]\s*$", token.strip()))
        if current and (len(candidate) > max_chars or boundary and len(current.strip()) >= max_chars * 0.55):
            chunks.append(current.strip())
            current = token
        else:
            current = candidate
    if current.strip():
        chunks.append(current.strip())

    refined = []
    for chunk in chunks:
        if len(chunk) <= max_chars * 1.35:
            refined.append(chunk)
            continue
        words = chunk.split()
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if current and len(candidate) > max_chars:
                refined.append(current)
                current = word
            else:
                current = candidate
        if current:
            refined.append(current)
    return refined or [text]


def split_segment_into_srt_entries(start_seconds: float, end_seconds: float, text: str) -> List[Tuple[float, float, str]]:
    duration = max(float(end_seconds or 0) - float(start_seconds or 0), 0.2)
    min_parts_by_time = max(1, int(np.ceil(duration / max(SRT_MAX_CUE_DURATION_SECONDS, 0.5))))
    text_parts = split_subtitle_text(text, SRT_MAX_CUE_CHARS)
    if len(text_parts) < min_parts_by_time:
        words = re.sub(r"\s+", " ", text.strip()).split()
        if words:
            target_parts = min(min_parts_by_time, max(1, len(words)))
            text_parts = []
            for idx in range(target_parts):
                start = round(idx * len(words) / target_parts)
                end = round((idx + 1) * len(words) / target_parts)
                part = " ".join(words[start:end]).strip()
                if part:
                    text_parts.append(part)

    total_weight = sum(max(len(part), 1) for part in text_parts) or 1
    cursor = float(start_seconds or 0)
    entries = []
    for index, part in enumerate(text_parts):
        if index == len(text_parts) - 1:
            part_end = float(end_seconds or cursor + 0.2)
        else:
            part_duration = duration * (max(len(part), 1) / total_weight)
            part_end = min(float(end_seconds), cursor + max(part_duration, 0.45))
        entries.append((cursor, max(part_end, cursor + 0.2), part))
        cursor = part_end
    return entries
# Pydantic 모델
# Override the legacy splitter above with a safer Korean-friendly version.
def split_subtitle_text(text: str, max_chars: Optional[int] = None) -> List[str]:
    max_chars = max_chars or SRT_MAX_CUE_CHARS
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    words = text.split(" ")
    if len(words) <= 1:
        return [text[i:i + max_chars].strip() for i in range(0, len(text), max_chars) if text[i:i + max_chars].strip()]

    chunks: List[str] = []
    current_words: List[str] = []
    strong_boundary = re.compile(r"[.!?。！？…]$")
    soft_boundary = re.compile(r"[,，、;:：]$")

    for word in words:
        if len(word) > max_chars:
            if current_words:
                chunks.append(" ".join(current_words).strip())
                current_words = []
            chunks.extend(word[i:i + max_chars].strip() for i in range(0, len(word), max_chars) if word[i:i + max_chars].strip())
            continue

        candidate_words = [*current_words, word]
        candidate = " ".join(candidate_words).strip()
        current = " ".join(current_words).strip()
        has_natural_boundary = bool(
            current_words and (strong_boundary.search(current_words[-1]) or soft_boundary.search(current_words[-1]))
        )
        should_split = bool(current_words) and (
            len(candidate) > max_chars
            or (has_natural_boundary and len(current) >= max_chars * 0.65)
        )
        if should_split:
            chunks.append(current)
            current_words = [word]
        else:
            current_words = candidate_words

    if current_words:
        chunks.append(" ".join(current_words).strip())
    return chunks or [text]


def split_segment_into_srt_entries(start_seconds: float, end_seconds: float, text: str) -> List[Tuple[float, float, str]]:
    duration = max(float(end_seconds or 0) - float(start_seconds or 0), 0.2)
    text_parts = split_subtitle_text(text, SRT_MAX_CUE_CHARS)
    min_parts_by_time = max(1, int(np.ceil(duration / max(SRT_MAX_CUE_DURATION_SECONDS, 0.5))))
    compact_text_length = len(re.sub(r"\s+", "", text or ""))
    max_parts_by_text = max(1, compact_text_length // max(SRT_MIN_CHARS_PER_SPLIT_PART, 1))
    target_parts_by_time = min(min_parts_by_time, max_parts_by_text)
    if (
        compact_text_length >= SRT_TIME_SPLIT_MIN_CHARS
        and len(text_parts) < target_parts_by_time
    ):
        expanded_parts: List[str] = []
        source_parts = text_parts if len(text_parts) > 1 else [text]
        for part in source_parts:
            part_ratio = len(part) / max(len(text), 1)
            part_target_count = max(1, int(round(target_parts_by_time * part_ratio)))
            words = part.split()
            if len(words) > 1:
                for idx in range(part_target_count):
                    start = round(idx * len(words) / part_target_count)
                    end = round((idx + 1) * len(words) / part_target_count)
                    chunk = " ".join(words[start:end]).strip()
                    if chunk:
                        expanded_parts.append(chunk)
            else:
                chunk_size = max(1, int(np.ceil(len(part) / part_target_count)))
                expanded_parts.extend(part[i:i + chunk_size].strip() for i in range(0, len(part), chunk_size) if part[i:i + chunk_size].strip())
        if len(expanded_parts) > len(text_parts):
            text_parts = expanded_parts

    total_weight = sum(max(len(part), 1) for part in text_parts) or 1
    cursor = float(start_seconds or 0)
    entries = []
    for index, part in enumerate(text_parts):
        if index == len(text_parts) - 1:
            part_end = float(end_seconds or cursor + 0.2)
        else:
            part_duration = duration * (max(len(part), 1) / total_weight)
            part_end = min(float(end_seconds), cursor + max(part_duration, 0.45))
        entries.append((cursor, max(part_end, cursor + 0.2), part))
        cursor = part_end
    return entries


class ApiKeyRequest(BaseModel):
    api_key: str

class SubtitleStyleRequest(BaseModel):
    font_family: str = "Arial"
    font_size: int = 48
    position: str = "bottom"
    text_color: str = "#FFFFFF"
    background_color: str = "#000000"
    background_opacity: int = 60
    background_enabled: bool = True
    outline_color: str = "#000000"
    outline_width: int = 2
    shadow: int = 1
    margin_v: int = 64


class LanguageRequest(BaseModel):
    language: str = "ko"
    voice_name: Optional[str] = None
    tts_provider: Optional[str] = None
    style_prompt: Optional[str] = None
    srt_source: Optional[str] = None
    audio_artifact_id: Optional[str] = None
    subtitle_style: Optional[SubtitleStyleRequest] = None

class EnglishSrtRequest(BaseModel):
    english_srt_text: str

class CorrectedSrtRequest(BaseModel):
    corrected_srt_text: str

class ScriptAudioRequest(BaseModel):
    script: str
    language: str = "ko"
    filename: Optional[str] = None
    voice_name: Optional[str] = None
    tts_provider: Optional[str] = None
    style_prompt: Optional[str] = None


class VoiceSampleGenerateRequest(BaseModel):
    force: bool = False


class ArtifactBatchRequest(BaseModel):
    artifact_ids: List[str]


class ScriptJobRequest(BaseModel):
    filename: str
    script: str
    language: str = "ko"

class AiVideoDraftRequest(BaseModel):
    topic: str
    language: str = "ko"
    target_duration: str = "1-3분"
    audience: str = "일반 시청자"
    tone: str = "명확하고 자연스럽게"
    image_style: str = "clean modern editorial illustration, cinematic lighting"
    aspect_ratio: Optional[str] = None
    character_names: Optional[List[str]] = None


class AiVideoSceneRequest(BaseModel):
    scene_no: int
    script: str
    image_prompt: Optional[str] = ""
    visual_notes: Optional[str] = ""
    scene_kind: Optional[str] = "veo_clip"
    audio_mode: Optional[str] = "narrator"
    video_prompt: Optional[str] = ""
    dialogue: Optional[str] = ""
    sound_design: Optional[str] = ""
    subtitle_text: Optional[str] = ""
    duration_seconds: Optional[float] = 5.0
    character_usage: Optional[List[str]] = None
    character_role: Optional[str] = ""


class AiVideoCreateRequest(BaseModel):
    draft_id: Optional[str] = None
    title: Optional[str] = None
    topic: Optional[str] = None
    language: str = "ko"
    target_duration: str = "1-3분"
    audience: str = "일반 시청자"
    tone: str = "명확하고 자연스럽게"
    image_style: str = "clean modern editorial illustration, cinematic lighting"
    aspect_ratio: Optional[str] = None
    character_assets: Optional[List[Dict]] = None
    scenes: Optional[List[AiVideoSceneRequest]] = None
    visual_mode: Optional[str] = None
    visual_provider: Optional[str] = None
    final_output: str = "captioned_dub_video"
    tts_provider: Optional[str] = None
    voice_name: Optional[str] = None
    style_prompt: Optional[str] = None
    subtitle_style: Optional[SubtitleStyleRequest] = None

class JobRequest(BaseModel):
    language: str = "ko"
    voice_name: Optional[str] = None
    tts_provider: Optional[str] = None
    style_prompt: Optional[str] = None
    srt_source: Optional[str] = None
    audio_artifact_id: Optional[str] = None
    final_output: Optional[str] = None
    generate_corrected: bool = True
    generate_english: bool = True
    subtitle_style: Optional[SubtitleStyleRequest] = None


class TrimVideoRequest(BaseModel):
    start_seconds: float = 0
    end_seconds: float


class EditorLogoIntroBatchRequest(BaseModel):
    file_ids: List[str]
    position: str = "before"

# 환경 변수 로드
load_dotenv()

app = FastAPI(title="MP4 to Text Converter")

# 동시 Whisper 전사 요청을 제한하기 위한 세마포어
transcription_semaphore = asyncio.Semaphore(1)

# Gemini API 설정 (사용자가 직접 입력)
gemini_api_key = None
gemini_text_client = None
gemini_tts_client = None
GEMINI_PROVIDER = os.getenv("GEMINI_PROVIDER", "vertex_ai").lower()
VERTEX_AI_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", os.getenv("VERTEX_AI_LOCATION", "global"))
GEMINI_TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash" if GEMINI_PROVIDER in {"vertex_ai", "vertex"} else "gemini-3.5-flash")


def default_gemini_tts_model() -> str:
    if GEMINI_PROVIDER in {"vertex_ai", "vertex", "google_cloud"} and VERTEX_AI_LOCATION != "global":
        return "gemini-2.5-flash-tts"
    return "gemini-3.1-flash-tts-preview"


GEMINI_TTS_MODEL = os.getenv("GEMINI_TTS_MODEL", default_gemini_tts_model())
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "google_cloud").lower()
AI_VIDEO_VISUAL_PROVIDER = os.getenv("AI_VIDEO_VISUAL_PROVIDER", "nano_banana").lower()
AI_VIDEO_VISUAL_MODE = os.getenv("AI_VIDEO_VISUAL_MODE", "veo").lower()
NANO_BANANA_MODEL = os.getenv("NANO_BANANA_MODEL", "gemini-2.5-flash-image")
NANO_BANANA_MODELS = [
    model.strip()
    for model in os.getenv(
        "NANO_BANANA_MODELS",
        f"{NANO_BANANA_MODEL},gemini-3.1-flash-image,gemini-3.1-flash-image-preview,gemini-3-pro-image,gemini-2.5-flash-image-preview",
    ).split(",")
    if model.strip()
]
AI_VIDEO_IMAGE_LOCATION = os.getenv("AI_VIDEO_IMAGE_LOCATION", "global")
AI_VIDEO_IMAGE_API_VERSION = os.getenv("AI_VIDEO_IMAGE_API_VERSION", "")
VEO_MODEL = os.getenv("VEO_MODEL", "veo-3.1-fast-generate-001")
VEO_MODELS = [
    model.strip()
    for model in os.getenv(
        "VEO_MODELS",
        f"{VEO_MODEL},veo-3.1-generate-001",
    ).split(",")
    if model.strip()
]
VEO_LOCATION = os.getenv("VEO_LOCATION", "us-central1")
VEO_API_VERSION = os.getenv("VEO_API_VERSION", "")
VEO_ASPECT_RATIO = os.getenv("VEO_ASPECT_RATIO", "9:16")
VEO_RESOLUTION = os.getenv("VEO_RESOLUTION", "720p")
AI_VIDEO_TRANSCODE_PRESET = os.getenv("AI_VIDEO_TRANSCODE_PRESET", "medium")
AI_VIDEO_TRANSCODE_CRF = os.getenv("AI_VIDEO_TRANSCODE_CRF", "18")
VEO_DEFAULT_DURATION_SECONDS = float(os.getenv("VEO_DEFAULT_DURATION_SECONDS", "5"))
VEO_MAX_DURATION_SECONDS = float(os.getenv("VEO_MAX_DURATION_SECONDS", "8"))
VEO_POLL_INTERVAL_SECONDS = float(os.getenv("VEO_POLL_INTERVAL_SECONDS", "10"))
VEO_MAX_WAIT_SECONDS = float(os.getenv("VEO_MAX_WAIT_SECONDS", "900"))
IMAGEN_MODEL = os.getenv("IMAGEN_MODEL", "imagen-3.0-generate-002")
AI_VIDEO_DEFAULT_SCENE_COUNT = int(os.getenv("AI_VIDEO_DEFAULT_SCENE_COUNT", "10"))
AI_VIDEO_MAX_SCENE_COUNT = int(os.getenv("AI_VIDEO_MAX_SCENE_COUNT", "12"))
AI_VIDEO_IMAGE_ASPECT_RATIO = os.getenv("AI_VIDEO_IMAGE_ASPECT_RATIO", "16:9")
AI_VIDEO_ALLOW_TEXT_FALLBACK = os.getenv("AI_VIDEO_ALLOW_TEXT_FALLBACK", "false").lower() in {"1", "true", "yes", "on"}
AI_VIDEO_DRAFTS: Dict[str, Dict] = {}
ASPECT_RATIO_RE = re.compile(r"(?<!\d)(1:1|9:16|16:9|4:3|3:4)(?!\d)")
VEO_SUPPORTED_ASPECT_RATIOS = {"9:16", "16:9"}
IMAGE_SUPPORTED_ASPECT_RATIOS = {"1:1", "9:16", "16:9", "4:3", "3:4"}


def get_service_account_project_id() -> Optional[str]:
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not credentials_path:
        return None
    try:
        credentials_data = json.loads(Path(credentials_path).read_text(encoding="utf-8"))
        return credentials_data.get("project_id")
    except Exception:
        return None


def get_google_cloud_project() -> Optional[str]:
    return os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT_ID") or get_service_account_project_id()


def set_gemini_api_key(api_key: str) -> bool:
    """Gemini API 키 설정"""
    global gemini_api_key, gemini_text_client, gemini_tts_client
    try:
        if google_genai is None:
            raise RuntimeError("google-genai package is not installed.")
        client = google_genai.Client(api_key=api_key)
        gemini_text_client = client
        gemini_tts_client = client
        gemini_api_key = api_key
        try:
            client.models.generate_content(model=GEMINI_TEXT_MODEL, contents="Hi")
        except Exception as validation_error:
            print(f"Gemini API validation warning: {validation_error}")
        print(f"Gemini API connection complete. (model: {GEMINI_TEXT_MODEL})")
        return True
    except Exception as e:
        print(f"Gemini API 연결 실패: {e}")
        gemini_text_client = None
        gemini_tts_client = None
        gemini_api_key = None
        return False


def persist_gemini_api_key(api_key: str) -> None:
    env_path = Path(".env")
    if not env_path.exists():
        env_path.write_text("", encoding="utf-8")
    set_key(str(env_path), "GEMINI_API_KEY", api_key)


def initialize_gemini_vertex_client() -> bool:
    global gemini_text_client, gemini_tts_client, gemini_api_key
    try:
        if google_genai is None:
            raise RuntimeError("google-genai package is not installed.")
        project = get_google_cloud_project()
        if not project:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT or service account project_id is required for Vertex AI Gemini.")
        client = google_genai.Client(
            vertexai=True,
            project=project,
            location=VERTEX_AI_LOCATION,
            http_options=google_genai_types.HttpOptions(apiVersion="v1") if google_genai_types else None,
        )
        gemini_text_client = client
        gemini_tts_client = client
        gemini_api_key = "vertex-ai"
        try:
            client.models.generate_content(model=GEMINI_TEXT_MODEL, contents="Hi")
        except Exception as validation_error:
            print(f"Vertex AI Gemini validation warning: {validation_error}")
        print(f"Vertex AI Gemini connection complete. (project: {project}, location: {VERTEX_AI_LOCATION}, model: {GEMINI_TEXT_MODEL})")
        return True
    except Exception as e:
        print(f"Vertex AI Gemini connection failed: {e}")
        gemini_text_client = None
        gemini_tts_client = None
        gemini_api_key = None
        return False


def initialize_gemini_from_env() -> None:
    if GEMINI_PROVIDER in {"vertex_ai", "vertex", "google_cloud"}:
        initialize_gemini_vertex_client()
        return
    env_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if env_api_key:
        set_gemini_api_key(env_api_key)


def generate_gemini_text(prompt: str, operation: str = "gemini_text") -> str:
    response = gemini_text_client.models.generate_content(
        model=GEMINI_TEXT_MODEL,
        contents=prompt,
    )
    text = getattr(response, "text", "") or ""
    usage = getattr(response, "usage_metadata", None)
    input_tokens = ai_usage.usage_metadata_value(usage, "prompt_token_count", "input_token_count")
    output_tokens = ai_usage.usage_metadata_value(usage, "candidates_token_count", "output_token_count")
    total_tokens = ai_usage.usage_metadata_value(usage, "total_token_count")
    if not input_tokens:
        input_tokens = ai_usage.estimate_tokens_from_text(prompt)
    if not output_tokens:
        output_tokens = ai_usage.estimate_tokens_from_text(text)
    if not total_tokens:
        total_tokens = input_tokens + output_tokens
    ai_usage.record_ai_usage(
        provider="gemini",
        model=GEMINI_TEXT_MODEL,
        operation=operation,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        characters=len(prompt or "") + len(text or ""),
        request_count=1,
        estimated_cost_usd=ai_usage.estimate_gemini_text_cost(input_tokens, output_tokens),
        metadata={"usage_source": "api" if usage else "estimated_tokens"},
    )
    return text


def create_gemini_image_client() -> Any:
    if google_genai is None:
        raise RuntimeError("google-genai package is not installed.")
    if GEMINI_PROVIDER in {"vertex_ai", "vertex", "google_cloud"}:
        project = get_google_cloud_project()
        if not project:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT or service account project_id is required for Vertex AI image generation.")
        http_options = (
            google_genai_types.HttpOptions(apiVersion=AI_VIDEO_IMAGE_API_VERSION)
            if google_genai_types and AI_VIDEO_IMAGE_API_VERSION
            else None
        )
        return google_genai.Client(
            vertexai=True,
            project=project,
            location=AI_VIDEO_IMAGE_LOCATION,
            http_options=http_options,
        )
    if gemini_tts_client:
        return gemini_tts_client
    if gemini_api_key:
        return google_genai.Client(api_key=gemini_api_key)
    raise RuntimeError("Gemini image client is not configured.")


def create_veo_client() -> Any:
    if google_genai is None:
        raise RuntimeError("google-genai package is not installed.")
    if GEMINI_PROVIDER in {"vertex_ai", "vertex", "google_cloud"}:
        project = get_google_cloud_project()
        if not project:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT or service account project_id is required for Veo generation.")
        http_options = (
            google_genai_types.HttpOptions(apiVersion=VEO_API_VERSION)
            if google_genai_types and VEO_API_VERSION
            else None
        )
        return google_genai.Client(
            vertexai=True,
            project=project,
            location=VEO_LOCATION,
            http_options=http_options,
        )
    if gemini_api_key:
        return google_genai.Client(api_key=gemini_api_key)
    raise RuntimeError("Veo client is not configured.")


initialize_gemini_from_env()

# 디렉토리 생성
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
MEDIA_DIR = Path("media")
MEDIA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)
AI_CHARACTER_ASSET_DIR = MEDIA_DIR / "ai_character_assets"
AI_CHARACTER_ASSET_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_AI_CHARACTER_ASSET_PATH = Path(os.getenv("AI_VIDEO_DEFAULT_CHARACTER_ASSET", str(AI_CHARACTER_ASSET_DIR / "캐릭터 에셋.png")))
DEFAULT_AI_CHARACTER_NAME = os.getenv("AI_VIDEO_DEFAULT_CHARACTER_NAME", "캐릭터 에셋")
DEFAULT_AI_CHARACTER_DESCRIPTION = os.getenv(
    "AI_VIDEO_DEFAULT_CHARACTER_DESCRIPTION",
    "A character reference sheet with a yellow chick mascot and a white bear mascot wearing a blue AI headband, shown from multiple angles and with facial expressions.",
)
DEFAULT_AI_CHARACTER_ASSETS = [
    {
        "name": "오르",
        "filename": "오르.png",
        "description": "Reference sheet for Or, a white bear character with multiple angles and facial expressions.",
    },
    {
        "name": "삐야",
        "filename": "삐야.png",
        "description": "Reference sheet for Ppiya, a yellow chick character with multiple angles and poses.",
    },
]
ASSET_DIR = Path("assets")
VOICE_SAMPLE_DIR = ASSET_DIR / "voice_samples"
VOICE_SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
VIDEO_EDITOR_ASSET_DIR = ASSET_DIR / "video_editor"
VIDEO_EDITOR_ASSET_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_LOGO_INTRO_PATH = VIDEO_EDITOR_ASSET_DIR / "LogoIntro.mp4"
THUMBNAIL_DIR = Path("thumbnails")
THUMBNAIL_DIR.mkdir(exist_ok=True)

# 정적 파일 서빙
app.mount("/static", StaticFiles(directory="static"), name="static")

# GPU 사용 가능 여부 확인
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"사용 장치: {device}")

# Whisper 모델 로드
# 기본값은 정확도가 높은 large-v3입니다.
# 속도나 메모리가 부담되면 환경변수 WHISPER_MODEL=turbo 로 실행하세요.
default_whisper_model = "large-v3"
WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL", default_whisper_model)
print(f"Whisper 모델('{WHISPER_MODEL_NAME}')을 {device}에 로드하는 중...")
try:
    model = whisper.load_model(WHISPER_MODEL_NAME, device=device)
except Exception as e:
    if WHISPER_MODEL_NAME == "turbo":
        raise
    print(f"Whisper 모델('{WHISPER_MODEL_NAME}') 로드 실패: {e}")
    WHISPER_MODEL_NAME = "turbo"
    print(f"Whisper 모델('{WHISPER_MODEL_NAME}')로 다시 시도합니다.")
    model = whisper.load_model(WHISPER_MODEL_NAME, device=device)
print("Whisper 모델 로드 완료!")


TARGET_AUDIO_DBFS = -20.0
MAX_AUDIO_GAIN_DB = 18.0
MAX_TRANSCRIBE_CHUNK_MS = int(os.getenv("MAX_TRANSCRIBE_CHUNK_MS", str(3 * 60 * 1000)))
TTS_GROUP_MAX_CHARS = int(os.getenv("TTS_GROUP_MAX_CHARS", "1800"))
TTS_GROUP_MAX_DURATION_MS = int(os.getenv("TTS_GROUP_MAX_DURATION_MS", "45000"))
TTS_GROUP_MAX_GAP_MS = int(os.getenv("TTS_GROUP_MAX_GAP_MS", "2000"))
TTS_SYNC_MODE = os.getenv("TTS_SYNC_MODE", "cue").lower()
SRT_MAX_CUE_CHARS = int(os.getenv("SRT_MAX_CUE_CHARS", "64"))
SRT_MAX_CUE_DURATION_SECONDS = float(os.getenv("SRT_MAX_CUE_DURATION_SECONDS", "5.5"))
SRT_TIME_SPLIT_MIN_CHARS = int(os.getenv("SRT_TIME_SPLIT_MIN_CHARS", "90"))
SRT_MIN_CHARS_PER_SPLIT_PART = int(os.getenv("SRT_MIN_CHARS_PER_SPLIT_PART", "28"))
GEMINI_TTS_MAX_RETRIES = int(os.getenv("GEMINI_TTS_MAX_RETRIES", "4"))
GEMINI_TTS_RETRY_BASE_SECONDS = float(os.getenv("GEMINI_TTS_RETRY_BASE_SECONDS", "20"))
MIN_TRANSCRIBE_CHUNK_MS = 700
MIN_SILENCE_LEN_MS = 700
KEEP_SILENCE_MS = 250
SILENCE_SEEK_STEP_MS = int(os.getenv("SILENCE_SEEK_STEP_MS", "100"))
MERGE_SPEECH_GAP_MS = int(os.getenv("MERGE_SPEECH_GAP_MS", "2000"))
WHISPER_BEAM_SIZE = int(os.getenv("WHISPER_BEAM_SIZE", "1"))

KOREAN_TRANSCRIPTION_PROMPT = (
    "이것은 한국어 강의 또는 화면 녹화 음성입니다. "
    "한국어 문장 부호와 띄어쓰기를 자연스럽게 정리해서 전사하세요. "
    "영어 기술 용어는 들리는 그대로 유지하세요. "
    "자주 나오는 용어: Python, Jupyter Notebook, Cursor, Selenium, Pandas, Excel, "
    "API, Gemini, ChatGPT, VS Code, GUI, Tkinter, PyQt, batch file, pyinstaller, "
    "웹 크롤링, 데이터프레임, 가상환경, 주피터 노트북, 모드랩스, Mode Labs. "
    "명확히 들리지 않는 구간은 임의로 러시아어, 중국어, 아랍어 등 다른 언어로 쓰지 마세요."
)

UNWANTED_SCRIPT_RE = re.compile(
    r"[\u00c0-\u024f\u0370-\u03ff\u0400-\u052f\u0590-\u08ff"
    r"\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uff00-\uffef]"
)
MEANINGFUL_TEXT_RE = re.compile(r"[0-9A-Za-z가-힣]")
WHISPER_HALLUCINATION_PATTERNS = [
    "한국어 자막 제공",
    "자막 제공",
    "광고는 kakaotalk",
    "광고는 카카오톡",
    "kakaotalk 플러스친구",
    "카카오톡 플러스친구",
    "플러스친구의 홈페이지",
    "시청해주셔서 감사합니다",
    "구독과 좋아요",
]


def is_audio_silent(audio: AudioSegment) -> bool:
    """실질적인 소리가 없는 오디오인지 확인합니다."""
    return len(audio) == 0 or audio.rms == 0 or audio.dBFS == float("-inf")


def preprocess_audio_for_whisper(audio: AudioSegment) -> AudioSegment:
    """Whisper 입력에 맞게 음량, 채널, 샘플레이트, 대역을 정리합니다."""
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
    if is_audio_silent(audio):
        return audio

    audio = audio.high_pass_filter(80).low_pass_filter(7600)
    audio = effects.compress_dynamic_range(
        audio,
        threshold=-28.0,
        ratio=2.5,
        attack=5.0,
        release=50.0,
    )

    if not is_audio_silent(audio):
        gain = TARGET_AUDIO_DBFS - audio.dBFS
        gain = max(min(gain, MAX_AUDIO_GAIN_DB), -MAX_AUDIO_GAIN_DB)
        audio = audio.apply_gain(gain)

    return effects.normalize(audio, headroom=1.0)


def export_preprocessed_audio(input_path: str, output_path: str) -> None:
    """영상/음성 파일을 Whisper용 WAV로 변환하고 전처리합니다."""
    audio = AudioSegment.from_file(input_path)
    audio = preprocess_audio_for_whisper(audio)
    audio.export(output_path, format="wav")


def audiosegment_to_whisper_array(audio: AudioSegment) -> np.ndarray:
    """16kHz mono AudioSegment를 Whisper가 바로 읽을 수 있는 float32 배열로 변환합니다."""
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
    samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
    return samples / 32768.0


def get_silence_threshold(audio: AudioSegment) -> float:
    """오디오 평균 음량을 기준으로 무음 판정 기준을 계산합니다."""
    if is_audio_silent(audio):
        return -50.0
    return max(audio.dBFS - 14.0, -50.0)


def merge_close_ranges(ranges: List[Tuple[int, int]], max_gap_ms: int) -> List[Tuple[int, int]]:
    """서로 가까운 음성 구간을 합쳐 지나치게 잘게 쪼개지는 것을 막습니다."""
    if not ranges:
        return []

    merged = [ranges[0]]
    for start, end in ranges[1:]:
        prev_start, prev_end = merged[-1]
        if start - prev_end <= max_gap_ms:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))
    return merged


def build_transcription_ranges(audio: AudioSegment) -> List[Tuple[int, int]]:
    """무음 구간을 제외하고 Whisper에 넣을 음성 구간 목록을 만듭니다."""
    if is_audio_silent(audio):
        return []

    raw_ranges = silence.detect_nonsilent(
        audio,
        min_silence_len=MIN_SILENCE_LEN_MS,
        silence_thresh=get_silence_threshold(audio),
        seek_step=SILENCE_SEEK_STEP_MS,
    )

    if not raw_ranges:
        raw_ranges = [[0, len(audio)]]

    padded_ranges = []
    for start, end in raw_ranges:
        start = max(0, start - KEEP_SILENCE_MS)
        end = min(len(audio), end + KEEP_SILENCE_MS)
        if end - start >= MIN_TRANSCRIBE_CHUNK_MS:
            padded_ranges.append((start, end))

    merged_ranges = merge_close_ranges(padded_ranges, max_gap_ms=MERGE_SPEECH_GAP_MS)
    transcription_ranges = []
    for start, end in merged_ranges:
        cursor = start
        while cursor < end:
            chunk_end = min(cursor + MAX_TRANSCRIBE_CHUNK_MS, end)
            if chunk_end - cursor >= MIN_TRANSCRIBE_CHUNK_MS:
                transcription_ranges.append((cursor, chunk_end))
            cursor = chunk_end

    return transcription_ranges


def clean_transcript_text(text: str) -> str:
    """한국어 강의 결과에 섞인 비정상 외국어 문자 조각을 정리합니다."""
    text = text.replace("\ufffd", "")
    text = UNWANTED_SCRIPT_RE.sub("", text)
    text = re.sub(r"([.!?。！？…])(?=\S)", r"\1 ", text)
    text = re.sub(r"([,，、;:：])(?=\S)", r"\1 ", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    return text.strip()


def clean_transcript_text(text: str) -> str:
    text = text.replace("\ufffd", "")
    text = UNWANTED_SCRIPT_RE.sub("", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    return text.strip()


def should_skip_segment(segment: dict, text: str) -> bool:
    """Whisper가 낮은 확신도로 만든 환각 가능성이 큰 세그먼트를 제외합니다."""
    compact_text = re.sub(r"\s+", "", text)
    if not compact_text:
        return True

    normalized_text = re.sub(r"\s+", " ", text).strip().lower()
    compact_lower = re.sub(r"\s+", "", normalized_text)
    for pattern in WHISPER_HALLUCINATION_PATTERNS:
        pattern_lower = pattern.lower()
        if pattern_lower in normalized_text or re.sub(r"\s+", "", pattern_lower) in compact_lower:
            return True

    unwanted_count = len(UNWANTED_SCRIPT_RE.findall(text)) + text.count("\ufffd")
    unwanted_ratio = unwanted_count / max(len(compact_text), 1)
    avg_logprob = segment.get("avg_logprob")
    no_speech_prob = segment.get("no_speech_prob") or 0.0
    compression_ratio = segment.get("compression_ratio")

    if no_speech_prob > 0.85:
        return True
    if avg_logprob is not None and avg_logprob < -1.0 and no_speech_prob > 0.35:
        return True
    if compression_ratio is not None and compression_ratio > 2.6:
        return True
    if unwanted_ratio > 0.35:
        return True

    cleaned_text = clean_transcript_text(text)
    return not MEANINGFUL_TEXT_RE.search(cleaned_text)


async def send_progress(message: str, progress: int, status: str = "processing"):
    """진행 상황 메시지를 생성합니다."""
    data = {
        "message": message,
        "progress": progress,
        "status": status
    }
    return f"data: {json.dumps(data)}\n\n"


ProgressCallback = Callable[[int, str], Awaitable[None]]


async def report_progress(callback: Optional[ProgressCallback], progress: int, message: str) -> None:
    if callback:
        await callback(max(0, min(int(progress), 100)), message)


async def extract_audio_from_video_async(video_path: str, audio_path: str) -> bool:
    """영상/음성 파일에서 Whisper 최적화 오디오(16kHz, Mono)를 추출합니다 (비동기 스레드 실행)."""
    def _extract():
        try:
            export_preprocessed_audio(video_path, audio_path)
            return True
        except Exception as e:
            print(f"오디오 전처리 오류: {e}")
            return False
            
    return await asyncio.to_thread(_extract)


async def transcribe_audio_async_generator(audio_path: str, language: str = "ko"):
    """Whisper를 사용하여 오디오를 텍스트로 변환합니다. 무음 구간을 제외하고 각 구간에 타임스탬프를 추가합니다."""
    try:
        # CPU 작업은 GPU 큐 밖에서 먼저 준비합니다.
        audio = await asyncio.to_thread(AudioSegment.from_file, audio_path)
        chunks = build_transcription_ranges(audio)
        if not chunks:
            yield {"type": "result", "text": ""}
            return

        full_text_with_timestamps = []
        srt_entries = []
        skipped_segments = 0
        decode_options = {}
        if WHISPER_BEAM_SIZE > 1:
            decode_options["beam_size"] = WHISPER_BEAM_SIZE

        yield {"type": "waiting", "total": len(chunks)}
        async with transcription_semaphore:
            yield {"type": "gpu_start", "total": len(chunks)}
            for i, (chunk_start_ms, chunk_end_ms) in enumerate(chunks):
                # 진행 상황 전달
                yield {"type": "progress", "current": i + 1, "total": len(chunks)}

                chunk = audio[chunk_start_ms:chunk_end_ms]
                chunk_samples = audiosegment_to_whisper_array(chunk)

                # asyncio.to_thread를 사용하여 CPU/GPU 작업을 별도 스레드에서 실행
                result = await asyncio.to_thread(
                    model.transcribe,
                    chunk_samples,
                    language=language,
                    fp16=(device == "cuda"),
                    verbose=False,
                    initial_prompt=KOREAN_TRANSCRIPTION_PROMPT,
                    temperature=0.0,
                    condition_on_previous_text=False,
                    compression_ratio_threshold=2.4,
                    logprob_threshold=-1.0,
                    no_speech_threshold=0.55,
                    hallucination_silence_threshold=2.0,
                    **decode_options,
                )

                # 결과에서 segments를 추출하여 타임스탬프와 함께 포맷팅
                chunk_offset_seconds = chunk_start_ms / 1000.0

                for segment in result.get("segments", []):
                    raw_segment_text = segment.get("text", "").strip()
                    if should_skip_segment(segment, raw_segment_text):
                        skipped_segments += 1
                        continue

                    segment_text = clean_transcript_text(raw_segment_text)
                    if segment_text:
                        # 청크 오프셋을 현재 세그먼트의 시작/끝 시간에 더함
                        absolute_start_time = chunk_offset_seconds + segment.get("start", 0)
                        absolute_end_time = chunk_offset_seconds + segment.get("end", 0)

                        formatted_timestamp = format_time(absolute_start_time)
                        if full_text_with_timestamps and full_text_with_timestamps[-1].endswith(f"\n{segment_text}"):
                            continue
                        full_text_with_timestamps.append(
                            f"[{formatted_timestamp}]\n{segment_text}"
                        )
                        srt_entries.append(
                            format_srt_entry(
                                len(srt_entries) + 1,
                                absolute_start_time,
                                absolute_end_time,
                                segment_text,
                            )
                        )

            if skipped_segments:
                print(f"음성 인식 후처리: 낮은 품질 세그먼트 {skipped_segments}개 제외")
                        
            # 최종 결과로 타임스탬프가 포함된 텍스트를 반환
            yield {
                "type": "result",
                "text": "\n\n".join(full_text_with_timestamps),
                "srt_text": "\n\n".join(srt_entries),
            }

    except Exception as e:
        print(f"음성 인식 오류: {e}")
        yield {"type": "error", "error": str(e)}


async def summarize_with_gemini(text: str, summary_type: str = "general") -> Optional[str]:
    """Gemini API로 텍스트를 요약합니다."""
    if not gemini_text_client or not gemini_api_key:
        return "⚠ Gemini API 키가 설정되지 않았습니다. 설정에서 API 키를 입력해주세요."
    
    try:
        prompts = {
            "general": f"""다음 텍스트를 명확하고 간결하게 요약해주세요. 
핵심 내용을 3-5개의 주요 포인트로 정리하세요.

텍스트:
{text}

요약:""",
            
            "meeting": f"""다음 회의 내용을 회의록 형식으로 정리해주세요:

[원본]
{text}

[회의록 형식]
## 📋 회의 개요

## 💬 주요 논의 사항
- 

## ✅ 결정 사항
- 

## 📌 향후 계획
- 

## 🔔 기타 사항
- """,
            
            "lecture": f"""다음 강의 내용을 학습 노트 형식으로 요약해주세요:

[강의 내용]
{text}

[학습 노트]
## 📚 핵심 개념
- 

## 💡 주요 내용
1. 

## 📝 예시/사례
- 

## 🎯 핵심 요점
- """,
            
            "youtube": f"""다음 영상 내용을 유튜브 요약 형식으로 정리해주세요:

[영상 내용]
{text}

[요약]
## 🎬 영상 개요
- 

## ⏱ 주요 내용
- 

## 💎 핵심 메시지
- 

## 📌 타임라인 요약
- """,
            
            "conversation": f"""다음 대화 내용을 정리해주세요:

[대화 내용]
{text}

[정리]
## 💬 대화 주제
- 

## 📝 주요 토픽
1. 

## 🗣 핵심 의견
- 

## 📌 결론
- """
        }
        
        prompt = prompts.get(summary_type, prompts["general"])
        
        # Gemini API 호출
        return await asyncio.to_thread(generate_gemini_text, prompt, "summary")
        
    except Exception as e:
        print(f"Gemini 요약 오류: {e}")
        return f"요약 생성 중 오류가 발생했습니다: {str(e)}"

TTS_VOICES = [
    {"name": "Kore", "label": "Kore - Firm", "default_ko": True},
    {"name": "Puck", "label": "Puck - Upbeat", "default_en": True},
    {"name": "Zephyr", "label": "Zephyr - Bright"},
    {"name": "Charon", "label": "Charon - Informative"},
    {"name": "Fenrir", "label": "Fenrir - Excitable"},
    {"name": "Leda", "label": "Leda - Youthful"},
    {"name": "Orus", "label": "Orus - Firm"},
    {"name": "Aoede", "label": "Aoede - Breezy"},
    {"name": "Callirrhoe", "label": "Callirrhoe - Easy-going"},
    {"name": "Autonoe", "label": "Autonoe - Bright"},
    {"name": "Enceladus", "label": "Enceladus - Breathy"},
    {"name": "Iapetus", "label": "Iapetus - Clear"},
    {"name": "Umbriel", "label": "Umbriel - Easy-going"},
    {"name": "Algieba", "label": "Algieba - Smooth"},
    {"name": "Despina", "label": "Despina - Smooth"},
    {"name": "Erinome", "label": "Erinome - Clear"},
    {"name": "Algenib", "label": "Algenib - Gravelly"},
    {"name": "Rasalgethi", "label": "Rasalgethi - Informative"},
    {"name": "Laomedeia", "label": "Laomedeia - Upbeat"},
    {"name": "Achernar", "label": "Achernar - Soft"},
    {"name": "Alnilam", "label": "Alnilam - Firm"},
    {"name": "Schedar", "label": "Schedar - Even"},
    {"name": "Gacrux", "label": "Gacrux - Mature"},
    {"name": "Pulcherrima", "label": "Pulcherrima - Forward"},
    {"name": "Achird", "label": "Achird - Friendly"},
    {"name": "Zubenelgenubi", "label": "Zubenelgenubi - Casual"},
    {"name": "Vindemiatrix", "label": "Vindemiatrix - Gentle"},
    {"name": "Sadachbia", "label": "Sadachbia - Lively"},
    {"name": "Sadaltager", "label": "Sadaltager - Knowledgeable"},
    {"name": "Sulafat", "label": "Sulafat - Warm"},
]

CLOUD_TTS_VOICES = [
    {"name": "ko-KR-Neural2-A", "label": "ko-KR-Neural2-A", "default_ko": True, "language_code": "ko-KR"},
    {"name": "ko-KR-Neural2-B", "label": "ko-KR-Neural2-B", "language_code": "ko-KR"},
    {"name": "ko-KR-Neural2-C", "label": "ko-KR-Neural2-C", "language_code": "ko-KR"},
    {"name": "en-US-Neural2-D", "label": "en-US-Neural2-D", "default_en": True, "language_code": "en-US"},
    {"name": "en-US-Neural2-A", "label": "en-US-Neural2-A", "language_code": "en-US"},
    {"name": "en-US-Neural2-C", "label": "en-US-Neural2-C", "language_code": "en-US"},
    {"name": "en-US-Neural2-E", "label": "en-US-Neural2-E", "language_code": "en-US"},
    {"name": "en-US-Neural2-F", "label": "en-US-Neural2-F", "language_code": "en-US"},
]

VOICE_SAMPLE_TEXT = "안녕하세요? 저는 AI 모델입니다. Hello? I am AI Speech Model"
VOICE_SAMPLE_STYLE_PROMPT = "Read this short Korean and English voice sample naturally, clearly, and warmly."


def active_tts_provider() -> str:
    return "gemini" if TTS_PROVIDER in {"gemini", "gemini_api"} else "google_cloud"


def provider_for_voice_name(voice_name: Optional[str]) -> Optional[str]:
    if not voice_name:
        return None
    if voice_name in {voice["name"] for voice in TTS_VOICES}:
        return "gemini"
    if voice_name in {voice["name"] for voice in CLOUD_TTS_VOICES}:
        return "google_cloud"
    return None


def normalize_tts_provider(language: str, tts_provider: Optional[str] = None, voice_name: Optional[str] = None) -> str:
    inferred_provider = provider_for_voice_name(voice_name) if not tts_provider else None
    provider = (tts_provider or inferred_provider or active_tts_provider() or "gemini").lower().strip()
    aliases = {
        "gemini_api": "gemini",
        "vertex": "gemini",
        "vertex_ai": "gemini",
        "google": "google_cloud",
        "cloud": "google_cloud",
        "google_cloud_tts": "google_cloud",
    }
    provider = aliases.get(provider, provider)
    if provider not in {"google_cloud", "gemini"}:
        provider = "gemini"
    return provider


def normalize_tts_selection(language: str, tts_provider: Optional[str] = None, voice_name: Optional[str] = None) -> Tuple[str, str]:
    provider = normalize_tts_provider(language, tts_provider, voice_name)
    return provider, normalize_voice_name(language, voice_name, provider)


def voices_for_provider(provider: str) -> List[Dict]:
    if provider == "gemini":
        return TTS_VOICES
    return CLOUD_TTS_VOICES


def voice_sample_providers() -> Dict[str, List[Dict]]:
    return {
        "gemini": TTS_VOICES,
    }


def validate_voice_sample(provider: str, voice_name: str) -> Tuple[str, Dict]:
    provider = (provider or "").lower().strip()
    providers = voice_sample_providers()
    if provider not in providers:
        raise HTTPException(status_code=400, detail="Unsupported sample provider.")
    voice = next((item for item in providers[provider] if item.get("name") == voice_name), None)
    if not voice:
        raise HTTPException(status_code=404, detail="Voice sample target was not found.")
    return provider, voice


def voice_sample_path(provider: str, voice_name: str) -> Path:
    provider, _ = validate_voice_sample(provider, voice_name)
    return VOICE_SAMPLE_DIR / f"{sanitize_output_name(provider)}_{sanitize_output_name(voice_name)}.mp3"


def voice_sample_language(provider: str) -> str:
    return "ko"


def voice_sample_status(provider: str, voice: Dict) -> Dict:
    path = voice_sample_path(provider, voice["name"])
    exists = path.exists()
    return {
        "provider": provider,
        "voice_name": voice["name"],
        "label": voice.get("label") or voice["name"],
        "exists": exists,
        "sample_url": f"/api/tts/voice-samples/{provider}/{voice['name']}" if exists else "",
        "filename": path.name,
    }


async def generate_voice_sample(provider: str, voice_name: str, force: bool = False) -> Dict:
    provider, voice = validate_voice_sample(provider, voice_name)
    path = voice_sample_path(provider, voice_name)
    if path.exists() and not force:
        return voice_sample_status(provider, voice)
    await synthesize_audio_from_text(
        VOICE_SAMPLE_TEXT,
        voice_sample_language(provider),
        path,
        voice_name=voice_name,
        style_prompt=VOICE_SAMPLE_STYLE_PROMPT,
        tts_provider=provider,
    )
    return voice_sample_status(provider, voice)


def defaults_for_provider(provider: str) -> Dict:
    voices = voices_for_provider(provider)
    defaults = {}
    for language, key in [("ko", "default_ko"), ("en", "default_en")]:
        default = next((voice["name"] for voice in voices if voice.get(key)), None)
        if default:
            defaults[language] = default
    return defaults


def get_active_tts_voices() -> List[Dict]:
    return voices_for_provider(active_tts_provider())


def default_voice_for_language(language: str, tts_provider: Optional[str] = None) -> str:
    language = (language or "ko").lower()
    provider = normalize_tts_provider(language, tts_provider)
    voices = voices_for_provider(provider)
    default_key = "default_ko" if language == "ko" else "default_en"
    for voice in voices:
        if voice.get(default_key):
            return voice["name"]
    return voices[0]["name"]


def extract_aspect_ratio_from_text(text: str) -> Optional[str]:
    match = ASPECT_RATIO_RE.search(text or "")
    return match.group(1) if match else None


def resolve_ai_video_aspect_ratio(image_style: str, visual_mode: Optional[str] = None, aspect_ratio: Optional[str] = None) -> Tuple[str, Optional[str]]:
    requested = aspect_ratio if aspect_ratio in (IMAGE_SUPPORTED_ASPECT_RATIOS | VEO_SUPPORTED_ASPECT_RATIOS) else None
    requested = requested or extract_aspect_ratio_from_text(image_style)
    mode = normalize_ai_video_visual_mode(visual_mode)
    if mode == "veo":
        if requested in VEO_SUPPORTED_ASPECT_RATIOS:
            return requested, None
        if requested:
            return VEO_ASPECT_RATIO if VEO_ASPECT_RATIO in VEO_SUPPORTED_ASPECT_RATIOS else "9:16", (
                f"Veo supports only 9:16 and 16:9. Requested {requested} was mapped to "
                f"{VEO_ASPECT_RATIO if VEO_ASPECT_RATIO in VEO_SUPPORTED_ASPECT_RATIOS else '9:16'}."
            )
        return VEO_ASPECT_RATIO if VEO_ASPECT_RATIO in VEO_SUPPORTED_ASPECT_RATIOS else "9:16", None
    if requested in IMAGE_SUPPORTED_ASPECT_RATIOS:
        return requested, None
    return AI_VIDEO_IMAGE_ASPECT_RATIO, None


def sanitize_output_name(filename: str) -> str:
    stem = Path(filename or "output").stem
    stem = re.sub(r"[^\w가-힣.-]+", "_", stem, flags=re.UNICODE).strip("._")
    return stem or "output"


def get_srt_for_language(file: Dict, language: str, srt_source: Optional[str] = None) -> str:
    language = (language or "ko").lower()
    if srt_source == "original":
        return file.get("srt_text") or ""
    if srt_source == "corrected":
        return file.get("corrected_srt_text") or file.get("srt_text") or ""
    if srt_source == "english":
        return file.get("english_srt_text") or ""
    if language == "en":
        return file.get("english_srt_text") or ""
    if file.get("english_srt_text") and not (file.get("srt_text") or file.get("corrected_srt_text")):
        return file.get("english_srt_text") or ""
    return file.get("corrected_srt_text") or file.get("srt_text") or ""


def normalize_voice_name(language: str, voice_name: Optional[str], tts_provider: Optional[str] = None) -> str:
    provider = normalize_tts_provider(language, tts_provider, voice_name)
    default_voice = default_voice_for_language(language, provider)
    if not voice_name:
        return default_voice
    valid_voice_names = {voice["name"] for voice in voices_for_provider(provider)}
    return voice_name if voice_name in valid_voice_names else default_voice


def artifact_api_response(artifact: Dict) -> Dict:
    metadata = artifact.get("metadata") or {}
    return {
        "success": True,
        "artifact": artifact,
        "artifact_id": artifact["id"],
        "filename": artifact.get("filename", ""),
        "duration_ms": metadata.get("duration_ms"),
        "download_url": f"/api/artifacts/{artifact['id']}/download",
    }


def prepare_file_for_api(file: Dict, include_original: bool = False) -> Dict:
    if file.get("thumbnail_path"):
        file["thumbnail_url"] = f"/api/files/{file['id']}/thumbnail"
    else:
        file["thumbnail_url"] = None
    media_path = Path(file.get("media_path") or "")
    file["media_url"] = f"/api/files/{file['id']}/media" if media_path.exists() else None
    if not include_original:
        if len(file.get("original_text", "")) > 200:
            file["text_preview"] = file["original_text"][:200] + "..."
        else:
            file["text_preview"] = file.get("original_text", "")
        file.pop("original_text", None)
    return file


def require_gemini_ready():
    if not gemini_text_client or not gemini_api_key:
        raise HTTPException(status_code=400, detail="Gemini API key is not configured.")


def require_tts_ready(tts_provider: Optional[str] = None, language: str = "ko"):
    provider = normalize_tts_provider(language, tts_provider)
    if provider == "google_cloud":
        if cloud_texttospeech is None:
            raise HTTPException(status_code=500, detail="google-cloud-texttospeech package is not installed. Run pip install -r requirements.txt.")
        return
    require_gemini_ready()
    if google_genai is None or google_genai_types is None:
        raise HTTPException(status_code=500, detail="google-genai package is not installed. Run pip install -r requirements.txt.")
    if gemini_tts_client is None:
        raise HTTPException(status_code=400, detail="Gemini TTS client is not configured. Save the Gemini API key again.")


async def translate_srt_to_english(srt_text: str) -> str:
    require_gemini_ready()
    cues = parse_srt(srt_text)
    if not cues:
        raise HTTPException(status_code=400, detail="No valid Korean SRT cues found.")
    source_items = [{"index": cue["index"], "text": cue["text"]} for cue in cues]
    prompt = (
        "Translate the following Korean subtitle cue texts into natural English. "
        "Return JSON only as an array of objects with index and text. "
        "Do not add, remove, merge, split, or reorder items. Preserve line breaks only when useful.\n\n"
        f"{json.dumps(source_items, ensure_ascii=False)}"
    )
    raw_text = (await asyncio.to_thread(generate_gemini_text, prompt, "correct_ko")).strip()
    raw_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text, flags=re.IGNORECASE | re.DOTALL).strip()
    try:
        translated_items = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f"Translation response was not valid JSON: {exc}")
    translated_by_index = {
        int(item.get("index")): str(item.get("text", "")).strip()
        for item in translated_items
        if isinstance(item, dict) and item.get("index") is not None
    }
    return build_srt(cues, [translated_by_index.get(cue["index"], cue["text"]) for cue in cues])


def write_wave_file(path: Path, pcm: bytes, channels: int = 1, rate: int = 24000, sample_width: int = 2) -> None:
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(rate)
        wav_file.writeframes(pcm)


def extract_tts_pcm(response) -> bytes:
    part = response.candidates[0].content.parts[0]
    inline_data = getattr(part, "inline_data", None) or getattr(part, "inlineData", None)
    data = getattr(inline_data, "data", None)
    if isinstance(data, bytes):
        return data
    if isinstance(data, str):
        return base64.b64decode(data)
    raise ValueError("Gemini TTS response did not include audio data.")


def retry_delay_seconds_from_error(message: str, attempt: int) -> float:
    retry_match = re.search(r"retryDelay['\"]?\s*:\s*['\"]?(\d+(?:\.\d+)?)s", message, re.IGNORECASE)
    if retry_match:
        return float(retry_match.group(1))
    retry_match = re.search(r"retry in (\d+(?:\.\d+)?)s", message, re.IGNORECASE)
    if retry_match:
        return float(retry_match.group(1))
    return GEMINI_TTS_RETRY_BASE_SECONDS * max(attempt, 1)


def is_quota_error(message: str) -> bool:
    return "RESOURCE_EXHAUSTED" in message or "Quota exceeded" in message or "429" in message


async def generate_tts_wav(text: str, language: str, wav_path: Path, voice_name: Optional[str] = None, style_prompt: Optional[str] = None, tts_provider: Optional[str] = None) -> Dict:
    language = (language or "ko").lower()
    provider, voice_name = normalize_tts_selection(language, tts_provider, voice_name)
    require_tts_ready(provider, language)
    print(f"TTS dispatch provider={provider} voice={voice_name} language={language}")
    if provider == "google_cloud":
        return await generate_cloud_tts_wav(text, language, wav_path, voice_name)
    return await generate_gemini_tts_wav(text, language, wav_path, voice_name, style_prompt=style_prompt)


async def generate_gemini_tts_wav(text: str, language: str, wav_path: Path, voice_name: str, style_prompt: Optional[str] = None) -> Dict:
    prompt_language = "Korean" if language == "ko" else "English"
    style = (style_prompt or "Read clearly at a steady narration pace.").strip()
    prompt = f"{style}\nRead the following {prompt_language} text exactly:\n{text.strip()}"
    last_quota_error = ""
    for attempt in range(1, GEMINI_TTS_MAX_RETRIES + 2):
        try:
            response = await asyncio.to_thread(
                gemini_tts_client.models.generate_content,
                model=GEMINI_TTS_MODEL,
                contents=prompt,
                config=google_genai_types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=google_genai_types.SpeechConfig(
                        voice_config=google_genai_types.VoiceConfig(
                            prebuilt_voice_config=google_genai_types.PrebuiltVoiceConfig(voice_name=voice_name)
                        )
                    ),
                ),
            )
            write_wave_file(wav_path, extract_tts_pcm(response))
            usage = getattr(response, "usage_metadata", None)
            input_tokens = ai_usage.usage_metadata_value(usage, "prompt_token_count", "input_token_count")
            total_tokens = ai_usage.usage_metadata_value(usage, "total_token_count")
            if not input_tokens:
                input_tokens = ai_usage.estimate_tokens_from_text(prompt)
            if not total_tokens:
                total_tokens = input_tokens
            estimated_cost = ai_usage.estimate_gemini_tts_cost(input_tokens)
            ai_usage.record_ai_usage(
                provider="gemini",
                model=GEMINI_TTS_MODEL,
                operation="tts",
                input_tokens=input_tokens,
                total_tokens=total_tokens,
                characters=len(text or ""),
                request_count=1,
                estimated_cost_usd=estimated_cost,
                metadata={"voice_name": voice_name, "language": language, "usage_source": "api" if usage else "estimated_tokens"},
            )
            return {
                "input_tokens": input_tokens,
                "output_tokens": 0,
                "total_tokens": total_tokens,
                "characters": len(text or ""),
                "request_count": 1,
                "estimated_cost_usd": estimated_cost,
            }
        except Exception as exc:
            message = str(exc)
            if is_quota_error(message):
                last_quota_error = message
                if attempt <= GEMINI_TTS_MAX_RETRIES:
                    delay = retry_delay_seconds_from_error(message, attempt)
                    print(f"Gemini TTS quota hit. retrying in {delay:.1f}s ({attempt}/{GEMINI_TTS_MAX_RETRIES})")
                    await asyncio.sleep(delay)
                    continue
                raise HTTPException(
                    status_code=429,
                    detail=(
                        "Gemini TTS Vertex AI 모델별 분당 요청 쿼터를 초과했습니다. "
                        f"model={GEMINI_TTS_MODEL}, location={VERTEX_AI_LOCATION}, voice={voice_name}, "
                        f"sync_mode={TTS_SYNC_MODE}. 잠시 후 다시 시도하거나 Vertex AI 쿼터 증설을 요청하세요. "
                        f"raw={last_quota_error}"
                    ),
                )
            if "INVALID_ARGUMENT" in message or "invalid argument" in message.lower():
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Gemini TTS 요청값이 현재 Vertex AI 설정과 맞지 않습니다. "
                        f"model={GEMINI_TTS_MODEL}, location={VERTEX_AI_LOCATION}, voice={voice_name}. "
                        "us-central1 같은 지역 Vertex AI에서는 gemini-2.5-flash-tts를 사용하고, "
                        "gemini-3.1-flash-tts-preview를 쓰려면 지원되는 global/지역 설정으로 바꿔야 합니다."
                    ),
                )
            raise


def cloud_language_code(language: str) -> str:
    return "ko-KR" if (language or "ko").lower() == "ko" else "en-US"


async def generate_cloud_tts_wav(text: str, language: str, wav_path: Path, voice_name: str) -> Dict:
    def synthesize() -> bytes:
        client = cloud_texttospeech.TextToSpeechClient()
        synthesis_input = cloud_texttospeech.SynthesisInput(text=text.strip())
        voice = cloud_texttospeech.VoiceSelectionParams(
            language_code=cloud_language_code(language),
            name=voice_name,
        )
        audio_config = cloud_texttospeech.AudioConfig(
            audio_encoding=cloud_texttospeech.AudioEncoding.LINEAR16,
            speaking_rate=1.0,
        )
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )
        return response.audio_content

    wav_path.write_bytes(await asyncio.to_thread(synthesize))
    characters = len((text or "").strip())
    estimated_cost = ai_usage.estimate_google_cloud_tts_cost(characters)
    ai_usage.record_ai_usage(
        provider="google_cloud_tts",
        model=voice_name,
        operation="tts",
        characters=characters,
        request_count=1,
        estimated_cost_usd=estimated_cost,
        metadata={"voice_name": voice_name, "language": language, "usage_source": "characters"},
    )
    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "characters": characters,
        "request_count": 1,
        "estimated_cost_usd": estimated_cost,
    }


def fit_audio_to_duration(audio: AudioSegment, duration_ms: int) -> AudioSegment:
    duration_ms = max(duration_ms, 250)
    if len(audio) <= duration_ms:
        audio = apply_short_fades(audio)
        return audio + AudioSegment.silent(duration=duration_ms - len(audio))
    speed = min(max(len(audio) / duration_ms, 1.01), 2.0)
    try:
        fitted = stretch_audio_with_ffmpeg(audio, speed)
    except Exception:
        fitted = audio
    if len(fitted) > duration_ms:
        fitted = fitted[:duration_ms]
    fitted = apply_short_fades(fitted)
    return fitted + AudioSegment.silent(duration=max(duration_ms - len(fitted), 0))


def build_atempo_filter(speed: float) -> str:
    speed = max(float(speed), 0.5)
    parts = []
    remaining = speed
    while remaining > 2.0:
        parts.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        parts.append("atempo=0.5")
        remaining /= 0.5
    parts.append(f"atempo={remaining:.6f}")
    return ",".join(parts)


def stretch_audio_with_ffmpeg(audio: AudioSegment, speed: float) -> AudioSegment:
    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = Path(temp_dir) / "input.wav"
        output_path = Path(temp_dir) / "output.wav"
        audio.export(input_path, format="wav")
        command = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-filter:a", build_atempo_filter(speed),
            "-vn",
            str(output_path),
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg atempo failed: {result.stderr[-1000:]}")
        return AudioSegment.from_file(output_path, format="wav").set_channels(audio.channels)


def apply_short_fades(audio: AudioSegment, fade_ms: int = 8) -> AudioSegment:
    if len(audio) <= fade_ms * 2:
        return audio
    return audio.fade_in(fade_ms).fade_out(fade_ms)


def build_tts_cue_groups(cues: List[Dict], max_chars: int = TTS_GROUP_MAX_CHARS, max_duration_ms: int = TTS_GROUP_MAX_DURATION_MS, max_gap_ms: int = TTS_GROUP_MAX_GAP_MS) -> List[List[Dict]]:
    groups = []
    current = []
    current_chars = 0
    for cue in cues:
        if not cue.get("text", "").strip():
            continue
        cue_text_len = len(cue["text"].strip())
        should_split = False
        if current:
            group_start_ms = int(current[0]["start"] * 1000)
            new_end_ms = int(cue["end"] * 1000)
            gap_ms = int((cue["start"] - current[-1]["end"]) * 1000)
            should_split = (
                current_chars + cue_text_len > max_chars
                or new_end_ms - group_start_ms > max_duration_ms
                or gap_ms > max_gap_ms
            )
        if should_split:
            groups.append(current)
            current = []
            current_chars = 0
        current.append(cue)
        current_chars += cue_text_len
    if current:
        groups.append(current)
    return groups


def text_for_tts_group(group: List[Dict]) -> str:
    return "\n".join(cue["text"].strip() for cue in group if cue.get("text", "").strip())


def tts_groups_for_mode(cues: List[Dict]) -> List[List[Dict]]:
    non_empty_cues = [cue for cue in cues if cue.get("text", "").strip()]
    if TTS_SYNC_MODE == "grouped":
        return build_tts_cue_groups(non_empty_cues)
    return [[cue] for cue in non_empty_cues]


async def synthesize_audio_from_srt(
    srt_text: str,
    language: str,
    output_path: Path,
    voice_name: Optional[str] = None,
    style_prompt: Optional[str] = None,
    tts_provider: Optional[str] = None,
    progress_callback: Optional[ProgressCallback] = None,
    progress_start: int = 10,
    progress_end: int = 85,
) -> Dict:
    cues = parse_srt(srt_text)
    if not cues:
        raise HTTPException(status_code=400, detail="No valid SRT cues found.")
    total_duration_ms = int(max(cue["end"] for cue in cues) * 1000)
    timeline = AudioSegment.silent(duration=total_duration_ms).set_channels(2)
    temp_paths = []
    groups = tts_groups_for_mode(cues)
    provider, normalized_voice = normalize_tts_selection(language, tts_provider, voice_name)
    usage_summary = {
        "ai_input_tokens": 0,
        "ai_output_tokens": 0,
        "ai_total_tokens": 0,
        "ai_characters": 0,
        "ai_request_count": 0,
        "ai_estimated_cost_usd": 0.0,
    }
    try:
        await report_progress(progress_callback, progress_start, f"{provider} 음성 엔진 준비 중 ({normalized_voice})")
        for index, group in enumerate(groups, 1):
            current_progress = progress_start + int(((index - 1) / max(len(groups), 1)) * max(progress_end - progress_start, 1))
            group_start = format_srt_time(group[0]["start"])
            group_end = format_srt_time(group[-1]["end"])
            await report_progress(progress_callback, current_progress, f"{provider} 음성 생성 중 ({index}/{len(groups)} 구간 · {group_start}~{group_end})")
            wav_path = OUTPUT_DIR / f"{uuid.uuid4()}.wav"
            temp_paths.append(wav_path)
            usage = await generate_tts_wav(text_for_tts_group(group), language, wav_path, voice_name=voice_name, style_prompt=style_prompt, tts_provider=tts_provider)
            usage = usage or {}
            usage_summary["ai_input_tokens"] += int(usage.get("input_tokens") or 0)
            usage_summary["ai_output_tokens"] += int(usage.get("output_tokens") or 0)
            usage_summary["ai_total_tokens"] += int(usage.get("total_tokens") or 0)
            usage_summary["ai_characters"] += int(usage.get("characters") or 0)
            usage_summary["ai_request_count"] += int(usage.get("request_count") or 0)
            usage_summary["ai_estimated_cost_usd"] += float(usage.get("estimated_cost_usd") or 0)
            await report_progress(progress_callback, min(current_progress + 1, progress_end), f"구간 길이 보정 및 타임라인 배치 중 ({index}/{len(groups)})")
            with open(wav_path, "rb") as wav_file:
                segment = AudioSegment.from_file(wav_file, format="wav").set_channels(2)
            group_start_ms = int(group[0]["start"] * 1000)
            group_duration_ms = int((group[-1]["end"] - group[0]["start"]) * 1000)
            segment = fit_audio_to_duration(segment, group_duration_ms)
            timeline = timeline.overlay(segment, position=group_start_ms)
        await report_progress(progress_callback, progress_end, "MP3 타임라인 내보내는 중")
        with open(output_path, "wb") as mp3_file:
            timeline.export(mp3_file, format="mp3", bitrate="192k")
    finally:
        for temp_path in temp_paths:
            try:
                temp_path.unlink()
            except OSError:
                pass
    return {
        "cue_count": len(cues),
        "tts_request_count": len(groups),
        "tts_sync_mode": "grouped" if TTS_SYNC_MODE == "grouped" else "cue",
        "duration_ms": len(timeline),
        "voice_name": normalized_voice,
        "tts_provider": provider,
        "tts_device": "remote",
        "tts_speed": 1.0,
        "style_prompt": style_prompt or "",
        **usage_summary,
    }


async def synthesize_audio_from_text(script: str, language: str, output_path: Path, voice_name: Optional[str] = None, style_prompt: Optional[str] = None, tts_provider: Optional[str] = None, progress_callback: Optional[ProgressCallback] = None) -> Dict:
    wav_path = OUTPUT_DIR / f"{uuid.uuid4()}.wav"
    try:
        await report_progress(progress_callback, 20, "음성 엔진 준비 중")
        usage = await generate_tts_wav(script, language, wav_path, voice_name=voice_name, style_prompt=style_prompt, tts_provider=tts_provider)
        await report_progress(progress_callback, 80, "MP3 파일 내보내는 중")
        with open(wav_path, "rb") as wav_file:
            audio = AudioSegment.from_file(wav_file, format="wav")
        with open(output_path, "wb") as mp3_file:
            audio.export(mp3_file, format="mp3", bitrate="192k")
        usage = usage or {}
        return {
            "cue_count": 0,
            "duration_ms": len(audio),
            "voice_name": normalize_tts_selection(language, tts_provider, voice_name)[1],
            "tts_provider": normalize_tts_selection(language, tts_provider, voice_name)[0],
            "tts_device": "remote",
            "tts_speed": 1.0,
            "style_prompt": style_prompt or "",
            "ai_input_tokens": int(usage.get("input_tokens") or 0),
            "ai_output_tokens": int(usage.get("output_tokens") or 0),
            "ai_total_tokens": int(usage.get("total_tokens") or 0),
            "ai_characters": int(usage.get("characters") or 0),
            "ai_request_count": int(usage.get("request_count") or 0),
            "ai_estimated_cost_usd": float(usage.get("estimated_cost_usd") or 0),
        }
    finally:
        try:
            wav_path.unlink()
        except OSError:
            pass


async def synthesize_script_audio(script: str, language: str, output_path: Path, voice_name: Optional[str] = None, style_prompt: Optional[str] = None, tts_provider: Optional[str] = None, progress_callback: Optional[ProgressCallback] = None) -> Dict:
    if parse_srt(script):
        return await synthesize_audio_from_srt(script, language, output_path, voice_name=voice_name, style_prompt=style_prompt, tts_provider=tts_provider, progress_callback=progress_callback)
    return await synthesize_audio_from_text(script, language, output_path, voice_name=voice_name, style_prompt=style_prompt, tts_provider=tts_provider, progress_callback=progress_callback)


def mux_video_with_audio(video_path: Path, audio_path: Path, output_path: Path) -> None:
    command = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"ffmpeg failed: {result.stderr[-1000:]}")


def pad_or_trim_video_to_duration(video_path: Path, duration_seconds: float, output_path: Path) -> None:
    duration = max(float(duration_seconds or 0), 0.1)
    command = [
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-i", str(video_path),
        "-t", f"{duration:.3f}",
        "-map", "0:v:0",
        "-an",
        "-c:v", "libx264",
        "-preset", AI_VIDEO_TRANSCODE_PRESET,
        "-crf", AI_VIDEO_TRANSCODE_CRF,
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"video duration normalization failed: {result.stderr[-1000:]}")


def media_type_for_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".mp4", ".m4v", ".mov"}:
        return "video/mp4"
    if suffix == ".webm":
        return "video/webm"
    if suffix == ".mp3":
        return "audio/mpeg"
    if suffix == ".wav":
        return "audio/wav"
    return "application/octet-stream"


def clamp_int(value, minimum: int, maximum: int, default: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))


def ass_time(seconds: float) -> str:
    seconds = max(float(seconds or 0), 0.0)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    whole_seconds = int(seconds % 60)
    centiseconds = int(round((seconds - int(seconds)) * 100))
    if centiseconds == 100:
        whole_seconds += 1
        centiseconds = 0
    if whole_seconds == 60:
        minutes += 1
        whole_seconds = 0
    if minutes == 60:
        hours += 1
        minutes = 0
    return f"{hours}:{minutes:02d}:{whole_seconds:02d}.{centiseconds:02d}"


def ass_color(hex_color: str, opacity: int = 100) -> str:
    color = (hex_color or "").strip().lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", color):
        color = "FFFFFF"
    red = color[0:2]
    green = color[2:4]
    blue = color[4:6]
    alpha = 255 - round(255 * max(0, min(100, int(opacity))) / 100)
    return f"&H{alpha:02X}{blue}{green}{red}".upper()


def ass_dialogue_text(text: str) -> str:
    return (
        (text or "")
        .replace("{", "｛")
        .replace("}", "｝")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\n", r"\N")
        .strip()
    )


def normalize_subtitle_style(style: Optional[SubtitleStyleRequest]) -> Dict:
    data = style.model_dump() if style else {}
    font_family = re.sub(r"[,;\r\n]", "", str(data.get("font_family") or "Arial")).strip() or "Arial"
    position = str(data.get("position") or "bottom").lower()
    if position not in {"top", "middle", "bottom"}:
        position = "bottom"
    background_enabled = bool(data.get("background_enabled", True))
    return {
        "font_family": font_family[:80],
        "font_size": clamp_int(data.get("font_size"), 16, 120, 48),
        "position": position,
        "text_color": data.get("text_color") or "#FFFFFF",
        "background_color": data.get("background_color") or "#000000",
        "background_opacity": clamp_int(data.get("background_opacity"), 0, 100, 60),
        "background_enabled": background_enabled,
        "outline_color": data.get("outline_color") or "#000000",
        "outline_width": clamp_int(data.get("outline_width"), 0, 10, 2),
        "shadow": clamp_int(data.get("shadow"), 0, 8, 1),
        "margin_v": clamp_int(data.get("margin_v"), 0, 240, 64),
    }


def build_ass_subtitles(
    srt_text: str,
    style: Optional[SubtitleStyleRequest] = None,
    play_res: Optional[Tuple[int, int]] = None,
) -> Tuple[str, Dict]:
    cues = parse_srt(srt_text)
    normalized = normalize_subtitle_style(style)
    play_res_x, play_res_y = play_res or (1920, 1080)
    alignment = {"bottom": 2, "middle": 5, "top": 8}[normalized["position"]]
    background_active = normalized["background_enabled"] and normalized["background_opacity"] > 0
    border_style = 3 if background_active else 1
    back_opacity = normalized["background_opacity"] if background_active else 0
    outline_color = (
        ass_color(normalized["background_color"], normalized["background_opacity"])
        if background_active
        else ass_color(normalized["outline_color"], 100)
    )
    style_line = ",".join([
        "Default",
        normalized["font_family"],
        str(normalized["font_size"]),
        ass_color(normalized["text_color"], 100),
        ass_color(normalized["text_color"], 100),
        outline_color,
        ass_color(normalized["background_color"], back_opacity),
        "-1", "0", "0", "0",
        "100", "100", "0", "0",
        str(border_style),
        str(normalized["outline_width"]),
        str(normalized["shadow"]),
        str(alignment),
        "80", "80", str(normalized["margin_v"]),
        "1",
    ])
    dialogue_lines = [
        f"Dialogue: 0,{ass_time(cue['start'])},{ass_time(cue['end'])},Default,,0,0,0,,{ass_dialogue_text(cue['text'])}"
        for cue in cues
    ]
    ass_text = "\n".join([
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {play_res_x}",
        f"PlayResY: {play_res_y}",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
        f"Style: {style_line}",
        "",
        "[Events]",
        "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
        *dialogue_lines,
        "",
    ])
    return ass_text, normalized


def burn_subtitles_into_video(source_video_path: Path, srt_text: str, output_path: Path, subtitle_style: Optional[SubtitleStyleRequest] = None) -> Dict:
    temp_ass_path = OUTPUT_DIR / f"subtitle_{uuid.uuid4().hex}.ass"
    try:
        play_res = video_utils.media_video_dimensions(source_video_path)
        ass_text, normalized_style = build_ass_subtitles(srt_text, subtitle_style, play_res=play_res)
        temp_ass_path.write_text(ass_text, encoding="utf-8")
        subtitle_filter = f"subtitles={temp_ass_path.name}"
        command = [
            "ffmpeg", "-y",
            "-i", str(source_video_path.resolve()),
            "-vf", subtitle_filter,
            "-c:v", "libx264",
            "-preset", AI_VIDEO_TRANSCODE_PRESET,
            "-crf", AI_VIDEO_TRANSCODE_CRF,
            "-c:a", "copy",
            "-movflags", "+faststart",
            str(output_path.resolve()),
        ]
        result = subprocess.run(command, cwd=str(OUTPUT_DIR.resolve()), capture_output=True, text=True)
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"subtitle video generation failed: {result.stderr[-1000:]}")
        return normalized_style
    finally:
        try:
            temp_ass_path.unlink()
        except OSError:
            pass


async def create_subtitle_video_artifact_for_file(file: Dict, language: str, srt_source: Optional[str] = None, subtitle_style: Optional[SubtitleStyleRequest] = None, progress_callback: Optional[ProgressCallback] = None) -> Dict:
    language = (language or "ko").lower()
    await report_progress(progress_callback, 18, "SRT 소스 확인 중")
    srt_text = get_srt_for_language(file, language, srt_source=srt_source)
    if not srt_text:
        raise HTTPException(status_code=400, detail=f"No {language} SRT is available.")

    cues = parse_srt(srt_text)
    await report_progress(progress_callback, 28, f"자막 타임라인 분석 중 ({len(cues)}개 구간)")
    duration_ms = int(max((cue["end"] for cue in cues), default=1.0) * 1000)
    base_name = sanitize_output_name(file.get("filename", "subtitle_video"))
    output_path = OUTPUT_DIR / f"{base_name}_{language}_subtitled_{uuid.uuid4().hex[:8]}.mp4"
    media_path = Path(file.get("media_path") or "")
    black_video_path = None
    try:
        if media_path.exists():
            source_video_path = media_path
            source_video = "original"
            await report_progress(progress_callback, 42, "원본 영상 확인 완료")
        else:
            await report_progress(progress_callback, 42, "원본 영상이 없어 검은 배경 영상 생성 중")
            black_video_path = OUTPUT_DIR / f"{base_name}_black_{uuid.uuid4().hex[:8]}.mp4"
            await asyncio.to_thread(create_black_video, duration_ms, black_video_path)
            source_video_path = black_video_path
            source_video = "black"
        await report_progress(progress_callback, 60, "자막 스타일 준비 중")
        await report_progress(progress_callback, 74, "ffmpeg로 영상에 자막을 입히는 중")
        normalized_style = await asyncio.to_thread(burn_subtitles_into_video, source_video_path, srt_text, output_path, subtitle_style)
        await report_progress(progress_callback, 92, "자막 영상 파일 저장 중")
    finally:
        if black_video_path:
            try:
                black_video_path.unlink()
            except OSError:
                pass

    metadata = {
        "duration_ms": duration_ms,
        "srt_source": srt_source or ("english" if language == "en" else ("corrected" if file.get("corrected_srt_text") else "original")),
        "source_video": source_video,
        "variant": "subtitle",
        "subtitle_style": normalized_style,
    }
    return db.create_artifact(file["id"], "subtitle_video", language, str(output_path), output_path.name, metadata)


async def create_audio_artifact_for_file(file: Dict, language: str, voice_name: Optional[str] = None, style_prompt: Optional[str] = None, srt_source: Optional[str] = None, tts_provider: Optional[str] = None, progress_callback: Optional[ProgressCallback] = None, progress_start: int = 10, progress_end: int = 85) -> Dict:
    language = (language or "ko").lower()
    tts_provider, voice_name = normalize_tts_selection(language, tts_provider, voice_name)
    await report_progress(progress_callback, progress_start, "SRT 소스 확인 중")
    srt_text = get_srt_for_language(file, language, srt_source=srt_source)
    if not srt_text:
        raise HTTPException(status_code=400, detail=f"No {language} SRT is available.")
    cue_count = len(parse_srt(srt_text))
    await report_progress(progress_callback, min(progress_start + 5, progress_end), f"SRT 타임라인 분석 완료 ({cue_count}개 구간)")
    base_name = sanitize_output_name(file.get("filename", "audio"))
    output_path = OUTPUT_DIR / f"{base_name}_{language}_{uuid.uuid4().hex[:8]}.mp3"
    context = ai_usage.AI_USAGE_CONTEXT.get() or {}
    token = ai_usage.AI_USAGE_CONTEXT.set({**context, "file_id": context.get("file_id") or file.get("id")})
    try:
        metadata = await synthesize_audio_from_srt(
            srt_text,
            language,
            output_path,
            voice_name=voice_name,
            style_prompt=style_prompt,
            tts_provider=tts_provider,
            progress_callback=progress_callback,
            progress_start=progress_start,
            progress_end=progress_end,
        )
    finally:
        ai_usage.AI_USAGE_CONTEXT.reset(token)
    metadata["srt_source"] = desired_srt_source(file, language, srt_source)
    return db.create_artifact(file["id"], "audio", language, str(output_path), output_path.name, metadata)


def desired_srt_source(file: Dict, language: str, srt_source: Optional[str]) -> str:
    if srt_source:
        return srt_source
    language = (language or "ko").lower()
    if language == "en" or (file.get("english_srt_text") and not (file.get("srt_text") or file.get("corrected_srt_text"))):
        return "english"
    return "corrected" if file.get("corrected_srt_text") else "original"


def find_reusable_audio_artifact(file: Dict, language: str, voice_name: Optional[str], srt_source: Optional[str], tts_provider: Optional[str] = None) -> Optional[Dict]:
    language = (language or "ko").lower()
    expected_provider = normalize_tts_provider(language, tts_provider, voice_name)
    expected_voice = normalize_voice_name(language, voice_name, expected_provider)
    expected_srt_source = desired_srt_source(file, language, srt_source)
    expected_sync_mode = "grouped" if TTS_SYNC_MODE == "grouped" else "cue"
    fallback = None
    for artifact in db.get_artifacts_for_file(file["id"]):
        if artifact.get("kind") != "audio" or artifact.get("language") != language:
            continue
        metadata = artifact.get("metadata") or {}
        artifact_path = Path(artifact.get("path") or "")
        if not artifact_path.exists():
            continue
        artifact_voice = metadata.get("voice_name")
        artifact_provider = metadata.get("tts_provider") or provider_for_voice_name(artifact_voice) or active_tts_provider()
        artifact_voice = artifact_voice or normalize_voice_name(language, None, artifact_provider)
        artifact_srt_source = metadata.get("srt_source") or desired_srt_source(file, language, None)
        artifact_sync_mode = metadata.get("tts_sync_mode") or "grouped"
        if artifact_sync_mode != expected_sync_mode:
            continue
        if artifact_provider != expected_provider:
            continue
        if artifact_voice == expected_voice and artifact_srt_source == expected_srt_source:
            return artifact
        if fallback is None and artifact_srt_source == expected_srt_source:
            fallback = artifact
    return fallback


def get_selected_audio_artifact(file: Dict, audio_artifact_id: Optional[str], language: str) -> Optional[Dict]:
    if not audio_artifact_id:
        return None
    artifact = db.get_artifact_by_id(audio_artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Selected audio artifact was not found.")
    if artifact.get("file_id") != file.get("id") or artifact.get("kind") != "audio":
        raise HTTPException(status_code=400, detail="Selected artifact is not an audio MP3 for this file.")
    if artifact.get("language") != (language or "ko").lower():
        raise HTTPException(status_code=400, detail="Selected audio language does not match the requested output language.")
    audio_path = Path(artifact.get("path") or "")
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Selected audio file is missing.")
    return artifact


async def create_video_artifact_for_file(file: Dict, language: str, voice_name: Optional[str] = None, style_prompt: Optional[str] = None, srt_source: Optional[str] = None, tts_provider: Optional[str] = None, audio_artifact_id: Optional[str] = None, require_existing_audio: bool = False, progress_callback: Optional[ProgressCallback] = None, progress_start: int = 10, progress_end: int = 90) -> Dict:
    language = (language or "ko").lower()
    srt_text = get_srt_for_language(file, language, srt_source=srt_source)
    if not srt_text:
        raise HTTPException(status_code=400, detail=f"No {language} SRT is available.")
    base_name = sanitize_output_name(file.get("filename", "video"))
    video_output_path = OUTPUT_DIR / f"{base_name}_{language}_dubbed_{uuid.uuid4().hex[:8]}.mp4"
    selected_audio_artifact = get_selected_audio_artifact(file, audio_artifact_id, language)
    if require_existing_audio and not selected_audio_artifact:
        raise HTTPException(status_code=400, detail="더빙 영상을 만들려면 먼저 생성된 MP3를 선택하세요.")
    if selected_audio_artifact:
        audio_artifact = selected_audio_artifact
        await report_progress(progress_callback, progress_start, "선택한 MP3 산출물 확인 완료")
    else:
        tts_provider, voice_name = normalize_tts_selection(language, tts_provider, voice_name)
        audio_artifact = find_reusable_audio_artifact(file, language, voice_name, srt_source, tts_provider=tts_provider)
    reused_audio = audio_artifact is not None
    if audio_artifact:
        if not selected_audio_artifact:
            await report_progress(progress_callback, progress_start, "기존 음성 산출물 재사용")
        audio_path = Path(audio_artifact["path"])
        metadata = dict(audio_artifact.get("metadata") or {})
    else:
        audio_artifact = await create_audio_artifact_for_file(
            file,
            language,
            voice_name=voice_name,
            style_prompt=style_prompt,
            srt_source=srt_source,
            tts_provider=tts_provider,
            progress_callback=progress_callback,
            progress_start=progress_start,
            progress_end=max(progress_start + 5, progress_end - 20),
        )
        audio_path = Path(audio_artifact["path"])
        metadata = dict(audio_artifact.get("metadata") or {})
    media_path = Path(file.get("media_path") or "")
    black_video_path = None
    if media_path.exists():
        source_video_path = media_path
        await report_progress(progress_callback, max(progress_start, progress_end - 22), "원본 영상 확인 완료")
    else:
        await report_progress(progress_callback, max(progress_start, progress_end - 18), "원본 영상이 없어 검은 배경 영상 생성 중")
        black_video_path = OUTPUT_DIR / f"{base_name}_black_{uuid.uuid4().hex[:8]}.mp4"
        await asyncio.to_thread(create_black_video, metadata["duration_ms"], black_video_path)
        source_video_path = black_video_path
    await report_progress(progress_callback, max(progress_start, progress_end - 10), "ffmpeg로 더빙 음성과 영상을 합치는 중")
    await asyncio.to_thread(mux_video_with_audio, source_video_path, audio_path, video_output_path)
    await report_progress(progress_callback, progress_end, "더빙 영상 파일 저장 중")
    if black_video_path:
        try:
            black_video_path.unlink()
        except OSError:
            pass
    metadata["srt_source"] = desired_srt_source(file, language, srt_source)
    metadata["source_video"] = "original" if media_path.exists() else "black"
    metadata["audio_artifact_id"] = audio_artifact["id"]
    metadata["reused_audio"] = reused_audio
    metadata["selected_audio_artifact_id"] = audio_artifact_id or ""
    return db.create_artifact(file["id"], "video", language, str(video_output_path), video_output_path.name, metadata)


async def create_captioned_dub_video_artifact_for_file(
    file: Dict,
    language: str,
    voice_name: Optional[str] = None,
    style_prompt: Optional[str] = None,
    srt_source: Optional[str] = None,
    subtitle_style: Optional[SubtitleStyleRequest] = None,
    tts_provider: Optional[str] = None,
    audio_artifact_id: Optional[str] = None,
    require_existing_audio: bool = False,
    progress_callback: Optional[ProgressCallback] = None,
    progress_start: int = 10,
    progress_end: int = 96,
) -> Dict:
    language = (language or "ko").lower()
    srt_text = get_srt_for_language(file, language, srt_source=srt_source)
    if not srt_text:
        raise HTTPException(status_code=400, detail=f"No {language} SRT is available.")

    base_name = sanitize_output_name(file.get("filename", "captioned_dub_video"))
    video_kwargs = {
        "voice_name": voice_name,
        "style_prompt": style_prompt,
        "srt_source": srt_source,
        "tts_provider": tts_provider,
    }
    if audio_artifact_id:
        video_kwargs["audio_artifact_id"] = audio_artifact_id
    if require_existing_audio:
        video_kwargs["require_existing_audio"] = require_existing_audio
    if progress_callback:
        def scaled(relative: int) -> int:
            return progress_start + int((max(0, min(relative, 100)) / 100) * max(progress_end - progress_start, 1))
        video_kwargs.update({
            "progress_callback": progress_callback,
            "progress_start": scaled(0),
            "progress_end": scaled(78),
        })
    dubbed_artifact = await create_video_artifact_for_file(file, language, **video_kwargs)
    output_path = OUTPUT_DIR / f"{base_name}_{language}_captioned_dub_{uuid.uuid4().hex[:8]}.mp4"
    def caption_progress(relative: int) -> int:
        return progress_start + int((max(0, min(relative, 100)) / 100) * max(progress_end - progress_start, 1))
    await report_progress(progress_callback, caption_progress(80), "더빙 영상 합성 완료, 자막 준비 중")
    await report_progress(progress_callback, caption_progress(84), "ASS 자막 스타일 생성 중")
    await report_progress(progress_callback, caption_progress(88), "ffmpeg로 더빙 영상에 자막을 입히는 중")
    normalized_style = await asyncio.to_thread(
        burn_subtitles_into_video,
        Path(dubbed_artifact["path"]),
        srt_text,
        output_path,
        subtitle_style,
    )
    await report_progress(progress_callback, caption_progress(96), "자막+더빙 영상 파일 저장 중")

    metadata = dict(dubbed_artifact.get("metadata") or {})
    metadata["srt_source"] = desired_srt_source(file, language, srt_source)
    metadata["dubbed_video_artifact_id"] = dubbed_artifact["id"]
    metadata["variant"] = "captioned_dub"
    metadata["subtitle_style"] = normalized_style
    return db.create_artifact(file["id"], "captioned_dub_video", language, str(output_path), output_path.name, metadata)


def generate_video_thumbnail(video_path: Path, output_path: Path) -> bool:
    return video_utils.generate_video_thumbnail(video_path, output_path)


def create_black_video(duration_ms: int, output_path: Path) -> None:
    video_utils.create_black_video(duration_ms, output_path)


LECTURE_SLIDE_FADE_SECONDS = float(os.getenv("LECTURE_SLIDE_FADE_SECONDS", "0"))
LECTURE_SLIDE_SPEECH_PADDING_SECONDS = float(os.getenv("LECTURE_SLIDE_SPEECH_PADDING_SECONDS", "0.45"))
LECTURE_SLIDE_TRANSITION_SECONDS = float(os.getenv("LECTURE_SLIDE_TRANSITION_SECONDS", "0.4"))
LECTURE_HTML_RENDER_WIDTH = int(os.getenv("LECTURE_HTML_RENDER_WIDTH", "1920"))
LECTURE_HTML_RENDER_HEIGHT = int(os.getenv("LECTURE_HTML_RENDER_HEIGHT", "1080"))
LECTURE_HTML_MAX_AUTO_REFS = int(os.getenv("LECTURE_HTML_MAX_AUTO_REFS", "200"))


def split_html_slide_reference(slide_file: str) -> Tuple[str, Optional[int]]:
    text = safe_upload_filename(slide_file or "")
    if "#" not in text:
        return text, None
    filename, raw_index = text.rsplit("#", 1)
    filename = safe_upload_filename(filename)
    try:
        slide_index = int(raw_index)
    except (TypeError, ValueError):
        return text, None
    if slide_index < 1:
        return text, None
    return filename, slide_index


def lecture_available_slide_references(uploaded_filenames: List[str]) -> List[str]:
    refs: List[str] = []
    for filename in uploaded_filenames:
        refs.append(filename)
        if Path(filename).suffix.lower() in LECTURE_HTML_SLIDE_EXTENSIONS | LECTURE_PDF_SLIDE_EXTENSIONS:
            refs.extend(f"{filename}#{index}" for index in range(1, LECTURE_HTML_MAX_AUTO_REFS + 1))
    return refs


def can_auto_map_missing_slides_to_single_document(validation: Dict, uploaded_filenames: List[str]) -> bool:
    document_files = [
        name for name in uploaded_filenames
        if Path(name).suffix.lower() in LECTURE_HTML_SLIDE_EXTENSIONS | LECTURE_PDF_SLIDE_EXTENSIONS
    ]
    image_files = [
        name for name in uploaded_filenames
        if Path(name).suffix.lower() in LECTURE_IMAGE_SLIDE_EXTENSIONS
    ]
    if len(document_files) != 1 or image_files:
        return False
    errors = validation.get("errors") or []
    if not errors:
        return False
    return all("slide_file" in error and "was not uploaded" in error for error in errors)


def build_single_document_slide_aliases(validation: Dict, document_filename: str) -> Dict[str, str]:
    aliases: Dict[str, str] = {}
    for item in validation.get("items") or []:
        slide_file = safe_upload_filename(str(item.get("slide_file") or ""))
        slide_no = item.get("slide_no")
        if not slide_file or not isinstance(slide_no, int) or slide_no < 1:
            continue
        aliases[slide_file] = f"{document_filename}#{slide_no}"
    return aliases


def rendered_document_slide_output_name(source_filename: str, slide_index: Optional[int]) -> str:
    stem = Path(source_filename).stem or "slide"
    suffix = f"_{slide_index:03d}" if slide_index else "_001"
    return f"{stem}{suffix}.png"


async def render_html_slide_refs(html_path: Path, requested_refs: List[str], output_dir: Path) -> Dict[str, str]:
    try:
        from playwright.async_api import Error as PlaywrightError
        from playwright.async_api import async_playwright
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "HTML slide rendering requires Playwright. "
                "Install it with 'pip install playwright' and 'python -m playwright install chromium'."
            ),
        ) from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    html_filename = html_path.name
    refs = list(dict.fromkeys(requested_refs))
    rendered: Dict[str, str] = {}
    render_script = """
        async ({ targetIndex, width, height }) => {
            const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
            if (document.fonts?.ready) {
                try { await document.fonts.ready; } catch {}
            }
            const allSlides = Array.from(document.querySelectorAll("section.slide, .slide, [data-slide]"));
            const slides = allSlides.filter((slide) => !allSlides.some((other) => other !== slide && other.contains(slide)));
            document.documentElement.style.width = `${width}px`;
            document.documentElement.style.height = `${height}px`;
            document.body.style.width = `${width}px`;
            document.body.style.height = `${height}px`;
            document.body.style.margin = "0";
            document.body.style.overflow = "hidden";
            let target = document.body;
            if (slides.length) {
                if (targetIndex < 0 || targetIndex >= slides.length) {
                    return { ok: false, slideCount: slides.length };
                }
                slides.forEach((slide, index) => {
                    const isTarget = index === targetIndex;
                    slide.classList.toggle("active", isTarget);
                    slide.removeAttribute("aria-hidden");
                    slide.style.setProperty("display", isTarget ? "block" : "none", "important");
                    slide.style.setProperty("position", "fixed", "important");
                    slide.style.setProperty("inset", "0 auto auto 0", "important");
                    slide.style.setProperty("width", `${width}px`, "important");
                    slide.style.setProperty("height", `${height}px`, "important");
                    slide.style.setProperty("min-width", `${width}px`, "important");
                    slide.style.setProperty("min-height", `${height}px`, "important");
                    slide.style.setProperty("max-width", `${width}px`, "important");
                    slide.style.setProperty("max-height", `${height}px`, "important");
                    slide.style.setProperty("margin", "0", "important");
                    slide.style.setProperty("opacity", "1", "important");
                    slide.style.setProperty("transform", "none", "important");
                    slide.style.setProperty("overflow", "hidden", "important");
                    slide.querySelectorAll(".step,.fragment,[data-animate],[data-animation]").forEach((node) => {
                        node.classList.add("visible");
                        node.style.setProperty("opacity", "1", "important");
                        node.style.setProperty("visibility", "visible", "important");
                        node.style.setProperty("transform", "none", "important");
                    });
                });
                target = slides[targetIndex];
            } else if (targetIndex > 0) {
                return { ok: false, slideCount: 1 };
            }
            document.querySelectorAll("[data-html-slide-editor],.html-slide-editor-box,.html-slide-editor-guide-layer,.html-slide-editor-guide,#progress-bar").forEach((node) => node.remove());
            await wait(250);
            await Promise.race([
                Promise.all(Array.from(document.images).filter((image) => !image.complete).map((image) => new Promise((resolve) => {
                    image.addEventListener("load", resolve, { once: true });
                    image.addEventListener("error", resolve, { once: true });
                }))),
                wait(2500),
            ]);
            const rect = target.getBoundingClientRect();
            return { ok: true, slideCount: slides.length || 1, rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height } };
        }
    """
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page(
                viewport={"width": LECTURE_HTML_RENDER_WIDTH, "height": LECTURE_HTML_RENDER_HEIGHT},
                device_scale_factor=1,
            )
            try:
                await page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
                for ref in refs:
                    _, slide_index = split_html_slide_reference(ref)
                    target_index = 0 if slide_index is None else slide_index - 1
                    result = await page.evaluate(
                        render_script,
                        {
                            "targetIndex": target_index,
                            "width": LECTURE_HTML_RENDER_WIDTH,
                            "height": LECTURE_HTML_RENDER_HEIGHT,
                        },
                    )
                    if not result.get("ok"):
                        raise HTTPException(
                            status_code=400,
                            detail=f"HTML slide reference '{ref}' is out of range. Found {result.get('slideCount', 0)} slides in {html_filename}.",
                        )
                    output_path = output_dir / rendered_document_slide_output_name(html_filename, slide_index)
                    await page.screenshot(path=str(output_path), full_page=False)
                    rendered[ref] = str(output_path)
            finally:
                await page.close()
                await browser.close()
    except HTTPException:
        raise
    except PlaywrightError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "HTML slide rendering failed. "
                "If Chromium is not installed, run 'python -m playwright install chromium'. "
                f"Original error: {exc}"
            ),
        ) from exc
    return rendered


def render_pdf_slide_refs(pdf_path: Path, requested_refs: List[str], output_dir: Path) -> Dict[str, str]:
    try:
        import fitz
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="PDF slide rendering requires PyMuPDF. Install it with 'pip install pymupdf'.",
        ) from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_filename = pdf_path.name
    refs = list(dict.fromkeys(requested_refs))
    rendered: Dict[str, str] = {}
    try:
        with fitz.open(pdf_path) as document:
            page_count = int(document.page_count or 0)
            if page_count < 1:
                raise HTTPException(status_code=400, detail=f"PDF slide file has no pages: {pdf_filename}")
            for ref in refs:
                _, slide_index = split_html_slide_reference(ref)
                page_number = 1 if slide_index is None else slide_index
                if page_number < 1 or page_number > page_count:
                    raise HTTPException(
                        status_code=400,
                        detail=f"PDF slide reference '{ref}' is out of range. Found {page_count} pages in {pdf_filename}.",
                    )
                page = document.load_page(page_number - 1)
                rect = page.rect
                if rect.width <= 0 or rect.height <= 0:
                    raise HTTPException(status_code=400, detail=f"PDF page has invalid size: {ref}")
                scale = min(LECTURE_HTML_RENDER_WIDTH / rect.width, LECTURE_HTML_RENDER_HEIGHT / rect.height)
                pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                output_path = output_dir / rendered_document_slide_output_name(pdf_filename, slide_index)
                pixmap.save(output_path)
                rendered[ref] = str(output_path)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF slide rendering failed: {exc}") from exc
    return rendered


def extract_json_object(text: str) -> Dict:
    raw = (text or "").strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            return json.loads(raw[start:end + 1])
        raise


def clamp_ai_video_scene_count(value: Optional[int] = None) -> int:
    default_count = max(1, min(AI_VIDEO_DEFAULT_SCENE_COUNT, AI_VIDEO_MAX_SCENE_COUNT))
    try:
        count = int(value or default_count)
    except (TypeError, ValueError):
        count = default_count
    return max(1, min(count, AI_VIDEO_MAX_SCENE_COUNT))


def default_ai_video_character_assets() -> List[Dict]:
    assets: List[Dict] = []
    for asset in DEFAULT_AI_CHARACTER_ASSETS:
        path = AI_CHARACTER_ASSET_DIR / asset["filename"]
        if path.exists() and path.is_file():
            assets.append({
                **asset,
                "path": str(path),
                "default": True,
            })
    if assets:
        return assets
    path = DEFAULT_AI_CHARACTER_ASSET_PATH.expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists() or not path.is_file():
        return []
    return [{
        "name": DEFAULT_AI_CHARACTER_NAME or path.stem,
        "filename": path.name,
        "path": str(path),
        "description": DEFAULT_AI_CHARACTER_DESCRIPTION,
        "default": True,
    }]


def merge_ai_video_character_assets(*asset_groups: Optional[List[Dict]]) -> List[Dict]:
    merged: List[Dict] = []
    seen = set()
    for assets in asset_groups:
        for asset in assets or []:
            name = str(asset.get("name") or Path(str(asset.get("filename") or asset.get("path") or "")).stem).strip()
            path = str(asset.get("path") or "").strip()
            if not name or not path:
                continue
            key = (name.lower(), str(Path(path).expanduser()).lower())
            if key in seen:
                continue
            seen.add(key)
            merged.append({
                **asset,
                "name": name,
                "filename": str(asset.get("filename") or Path(path).name),
                "path": path,
            })
    return merged


def ai_video_character_names(extra_names: Optional[List[str]] = None, character_assets: Optional[List[Dict]] = None) -> List[str]:
    names: List[str] = []
    for name in extra_names or []:
        clean_name = str(name).strip()
        if clean_name and clean_name.lower() not in {item.lower() for item in names}:
            names.append(clean_name)
    for asset in character_assets or []:
        clean_name = str(asset.get("name") or "").strip()
        if clean_name and clean_name.lower() not in {item.lower() for item in names}:
            names.append(clean_name)
    return names


CHARACTER_APPEARANCE_PATTERNS = [
    r"\b(?:a|an|the)\s+curious\s+white\s+bear\s+mascot\s+with\s+a\s+blue\s+AI\s+headband\b",
    r"\b(?:a|an|the)\s+white\s+bear\s+mascot\s+with\s+a\s+blue\s+AI\s+headband\b",
    r"\b(?:a|an|the)\s+yellow\s+chick\s+mascot\s+with\s+a\s+blue\s+AI\s+headband\b",
    r"\bwhite\s+bear\s+mascot\b",
    r"\byellow\s+chick\s+mascot\b",
    r"\bblue\s+AI\s+headband\b",
    r"\bAI\s+headband\b",
    r"\bOr\b",
    r"\bPpiya\b",
    r"오르",
    r"삐야",
]


def strip_character_appearance_from_prompt(prompt: str, character_usage: List[str]) -> str:
    cleaned = str(prompt or "").strip()
    if not cleaned or not character_usage:
        return cleaned
    for pattern in CHARACTER_APPEARANCE_PATTERNS:
        cleaned = re.sub(pattern, "the referenced character", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"\bthe referenced character\s+with\s+the referenced character\b", "the referenced character", cleaned, flags=re.IGNORECASE)
    return cleaned.strip(" ,.")


def normalize_ai_video_scene(scene: Dict, index: int) -> Dict:
    script = re.sub(r"\s+", " ", str(scene.get("script") or "").strip())
    image_prompt = re.sub(r"\s+", " ", str(scene.get("image_prompt") or "").strip())
    visual_notes = re.sub(r"\s+", " ", str(scene.get("visual_notes") or "").strip())
    scene_kind = str(scene.get("scene_kind") or "veo_clip").strip().lower()
    if scene_kind not in {"veo_clip", "image_narration"}:
        scene_kind = "veo_clip"
    audio_mode = str(scene.get("audio_mode") or "narrator").strip().lower()
    if audio_mode not in {"narrator", "silent", "veo_audio"}:
        audio_mode = "narrator"
    video_prompt = re.sub(r"\s+", " ", str(scene.get("video_prompt") or "").strip())
    dialogue = re.sub(r"\s+", " ", str(scene.get("dialogue") or "").strip())
    sound_design = re.sub(r"\s+", " ", str(scene.get("sound_design") or "").strip())
    subtitle_text = re.sub(r"\s+", " ", str(scene.get("subtitle_text") or "").strip())
    raw_character_usage = scene.get("character_usage") or []
    if isinstance(raw_character_usage, str):
        raw_character_usage = [part.strip() for part in raw_character_usage.split(",")]
    character_usage = [str(name).strip() for name in raw_character_usage if str(name).strip()]
    video_prompt = strip_character_appearance_from_prompt(video_prompt, character_usage)
    character_role = re.sub(r"\s+", " ", str(scene.get("character_role") or "").strip())
    try:
        duration_seconds = float(scene.get("duration_seconds") or VEO_DEFAULT_DURATION_SECONDS)
    except (TypeError, ValueError):
        duration_seconds = VEO_DEFAULT_DURATION_SECONDS
    duration_seconds = min(max(duration_seconds, 2.0), VEO_MAX_DURATION_SECONDS)
    if not script and audio_mode == "veo_audio" and dialogue:
        script = dialogue
    if not script:
        script = f"Scene {index}."
    if not image_prompt:
        image_prompt = f"Create a clean 16:9 visual illustration for this narration: {script[:240]}"
    if not video_prompt:
        video_prompt = (
            f"Vertical 9:16 short-form video scene. {visual_notes or image_prompt}. "
            f"Action: {script[:220]}. "
            "Fast pacing, cinematic movement, social short-form style."
        )
    if subtitle_text != script:
        subtitle_text = script
    return {
        "scene_no": int(scene.get("scene_no") or index),
        "script": script,
        "image_prompt": image_prompt,
        "visual_notes": visual_notes,
        "scene_kind": scene_kind,
        "audio_mode": audio_mode,
        "video_prompt": video_prompt,
        "dialogue": dialogue,
        "sound_design": sound_design,
        "subtitle_text": subtitle_text,
        "duration_seconds": duration_seconds,
        "character_usage": character_usage,
        "character_role": character_role,
    }


def normalize_ai_video_draft(data: Dict, request: AiVideoDraftRequest, research_mode: str) -> Dict:
    scenes = data.get("scenes") if isinstance(data, dict) else []
    if not isinstance(scenes, list):
        scenes = []
    scene_count = clamp_ai_video_scene_count(max(len(scenes), AI_VIDEO_DEFAULT_SCENE_COUNT))
    normalized = [normalize_ai_video_scene(scene if isinstance(scene, dict) else {}, index + 1) for index, scene in enumerate(scenes[:scene_count])]
    while len(normalized) < scene_count:
        index = len(normalized) + 1
        normalized.append(normalize_ai_video_scene({
            "scene_no": index,
            "script": f"{request.topic}에 대한 핵심 내용을 장면 {index}에서 설명합니다.",
            "image_prompt": f"16:9 clean modern illustration about {request.topic}, scene {index}",
        }, index))
    target_aspect_ratio, aspect_warning = resolve_ai_video_aspect_ratio(request.image_style, "veo", request.aspect_ratio)
    character_assets = default_ai_video_character_assets()
    return {
        "draft_id": str(uuid.uuid4()),
        "title": str(data.get("title") or request.topic).strip()[:120],
        "summary": str(data.get("summary") or "").strip(),
        "topic": request.topic.strip(),
        "language": (request.language or "ko").lower(),
        "target_duration": request.target_duration,
        "audience": request.audience,
        "tone": request.tone,
        "image_style": request.image_style,
        "aspect_ratio": target_aspect_ratio,
        "aspect_ratio_warning": aspect_warning or "",
        "character_assets": character_assets,
        "research_mode": research_mode,
        "scenes": normalized,
    }


def build_ai_video_draft_prompt(request: AiVideoDraftRequest, research_mode: str) -> str:
    scene_count = clamp_ai_video_scene_count()
    target_aspect_ratio, aspect_warning = resolve_ai_video_aspect_ratio(request.image_style, "veo", request.aspect_ratio)
    default_character_assets = default_ai_video_character_assets()
    character_names = ai_video_character_names(request.character_names, default_character_assets)
    character_text = ", ".join(character_names) if character_names else "No predefined characters."
    return f"""
Return only valid JSON. Do not use markdown fences.
Create or adapt a short-form vertical video production plan.

User topic or planning brief:
{request.topic}
Language: {request.language}
Target duration: {request.target_duration}
Audience: {request.audience}
Narration tone: {request.tone}
Image style: {request.image_style}
Target aspect ratio: {target_aspect_ratio}
Aspect ratio note: {aspect_warning or "Use the target aspect ratio consistently."}
Available predefined characters: {character_text}
Research mode: {research_mode}

Rules:
- Create exactly {scene_count} scenes for a Shorts/Reels/TikTok style video.
- If the user input is already a shorts plan, storyboard, script, scene list, or prompt list, do not reinvent the concept. Adapt that plan into the JSON scenes.
- If the user input includes scene numbers, scene titles, dialogue, narration, or visual prompts, preserve their order and intent.
- If a visual/video prompt is provided by the user, use it as the scene video_prompt after removing any character appearance descriptions that should come from reference images.
- If the user input is only a broad topic, then plan the scenes yourself.
- Write video_prompt for the target aspect ratio: {target_aspect_ratio}.
- Plan fast visual pacing. Most scenes should feel like 2-4 second beats.
- Keep each narrator script very short: one sentence only, ideally 6-12 Korean words or 6-10 English words.
- If a thought needs more words, split it into multiple scenes instead of writing a long script.
- Prefer more quick visual beats over fewer explanatory scenes.
- Decide each scene_kind:
  - "veo_clip": moving video generated by Veo. The prompt must describe only the visual scene, action, camera movement, and mood.
  - "image_narration": static/generated image plus external narrator TTS, only when explanation is needed or Veo is unnecessary.
- Decide each audio_mode:
  - "narrator": external TTS narration explains the scene.
  - "veo_audio": Veo generates the scene's direct dialogue, sound effects, ambience, or music. Do not use external TTS for this scene.
  - "silent": no speech, visual beat only.
- Use "veo_audio" when the scene should contain direct in-video dialogue, reactions, sound effects, ambience, or native video audio.
- Use "narrator" when the scene needs external explanatory narration.
- For "narrator" scenes, do not ask Veo to create speech, music, sound effects, ambience, or character dialogue.
- For "veo_audio" scenes, put direct spoken lines in dialogue and audio cues in sound_design. Keep script as a short subtitle/meaning summary for the same spoken content.
- For veo_clip narrator scenes, video_prompt is visual-only. script is the exact separate narrator line that will be generated by TTS and used as the subtitle.
- For veo_clip veo_audio scenes, video_prompt describes the visual action and dialogue/sound_design describe the native audio.
- Narration should be punchy and short-form, not lecture-style.
- subtitle_text must match script exactly. Do not write scene titles, labels, summaries, or hook captions in subtitle_text.
- Avoid text-heavy visuals.
- If predefined characters are useful, set character_usage to one or more character names from the available list.
- Do not force characters into every scene. Use [] when the scene is better without them.
- If a character is used, write only the role/action in character_role, such as "holds an almond and looks curious".
- Do not describe predefined character appearance, species, color, clothing, headband, face, body shape, or mascot design in video_prompt.
- Do not write phrases like "white bear mascot", "yellow chick mascot", "blue AI headband", or any other reference-image appearance details in video_prompt.
- The video_prompt must describe only the scene content, action, camera movement, setting, lighting, and mood.
- The character's visual identity will be supplied as an attached reference image, not as text.

JSON shape:
{{
  "title": "video title",
  "summary": "one sentence summary",
  "scenes": [
    {{
      "scene_no": 1,
      "scene_kind": "veo_clip",
      "audio_mode": "narrator",
      "duration_seconds": 5,
      "script": "external narrator text for this scene",
      "video_prompt": "vertical 9:16 visual-only video prompt with action and camera movement; no audio instructions",
      "dialogue": "direct in-video dialogue only when audio_mode is veo_audio",
      "sound_design": "sound effects, ambience, or music only when audio_mode is veo_audio",
      "subtitle_text": "short subtitle text to show for this scene",
      "visual_notes": "brief note",
      "character_usage": ["character name"],
      "character_role": "how the character appears or acts in this scene"
    }}
  ]
}}
"""


def generate_ai_video_draft(request: AiVideoDraftRequest) -> Dict:
    if not request.topic.strip():
        raise HTTPException(status_code=400, detail="Topic is required.")
    if not gemini_text_client:
        raise HTTPException(status_code=500, detail="Gemini text client is not configured.")
    research_mode = "llm_only"
    prompt = build_ai_video_draft_prompt(request, research_mode)
    try:
        data = extract_json_object(generate_gemini_text(prompt, operation="ai_video_draft"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AI video draft JSON parsing failed: {exc}") from exc
    draft = normalize_ai_video_draft(data, request, research_mode)
    AI_VIDEO_DRAFTS[draft["draft_id"]] = draft
    return draft


def ai_video_script_text(scenes: List[Dict]) -> str:
    lines = []
    for scene in scenes:
        detail = scene.get("dialogue") or scene.get("script") or scene.get("subtitle_text") or ""
        lines.append(f"{scene['scene_no']}. [{scene.get('scene_kind', 'scene')}/{scene.get('audio_mode', '')}] {detail}")
    return "\n".join(lines)


def ai_video_timeline_items(scenes: List[Dict]) -> List[Dict]:
    return [
        {
            "slide_no": scene["scene_no"],
            "slide_file": f"scene_{scene['scene_no']:03d}.png",
            "script": scene["script"],
            "image_prompt": scene.get("image_prompt", ""),
            "visual_notes": scene.get("visual_notes", ""),
            "scene_kind": scene.get("scene_kind", "image_narration"),
            "audio_mode": scene.get("audio_mode", "narrator"),
            "video_prompt": scene.get("video_prompt", ""),
            "dialogue": scene.get("dialogue", ""),
            "sound_design": scene.get("sound_design", ""),
            "subtitle_text": scene.get("subtitle_text", scene.get("script", "")),
            "duration_seconds": scene.get("duration_seconds", VEO_DEFAULT_DURATION_SECONDS),
            "character_usage": scene.get("character_usage", []),
            "character_role": scene.get("character_role", ""),
        }
        for scene in scenes
    ]


def create_fallback_scene_image(scene: Dict, output_path: Path) -> None:
    title = f"Scene {scene.get('scene_no', 1)}"
    script = re.sub(r"\s+", " ", str(scene.get("script") or "").strip())[:220]
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
html,body{{margin:0;width:1920px;height:1080px;background:#111827;color:white;font-family:Arial,'Malgun Gothic',sans-serif;}}
.frame{{width:100%;height:100%;display:flex;flex-direction:column;justify-content:center;padding:120px;box-sizing:border-box;background:linear-gradient(135deg,#111827,#1f2937 55%,#334155);}}
.kicker{{font-size:34px;color:#93c5fd;text-transform:uppercase;letter-spacing:4px;margin-bottom:28px;}}
h1{{font-size:88px;line-height:1.05;margin:0 0 40px;max-width:1400px;}}
p{{font-size:44px;line-height:1.35;margin:0;max-width:1500px;color:#e5e7eb;}}
</style></head><body><div class="frame"><div class="kicker">AI Video</div><h1>{title}</h1><p>{script}</p></div></body></html>"""
    temp_html = output_path.with_suffix(".html")
    temp_html.write_text(html, encoding="utf-8")
    try:
        rendered = asyncio.run(render_html_slide_refs(temp_html, [temp_html.name], output_path.parent))
        rendered_path = Path(next(iter(rendered.values())))
        if rendered_path != output_path:
            rendered_path.replace(output_path)
    finally:
        try:
            temp_html.unlink()
        except OSError:
            pass


def save_imagen_response_image(response: Any, output_path: Path) -> bool:
    generated_images = getattr(response, "generated_images", None) or getattr(response, "images", None) or []
    for image_item in generated_images:
        image = getattr(image_item, "image", image_item)
        data = getattr(image, "image_bytes", None) or getattr(image, "data", None)
        if data:
            output_path.write_bytes(data)
            return True
    return False


def save_gemini_generated_image(response: Any, output_path: Path) -> bool:
    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            inline_data = getattr(part, "inline_data", None)
            inline_bytes = getattr(inline_data, "data", None) if inline_data else None
            if inline_bytes:
                if isinstance(inline_bytes, str):
                    output_path.write_bytes(base64.b64decode(inline_bytes))
                else:
                    output_path.write_bytes(bytes(inline_bytes))
                return True
    return False


def ai_video_visual_prompt(scene: Dict) -> str:
    prompt = scene.get("image_prompt") or scene.get("script") or "clean editorial image"
    aspect_ratio = scene.get("aspect_ratio") or AI_VIDEO_IMAGE_ASPECT_RATIO
    return (
        f"{prompt}\n\n"
        f"Create one polished {aspect_ratio} video frame for a short-form educational video. "
        "Do not place captions, subtitles, UI labels, watermarks, or long readable text inside the image. "
        "Make it visually complete and suitable as a scene background."
    )


def normalize_ai_video_visual_provider(provider: Optional[str]) -> str:
    normalized = (provider or AI_VIDEO_VISUAL_PROVIDER or "nano_banana").strip().lower().replace("-", "_")
    aliases = {
        "gemini": "nano_banana",
        "gemini_image": "nano_banana",
        "nanobanana": "nano_banana",
        "nano_banana_image": "nano_banana",
    }
    return aliases.get(normalized, normalized)


def generate_nano_banana_scene_image(scene: Dict, output_path: Path) -> Dict:
    image_client = create_gemini_image_client()
    prompt = ai_video_visual_prompt(scene)
    aspect_ratio = scene.get("aspect_ratio") if scene.get("aspect_ratio") in IMAGE_SUPPORTED_ASPECT_RATIOS else AI_VIDEO_IMAGE_ASPECT_RATIO
    errors: List[str] = []
    for model_name in NANO_BANANA_MODELS:
        try:
            config = None
            if google_genai_types:
                config = google_genai_types.GenerateContentConfig(
                    response_modalities=[
                        google_genai_types.Modality.TEXT,
                        google_genai_types.Modality.IMAGE,
                    ],
                    image_config=google_genai_types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                    ),
                )
            response = image_client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            if not save_gemini_generated_image(response, output_path):
                raise RuntimeError("Nano Banana response did not contain image bytes.")
            ai_usage.record_ai_usage(
                provider="nano_banana",
                model=model_name,
                operation="image_generation",
                characters=len(prompt),
                request_count=1,
                estimated_cost_usd=0.0,
                metadata={
                    "usage_source": "request_count_estimate",
                    "aspect_ratio": aspect_ratio,
                    "location": AI_VIDEO_IMAGE_LOCATION,
                    "api_version": AI_VIDEO_IMAGE_API_VERSION,
                },
            )
            return {
                "provider": "nano_banana",
                "model": model_name,
                "fallback": False,
                "aspect_ratio": aspect_ratio,
                "location": AI_VIDEO_IMAGE_LOCATION,
                "api_version": AI_VIDEO_IMAGE_API_VERSION,
                "attempted_models": NANO_BANANA_MODELS,
            }
        except Exception as exc:
            errors.append(f"{model_name}: {exc}")
            continue
    raise RuntimeError("Nano Banana image generation failed for all configured models. " + " | ".join(errors))


def generate_imagen_scene_image(scene: Dict, output_path: Path) -> Dict:
    prompt = ai_video_visual_prompt(scene)
    if not gemini_tts_client:
        raise RuntimeError("Gemini client is not configured.")
    config = None
    if google_genai_types and hasattr(google_genai_types, "GenerateImagesConfig"):
        try:
            config = google_genai_types.GenerateImagesConfig(
                numberOfImages=1,
                aspectRatio=AI_VIDEO_IMAGE_ASPECT_RATIO,
            )
        except TypeError:
            config = google_genai_types.GenerateImagesConfig(numberOfImages=1)
    response = gemini_tts_client.models.generate_images(
        model=IMAGEN_MODEL,
        prompt=prompt,
        config=config,
    )
    if not save_imagen_response_image(response, output_path):
        raise RuntimeError("Imagen response did not contain image bytes.")
    ai_usage.record_ai_usage(
        provider="imagen",
        model=IMAGEN_MODEL,
        operation="image_generation",
        characters=len(prompt),
        request_count=1,
        estimated_cost_usd=0.0,
        metadata={"usage_source": "request_count_estimate", "aspect_ratio": AI_VIDEO_IMAGE_ASPECT_RATIO},
    )
    return {"provider": "imagen", "model": IMAGEN_MODEL, "fallback": False}


def generate_scene_image_by_provider(scene: Dict, output_path: Path, provider: str) -> Dict:
    if provider == "nano_banana":
        return generate_nano_banana_scene_image(scene, output_path)
    if provider == "imagen":
        return generate_imagen_scene_image(scene, output_path)
    raise RuntimeError(f"Unsupported AI video visual provider: {provider}")


def normalize_ai_video_visual_mode(mode: Optional[str]) -> str:
    normalized = (mode or AI_VIDEO_VISUAL_MODE or "veo").strip().lower().replace("-", "_")
    if normalized in {"shorts", "veo", "veo_clip", "video"}:
        return "veo"
    return "image"


def build_veo_scene_prompt(scene: Dict) -> str:
    prompt = scene.get("video_prompt") or scene.get("visual_notes") or scene.get("image_prompt") or scene.get("script") or ""
    aspect_ratio = scene.get("aspect_ratio") if scene.get("aspect_ratio") in VEO_SUPPORTED_ASPECT_RATIOS else VEO_ASPECT_RATIO
    character_role = scene.get("character_role") or ""
    audio_mode = scene.get("audio_mode") or "narrator"
    dialogue = scene.get("dialogue") or ""
    sound_design = scene.get("sound_design") or ""
    parts = [
        f"{aspect_ratio} short-form video clip.",
        "Fast pacing, strong hook, cinematic camera movement, clear subject action.",
        prompt,
        (
            "Use the attached reference image as the character identity source. "
            "Do not infer or redesign the character from text. "
            "Do not show the reference sheet, lineup, grid, turntable, or multiple pose sheet in the final video. "
            f"Character action or role in this scene: {character_role}"
        ) if scene.get("character_reference_path") else "",
        "No burned-in captions, subtitles, logos, watermarks, or readable UI text.",
    ]
    if audio_mode == "veo_audio":
        parts.extend([
            "Generate native video audio for this scene.",
            f"Direct spoken dialogue: {dialogue}" if dialogue else "",
            f"Sound design: {sound_design}" if sound_design else "",
            "Keep dialogue short, natural, and synchronized to the visible action.",
        ])
    else:
        parts.extend([
            "Create visual footage only. No speech, no dialogue, no voiceover, no music, no sound effects, no ambience.",
            "Do not include any character speaking to camera or lip-syncing.",
        ])
    return "\n".join(part for part in parts if str(part).strip())


def attach_character_assets_to_scenes(scenes: List[Dict], character_assets: List[Dict]) -> None:
    lookup = {
        str(asset.get("name") or "").strip().lower(): asset
        for asset in character_assets or []
        if asset.get("name") and asset.get("path")
    }
    for scene in scenes:
        scene_assets = []
        for character_name in scene.get("character_usage") or []:
            asset = lookup.get(str(character_name).strip().lower())
            if asset:
                scene_assets.append(asset)
        if scene_assets:
            scene["character_reference_assets"] = scene_assets
            first_asset = scene_assets[0]
            scene["character_reference_path"] = first_asset.get("path")
            scene["character_reference_name"] = ", ".join(str(asset.get("name") or "") for asset in scene_assets if asset.get("name"))
            scene["character_reference_description"] = first_asset.get("description") or ""


def veo_reference_images_for_scene(scene: Dict) -> List[Any]:
    if not google_genai_types:
        return []
    raw_assets = scene.get("character_reference_assets") or []
    if not raw_assets and scene.get("character_reference_path"):
        raw_assets = [{
            "path": scene.get("character_reference_path"),
            "name": scene.get("character_reference_name") or "",
        }]
    reference_images = []
    for asset in raw_assets:
        raw_path = str(asset.get("path") or "").strip()
        if not raw_path:
            continue
        path = Path(raw_path).expanduser()
        if not path.exists() or not path.is_file():
            continue
        mime_type = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
        image = google_genai_types.Image(image_bytes=path.read_bytes(), mime_type=mime_type)
        reference_type = getattr(google_genai_types.VideoGenerationReferenceType, "ASSET", "ASSET")
        reference_images.append(
            google_genai_types.VideoGenerationReferenceImage(
                image=image,
                reference_type=reference_type,
            )
        )
    return reference_images


def veo_reference_image_for_scene(scene: Dict) -> Optional[Any]:
    reference_images = veo_reference_images_for_scene(scene)
    if reference_images:
        return getattr(reference_images[0], "image", None)
    return None


def save_veo_generated_video(client: Any, generated_video: Any, output_path: Path) -> bool:
    video = getattr(generated_video, "video", generated_video)
    video_bytes = getattr(video, "video_bytes", None)
    if video_bytes:
        output_path.write_bytes(video_bytes if isinstance(video_bytes, bytes) else bytes(video_bytes))
        return True
    try:
        if hasattr(video, "save"):
            video.save(str(output_path))
            if output_path.exists() and output_path.stat().st_size > 0:
                return True
    except Exception:
        pass
    try:
        downloaded = client.files.download(file=video)
        if downloaded:
            output_path.write_bytes(downloaded if isinstance(downloaded, bytes) else bytes(downloaded))
            return True
    except Exception:
        pass
    return False


def generate_veo_scene_video(scene: Dict, output_path: Path) -> Dict:
    client = create_veo_client()
    prompt = build_veo_scene_prompt(scene)
    aspect_ratio = scene.get("aspect_ratio") if scene.get("aspect_ratio") in VEO_SUPPORTED_ASPECT_RATIOS else VEO_ASPECT_RATIO
    generate_audio = (scene.get("audio_mode") or "") == "veo_audio"
    reference_images = veo_reference_images_for_scene(scene)
    errors: List[str] = []
    requested_resolutions = []
    for resolution in [VEO_RESOLUTION, "720p", ""]:
        normalized_resolution = str(resolution or "").strip()
        if normalized_resolution not in requested_resolutions:
            requested_resolutions.append(normalized_resolution)
    for model_name in VEO_MODELS:
        for requested_resolution in requested_resolutions:
            try:
                config = None
                if google_genai_types:
                    config_kwargs = {
                        "number_of_videos": 1,
                        "aspect_ratio": aspect_ratio,
                        "generate_audio": generate_audio,
                        "enhance_prompt": False if reference_images else True,
                    }
                    if requested_resolution:
                        config_kwargs["resolution"] = requested_resolution
                    if reference_images:
                        config_kwargs["reference_images"] = reference_images
                    config = google_genai_types.GenerateVideosConfig(**config_kwargs)
                operation = client.models.generate_videos(
                    model=model_name,
                    prompt=prompt,
                    config=config,
                )
                waited = 0.0
                while not getattr(operation, "done", False):
                    if waited >= VEO_MAX_WAIT_SECONDS:
                        raise RuntimeError(f"Veo operation timed out after {VEO_MAX_WAIT_SECONDS:.0f}s.")
                    time.sleep(VEO_POLL_INTERVAL_SECONDS)
                    waited += VEO_POLL_INTERVAL_SECONDS
                    operation = client.operations.get(operation)
                operation_error = getattr(operation, "error", None)
                if operation_error:
                    raise RuntimeError(f"Veo operation failed: {operation_error}")
                response = getattr(operation, "response", None) or getattr(operation, "result", None)
                generated_videos = getattr(response, "generated_videos", None) or []
                if not generated_videos:
                    response_dump = ""
                    try:
                        if hasattr(response, "model_dump_json"):
                            response_dump = response.model_dump_json()[:1200]
                        else:
                            response_dump = str(response)[:1200]
                    except Exception:
                        response_dump = str(response)[:1200]
                    raise RuntimeError(f"Veo response did not include generated videos. response={response_dump}")
                if not save_veo_generated_video(client, generated_videos[0], output_path):
                    raise RuntimeError("Veo generated video could not be downloaded.")
                generated_duration = video_utils.media_duration_seconds(output_path)
                resolution_label = requested_resolution or "provider_default"
                ai_usage.record_ai_usage(
                    provider="veo",
                    model=model_name,
                    operation="video_generation",
                    characters=len(prompt),
                    request_count=1,
                    estimated_cost_usd=0.0,
                    metadata={
                        "duration_seconds": generated_duration,
                        "aspect_ratio": aspect_ratio,
                        "resolution": resolution_label,
                        "generate_audio": generate_audio,
                        "character_reference": scene.get("character_reference_name") or "",
                        "reference_image_count": len(reference_images),
                        "location": VEO_LOCATION,
                        "api_version": VEO_API_VERSION,
                    },
                )
                return {
                    "provider": "veo",
                    "model": model_name,
                    "duration_seconds": generated_duration,
                    "aspect_ratio": aspect_ratio,
                    "resolution": resolution_label,
                    "generate_audio": generate_audio,
                    "character_reference": scene.get("character_reference_name") or "",
                    "reference_image_count": len(reference_images),
                    "location": VEO_LOCATION,
                    "api_version": VEO_API_VERSION,
                    "prompt": prompt,
                    "attempted_models": VEO_MODELS,
                }
            except Exception as exc:
                suffix = f" ({requested_resolution})" if requested_resolution else " (provider_default_resolution)"
                errors.append(f"{model_name}{suffix}: {exc}")
                continue
    raise RuntimeError("Veo video generation failed for all configured models. " + " | ".join(errors))


async def generate_ai_video_scene_images(
    scenes: List[Dict],
    project_dir: Path,
    visual_provider: Optional[str] = None,
    progress_callback: Optional[ProgressCallback] = None,
) -> Tuple[Dict[str, str], List[Dict]]:
    image_dir = project_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    slide_manifest: Dict[str, str] = {}
    image_metadata: List[Dict] = []
    provider = normalize_ai_video_visual_provider(visual_provider)
    for index, scene in enumerate(scenes, 1):
        filename = f"scene_{int(scene['scene_no']):03d}.png"
        output_path = image_dir / filename
        if progress_callback:
            await report_progress(progress_callback, 18 + int((index - 1) / max(len(scenes), 1) * 30), f"Generating scene image {index}/{len(scenes)}")
        metadata = {"scene_no": scene["scene_no"], "filename": filename, "prompt": scene.get("image_prompt", ""), "requested_provider": provider}
        try:
            generation_metadata = await asyncio.to_thread(generate_scene_image_by_provider, scene, output_path, provider)
            metadata.update(generation_metadata)
        except Exception as exc:
            print(f"{provider} image generation failed for scene {scene.get('scene_no')}: {exc}")
            if not AI_VIDEO_ALLOW_TEXT_FALLBACK:
                raise RuntimeError(f"Scene {scene.get('scene_no')} image generation failed with {provider}: {exc}") from exc
            await asyncio.to_thread(create_fallback_scene_image, scene, output_path)
            metadata.update({"provider": "fallback", "fallback": True, "error": str(exc)})
        slide_manifest[filename] = str(output_path)
        image_metadata.append(metadata)
    return slide_manifest, image_metadata


async def create_static_narration_scene_clip(
    scene: Dict,
    output_path: Path,
    project_dir: Path,
    language: str,
    voice_name: Optional[str],
    style_prompt: Optional[str],
    tts_provider: Optional[str],
    visual_provider: Optional[str],
) -> Dict:
    image_path = project_dir / "images" / f"scene_{int(scene['scene_no']):03d}.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_meta = await asyncio.to_thread(
        generate_scene_image_by_provider,
        scene,
        image_path,
        normalize_ai_video_visual_provider(visual_provider),
    )
    audio_mode = scene.get("audio_mode") or "narrator"
    narration_text = scene.get("script") or scene.get("subtitle_text") or ""
    temp_paths: List[Path] = []
    target_width, target_height = (720, 1280) if scene.get("aspect_ratio") == "9:16" else (1280, 720)
    try:
        if audio_mode == "narrator" and narration_text.strip():
            audio_path = OUTPUT_DIR / f"ai_scene_tts_{uuid.uuid4().hex}.mp3"
            temp_paths.append(audio_path)
            audio_meta = await synthesize_audio_from_text(
                narration_text,
                language,
                audio_path,
                voice_name=voice_name,
                style_prompt=style_prompt,
                tts_provider=tts_provider,
            )
            duration_seconds = max(float(audio_meta.get("duration_ms") or 0) / 1000.0 + 0.35, 2.0)
            segment_path = OUTPUT_DIR / f"ai_scene_static_{uuid.uuid4().hex}.mp4"
            temp_paths.append(segment_path)
            await asyncio.to_thread(
                video_utils.create_slide_segment,
                image_path,
                duration_seconds,
                segment_path,
                0,
                target_width,
                target_height,
            )
            await asyncio.to_thread(mux_video_with_audio, segment_path, audio_path, output_path)
            scene_duration = video_utils.media_duration_seconds(output_path)
        else:
            scene_duration = min(max(float(scene.get("duration_seconds") or VEO_DEFAULT_DURATION_SECONDS), 2.0), VEO_MAX_DURATION_SECONDS)
            await asyncio.to_thread(
                video_utils.create_slide_segment,
                image_path,
                scene_duration,
                output_path,
                0,
                target_width,
                target_height,
            )
        return {
            "provider": "static_narration",
            "scene_kind": "image_narration",
            "image": image_meta,
            "duration_seconds": scene_duration,
            "audio_mode": audio_mode,
        }
    finally:
        for temp_path in temp_paths:
            try:
                temp_path.unlink()
            except OSError:
                pass


async def generate_ai_video_scene_clips(
    scenes: List[Dict],
    project_dir: Path,
    language: str,
    voice_name: Optional[str],
    style_prompt: Optional[str],
    tts_provider: Optional[str],
    visual_provider: Optional[str],
    progress_callback: Optional[ProgressCallback] = None,
) -> Tuple[List[Path], List[Dict], str]:
    clip_dir = project_dir / "clips"
    clip_dir.mkdir(parents=True, exist_ok=True)
    clip_paths: List[Path] = []
    clip_metadata: List[Dict] = []
    srt_items: List[Dict] = []
    cursor = 0.0
    for index, scene in enumerate(scenes, 1):
        output_path = clip_dir / f"scene_{int(scene['scene_no']):03d}.mp4"
        if progress_callback:
            await report_progress(progress_callback, 12 + int((index - 1) / max(len(scenes), 1) * 58), f"Generating short scene clip {index}/{len(scenes)}")
        scene_kind = scene.get("scene_kind") or "veo_clip"
        if scene_kind == "veo_clip":
            temp_paths: List[Path] = []
            try:
                narration_text = (scene.get("script") or "").strip()
                if (scene.get("audio_mode") or "narrator") == "narrator" and narration_text:
                    audio_path = OUTPUT_DIR / f"ai_scene_veo_tts_{uuid.uuid4().hex}.mp3"
                    temp_paths.append(audio_path)
                    audio_meta = await synthesize_audio_from_text(
                        narration_text,
                        language,
                        audio_path,
                        voice_name=voice_name,
                        style_prompt=style_prompt,
                        tts_provider=tts_provider,
                    )
                    audio_duration = max(float(audio_meta.get("duration_ms") or 0) / 1000.0, 2.0)
                    target_duration = audio_duration + 0.35
                    raw_scene = dict(scene)
                    raw_video_path = clip_dir / f"scene_{int(scene['scene_no']):03d}_raw.mp4"
                    temp_paths.append(raw_video_path)
                    raw_meta = await asyncio.to_thread(generate_veo_scene_video, raw_scene, raw_video_path)
                    visual_path = clip_dir / f"scene_{int(scene['scene_no']):03d}_visual.mp4"
                    temp_paths.append(visual_path)
                    await asyncio.to_thread(pad_or_trim_video_to_duration, raw_video_path, target_duration, visual_path)
                    await asyncio.to_thread(mux_video_with_audio, visual_path, audio_path, output_path)
                    meta = {
                        "provider": "veo_visual_with_tts",
                        "model": raw_meta.get("model"),
                        "visual_generation_count": 1,
                        "looped_to_match_audio": target_duration > raw_meta.get("duration_seconds", 0) + 0.05,
                        "raw_visual": raw_meta,
                        "duration_seconds": target_duration,
                    }
                    meta["tts_duration_seconds"] = audio_duration
                    meta["audio_mode"] = "narrator"
                else:
                    meta = await asyncio.to_thread(generate_veo_scene_video, scene, output_path)
                    meta["audio_mode"] = scene.get("audio_mode") or "silent"
            finally:
                for temp_path in temp_paths:
                    try:
                        temp_path.unlink()
                    except OSError:
                        pass
        else:
            meta = await create_static_narration_scene_clip(
                scene,
                output_path,
                project_dir,
                language,
                voice_name,
                style_prompt,
                tts_provider,
                visual_provider,
            )
        duration = video_utils.media_duration_seconds(output_path)
        if (scene.get("audio_mode") or "") == "veo_audio":
            subtitle_text = (scene.get("dialogue") or scene.get("subtitle_text") or scene.get("script") or "").strip()
        else:
            subtitle_text = (scene.get("script") or "").strip()
        if subtitle_text:
            for start, end, text in split_segment_into_srt_entries(cursor, cursor + duration, subtitle_text):
                srt_items.append({
                    "start": start,
                    "end": end,
                    "text": text,
                })
        clip_paths.append(output_path)
        clip_metadata.append({
            "scene_no": scene.get("scene_no"),
            "scene_kind": scene_kind,
            "audio_mode": scene.get("audio_mode"),
            "path": str(output_path),
            "duration_seconds": duration,
            **meta,
        })
        cursor += duration
    srt_text = build_srt_from_timed_items(srt_items)
    return clip_paths, clip_metadata, srt_text


def create_slide_segment(slide_path: Path, duration_seconds: float, output_path: Path, fade_seconds: float = LECTURE_SLIDE_FADE_SECONDS) -> None:
    video_utils.create_slide_segment(slide_path, duration_seconds, output_path, fade_seconds=fade_seconds)


def crossfade_video_sequence(
    source_paths: List[Path],
    display_durations: List[float],
    output_path: Path,
    transition_seconds: float = LECTURE_SLIDE_TRANSITION_SECONDS,
) -> None:
    video_utils.crossfade_video_sequence(source_paths, display_durations, output_path, transition_seconds=transition_seconds)


def create_lecture_slide_video(timeline_items: List[Dict], slide_paths: Dict[str, Path], output_path: Path) -> Dict:
    if not timeline_items:
        raise HTTPException(status_code=400, detail="Timeline is empty.")
    temp_paths: List[Path] = []
    display_durations: List[float] = []
    previous_end = 0.0
    gap_probe_end = 0.0
    has_explicit_gap = False
    for item in timeline_items:
        if item["start_seconds"] > gap_probe_end + 0.001:
            has_explicit_gap = True
            break
        gap_probe_end = item["end_seconds"]
    try:
        for index, item in enumerate(timeline_items, 1):
            if item["start_seconds"] > previous_end + 0.001:
                gap_path = OUTPUT_DIR / f"lecture_gap_{uuid.uuid4().hex}.mp4"
                create_black_video(int(round((item["start_seconds"] - previous_end) * 1000)), gap_path)
                temp_paths.append(gap_path)
                display_durations.append(float(item["start_seconds"] - previous_end))
            slide_path = slide_paths.get(item["slide_file"])
            if not slide_path or not slide_path.exists():
                raise HTTPException(status_code=400, detail=f"Slide file is missing: {item['slide_file']}")
            segment_path = OUTPUT_DIR / f"lecture_slide_{index}_{uuid.uuid4().hex}.mp4"
            display_duration = max(float(item["duration_seconds"]), 0.1)
            transition_extension = LECTURE_SLIDE_TRANSITION_SECONDS if index < len(timeline_items) and not has_explicit_gap else 0.0
            create_slide_segment(
                slide_path,
                display_duration + transition_extension,
                segment_path,
                fade_seconds=LECTURE_SLIDE_FADE_SECONDS,
            )
            temp_paths.append(segment_path)
            display_durations.append(display_duration)
            previous_end = item["end_seconds"]
        should_crossfade = len(temp_paths) > 1 and not has_explicit_gap and LECTURE_SLIDE_TRANSITION_SECONDS > 0.01
        if should_crossfade:
            crossfade_video_sequence(
                temp_paths,
                display_durations,
                output_path,
                transition_seconds=LECTURE_SLIDE_TRANSITION_SECONDS,
            )
        elif len(temp_paths) == 1:
            crossfade_video_sequence(temp_paths, display_durations, output_path, transition_seconds=0)
        else:
            concat_video_sequence(temp_paths, output_path)
        return {
            "duration_ms": int(round(max(item["end_seconds"] for item in timeline_items) * 1000)),
            "slide_count": len(timeline_items),
            "gap_count": max(0, len(temp_paths) - len(timeline_items)),
            "transition": "crossfade" if should_crossfade else "cut_with_speech_padding",
            "transition_seconds": LECTURE_SLIDE_TRANSITION_SECONDS if should_crossfade else 0,
            "speech_padding_seconds": LECTURE_SLIDE_SPEECH_PADDING_SECONDS,
            "visual_fade_seconds": LECTURE_SLIDE_FADE_SECONDS,
        }
    finally:
        for temp_path in temp_paths:
            try:
                temp_path.unlink()
            except OSError:
                pass


def lecture_script_for_item(item: Dict, cues_by_index: Dict[int, Dict]) -> str:
    if item.get("script"):
        return str(item.get("script") or "").strip()
    texts = []
    for cue_index in range(item.get("srt_start_index", 0), item.get("srt_end_index", -1) + 1):
        cue = cues_by_index.get(cue_index)
        if cue and cue.get("text", "").strip():
            texts.append(cue["text"].strip())
    return "\n".join(texts).strip()


async def synthesize_lecture_audio_by_slides(
    timeline_items: List[Dict],
    srt_text: str,
    language: str,
    output_path: Path,
    voice_name: Optional[str] = None,
    style_prompt: Optional[str] = None,
    tts_provider: Optional[str] = None,
    progress_callback: Optional[ProgressCallback] = None,
    progress_start: int = 10,
    progress_end: int = 70,
) -> Dict:
    cues = parse_srt(srt_text)
    cues_by_index = {cue["index"]: cue for cue in cues}
    provider, normalized_voice = normalize_tts_selection(language, tts_provider, voice_name)
    timeline = AudioSegment.silent(duration=0).set_channels(2)
    generated_items: List[Dict] = []
    temp_paths: List[Path] = []
    cursor_ms = 0
    usage_summary = {
        "ai_input_tokens": 0,
        "ai_output_tokens": 0,
        "ai_total_tokens": 0,
        "ai_characters": 0,
        "ai_request_count": 0,
        "ai_estimated_cost_usd": 0.0,
    }
    try:
        for index, item in enumerate(timeline_items, 1):
            current_progress = progress_start + int(((index - 1) / max(len(timeline_items), 1)) * max(progress_end - progress_start, 1))
            script = lecture_script_for_item(item, cues_by_index)
            if not script:
                raise HTTPException(status_code=400, detail=f"Slide {item['slide_no']} has no script text.")
            await report_progress(progress_callback, current_progress, f"Slide {item['slide_no']} voice generation ({index}/{len(timeline_items)})")
            wav_path = OUTPUT_DIR / f"lecture_tts_{uuid.uuid4().hex}.wav"
            temp_paths.append(wav_path)
            usage = await generate_tts_wav(script, language, wav_path, voice_name=voice_name, style_prompt=style_prompt, tts_provider=tts_provider)
            usage = usage or {}
            usage_summary["ai_input_tokens"] += int(usage.get("input_tokens") or 0)
            usage_summary["ai_output_tokens"] += int(usage.get("output_tokens") or 0)
            usage_summary["ai_total_tokens"] += int(usage.get("total_tokens") or 0)
            usage_summary["ai_characters"] += int(usage.get("characters") or 0)
            usage_summary["ai_request_count"] += int(usage.get("request_count") or 0)
            usage_summary["ai_estimated_cost_usd"] += float(usage.get("estimated_cost_usd") or 0)
            with open(wav_path, "rb") as wav_file:
                segment = AudioSegment.from_file(wav_file, format="wav").set_channels(2)
            segment = apply_short_fades(segment)
            padding_ms = max(0, int(round(LECTURE_SLIDE_SPEECH_PADDING_SECONDS * 1000)))
            leading_ms = padding_ms if index > 1 else 0
            trailing_ms = padding_ms if index < len(timeline_items) else 0
            leading_silence = AudioSegment.silent(duration=leading_ms).set_channels(2)
            trailing_silence = AudioSegment.silent(duration=trailing_ms).set_channels(2)
            start_ms = cursor_ms
            speech_start_ms = start_ms + leading_ms
            speech_end_ms = speech_start_ms + len(segment)
            slide_audio = leading_silence + segment + trailing_silence
            timeline += slide_audio
            cursor_ms += len(slide_audio)
            generated_items.append({
                **item,
                "script": script,
                "start_seconds": round(start_ms / 1000, 3),
                "end_seconds": round(cursor_ms / 1000, 3),
                "duration_seconds": round(len(slide_audio) / 1000, 3),
                "speech_start_seconds": round(speech_start_ms / 1000, 3),
                "speech_end_seconds": round(speech_end_ms / 1000, 3),
            })
        await report_progress(progress_callback, progress_end, "Exporting generated lecture audio.")
        with open(output_path, "wb") as mp3_file:
            timeline.export(mp3_file, format="mp3", bitrate="192k")
    finally:
        for temp_path in temp_paths:
            try:
                temp_path.unlink()
            except OSError:
                pass
    return {
        "cue_count": len(cues),
        "slide_count": len(generated_items),
        "tts_request_count": len(generated_items),
        "tts_sync_mode": "natural_slide",
        "duration_ms": len(timeline),
        "voice_name": normalized_voice,
        "tts_provider": provider,
        "tts_device": "remote",
        "tts_speed": 1.0,
        "style_prompt": style_prompt or "",
        "slide_speech_padding_seconds": LECTURE_SLIDE_SPEECH_PADDING_SECONDS,
        "generated_timeline_items": generated_items,
        **usage_summary,
    }


async def transcribe_generated_lecture_audio(audio_path: Path, language: str = "ko") -> Tuple[str, str]:
    text = ""
    srt_text = ""
    async for status in transcribe_audio_async_generator(str(audio_path), language=language):
        if status["type"] == "result":
            text = status.get("text", "")
            srt_text = status.get("srt_text", "")
        elif status["type"] == "error":
            raise HTTPException(status_code=500, detail=status.get("error") or "Generated audio transcription failed.")
    return text, srt_text


def split_script_for_alignment(text: str) -> List[str]:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return []
    sentence_matches = re.findall(r"[^.!?。！？…]+[.!?。！？…]?|[^.!?。！？…]+$", text)
    sentences = [part.strip() for part in sentence_matches if part and part.strip()]
    chunks = []
    for sentence in sentences or [text]:
        chunks.extend(split_subtitle_text(sentence, SRT_MAX_CUE_CHARS))
    return [chunk for chunk in chunks if chunk.strip()]


def normalize_alignment_text(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]+", "", (text or "").lower())


def alignment_similarity(source_text: str, cue_text: str) -> float:
    source = normalize_alignment_text(source_text)
    cue = normalize_alignment_text(cue_text)
    if not source or not cue:
        return 0.0
    ratio = SequenceMatcher(None, source, cue).ratio()
    containment = min(len(source), len(cue)) / max(len(source), len(cue))
    if source in cue or cue in source:
        ratio = max(ratio, containment)
    return ratio


def proportional_script_entries(chunks: List[str], start: float, end: float) -> List[Dict]:
    if not chunks:
        return []
    start = float(start or 0)
    end = max(float(end or start + 0.2), start + 0.2)
    total_weight = sum(max(len(normalize_alignment_text(chunk)), 1) for chunk in chunks)
    cursor = start
    entries = []
    for index, chunk in enumerate(chunks):
        if index == len(chunks) - 1:
            chunk_end = end
        else:
            weight = max(len(normalize_alignment_text(chunk)), 1)
            chunk_end = min(end, cursor + (end - start) * weight / max(total_weight, 1))
        entries.append({"start": cursor, "end": max(chunk_end, cursor + 0.2), "text": chunk})
        cursor = entries[-1]["end"]
    return entries


def align_slide_script_to_cues(script: str, slide_cues: List[Dict], speech_start: float, speech_end: float) -> Tuple[List[Dict], int]:
    chunks = split_script_for_alignment(script)
    if not chunks:
        return [], 0
    if not slide_cues:
        return proportional_script_entries(chunks, speech_start, speech_end), 0

    entries = []
    cue_cursor = 0
    matched_count = 0
    fallback_entries = proportional_script_entries(chunks, speech_start, speech_end)

    for chunk_index, chunk in enumerate(chunks):
        remaining_chunks = len(chunks) - chunk_index - 1
        last_search_index = len(slide_cues) - remaining_chunks
        best_index = None
        best_score = 0.0
        for cue_index in range(cue_cursor, max(cue_cursor, last_search_index)):
            score = alignment_similarity(chunk, slide_cues[cue_index].get("text", ""))
            if score > best_score:
                best_score = score
                best_index = cue_index
        if best_index is not None and best_score >= 0.34:
            cue = slide_cues[best_index]
            entries.append({"start": cue["start"], "end": cue["end"], "text": chunk})
            cue_cursor = best_index + 1
            matched_count += 1
        else:
            entries.append(fallback_entries[chunk_index])

    repaired = []
    previous_end = speech_start
    for entry in entries:
        start = max(float(entry["start"]), previous_end)
        end = max(float(entry["end"]), start + 0.2)
        end = min(end, max(float(speech_end), start + 0.2))
        repaired.append({"start": start, "end": end, "text": entry["text"]})
        previous_end = end
    return repaired, matched_count


def align_generated_srt_to_lecture_scripts(generated_srt: str, timeline_items: List[Dict]) -> Tuple[str, Dict]:
    cues = parse_srt(generated_srt)
    if not cues or not timeline_items:
        return generated_srt, {"aligned": False, "reason": "missing_cues_or_timeline"}

    grouped: Dict[int, List[Dict]] = {index: [] for index in range(len(timeline_items))}
    unmatched: List[Dict] = []
    for cue in cues:
        midpoint = (float(cue["start"]) + float(cue["end"])) / 2
        match_index = None
        for index, item in enumerate(timeline_items):
            start = float(item.get("speech_start_seconds", item.get("start_seconds", 0)))
            end = float(item.get("speech_end_seconds", item.get("end_seconds", start)))
            if start - 0.25 <= midpoint <= end + 0.25:
                match_index = index
                break
        if match_index is None:
            unmatched.append(cue)
        else:
            grouped[match_index].append(cue)

    entries = []
    replaced_count = 0
    for index, item in enumerate(timeline_items):
        slide_cues = grouped.get(index) or []
        script = str(item.get("script") or "").strip()
        speech_start = float(item.get("speech_start_seconds", item.get("start_seconds", 0)))
        speech_end = float(item.get("speech_end_seconds", item.get("end_seconds", speech_start + 0.2)))
        slide_entries, matched_count = align_slide_script_to_cues(script, slide_cues, speech_start, speech_end)
        entries.extend(slide_entries)
        replaced_count += len(slide_entries)

    for cue in unmatched:
        entries.append({"start": cue["start"], "end": cue["end"], "text": cue["text"]})

    entries.sort(key=lambda item: (item["start"], item["end"]))
    aligned_srt = "\n\n".join(
        format_srt_entry(index, item["start"], item["end"], item["text"])
        for index, item in enumerate(entries, start=1)
    )
    return aligned_srt, {
        "aligned": True,
        "source": "excel_script_with_whisper_timing",
        "cue_count": len(cues),
        "aligned_cue_count": replaced_count,
        "unmatched_cue_count": len(unmatched),
    }


def ffprobe_json(path: Path) -> Dict:
    return video_utils.ffprobe_json(path)


def media_duration_seconds(path: Path) -> float:
    return video_utils.media_duration_seconds(path)


def has_audio_stream(path: Path) -> bool:
    return video_utils.has_audio_stream(path)


def source_video_path_for_file(file: Dict) -> Path:
    path = Path(file.get("media_path") or "")
    if not path.exists():
        raise HTTPException(status_code=404, detail="Source video file is missing.")
    return path


def trim_video_file(source_path: Path, output_path: Path, start_seconds: float, end_seconds: float) -> None:
    video_utils.trim_video_file(source_path, output_path, start_seconds, end_seconds)


def normalize_video_for_concat(source_path: Path, output_path: Path) -> None:
    video_utils.normalize_video_for_concat(source_path, output_path)


def concat_video_files(first_path: Path, second_path: Path, output_path: Path) -> None:
    concat_video_sequence([first_path, second_path], output_path)


def concat_video_sequence(source_paths: List[Path], output_path: Path) -> None:
    video_utils.concat_video_sequence(source_paths, output_path, OUTPUT_DIR)

async def correct_korean_srt(srt_text: str) -> str:
    require_gemini_ready()
    cues = parse_srt(srt_text)
    if not cues:
        raise HTTPException(status_code=400, detail="No valid Korean SRT cues found.")
    source_items = [
        {
            "index": cue["index"],
            "start": cue["start_code"],
            "end": cue["end_code"],
            "text": cue["text"],
        }
        for cue in cues
    ]
    prompt = (
        "You are conservatively correcting Korean SRT subtitles. Your highest priority is preserving every spoken idea. "
        "Do not summarize, omit, shorten, paraphrase broadly, or remove previously spoken content. "
        "Fix clear typos, spacing errors, obvious speech-to-text mistakes, repeated junk tokens, punctuation, and non-meaning filler sounds. "
        "Remove or clean hesitation fillers such as '어..', '어...', '음..', '음...', '아..', and similar filler at the start of a cue when it does not change meaning. "
        "If a cue contains only filler and removing it would make the cue empty, keep the cue but clean punctuation or leave the least intrusive text. "
        "You may make very small wording corrections only when the original is clearly a recognition error. "
        "Keep the same number of subtitle items, keep every original index, and keep the same order. "
        "Do not merge cues, split cues, add new cues, delete cues, or translate. "
        "Keep start/end timecodes unchanged unless a timecode is obviously invalid or overlapping; if unsure, keep the original time. "
        "Return JSON only as an array of objects with index, start, end, and text. "
        "Use SRT timecode strings for start/end (HH:MM:SS,mmm). Preserve technical terms and names. "
        "If a cue is awkward but understandable, preserve it rather than rewriting it.\n\n"
        f"{json.dumps(source_items, ensure_ascii=False)}"
    )
    raw_text = (await asyncio.to_thread(generate_gemini_text, prompt, "translate_en")).strip()
    raw_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text, flags=re.IGNORECASE | re.DOTALL).strip()
    try:
        corrected_items = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f"Correction response was not valid JSON: {exc}")
    indexed_srt = normalize_corrected_srt_by_index(corrected_items, cues)
    if indexed_srt:
        return indexed_srt

    normalized_items = normalize_corrected_srt_items(corrected_items, cues)
    if normalized_items:
        return build_srt_from_timed_items(normalized_items)

    corrected_by_index = {
        int(item.get("index")): str(item.get("text", "")).strip()
        for item in corrected_items
        if isinstance(item, dict) and item.get("index") is not None
    }
    return build_srt(cues, [
        clean_corrected_subtitle_text(corrected_by_index.get(cue["index"], cue["text"]), cue["text"])
        for cue in cues
    ])


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """메인 페이지를 반환합니다."""
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()


async def process_single_file(file: UploadFile, file_index: int, total_files: int):
    """단일 파일을 처리하고 진행 상황을 생성합니다."""
    file_prefix = f"[{file_index}/{total_files}] {file.filename}"
    filename_lower = file.filename.lower()
    video_extensions = ('.mp4', '.mov', '.avi', '.mkv', '.webm')
    audio_extensions = ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma', '.opus', '.webm')
    text_extensions = ('.txt', '.srt')

    is_video = filename_lower.endswith(video_extensions)
    is_audio = filename_lower.endswith(audio_extensions)
    is_text = filename_lower.endswith(text_extensions)
    is_srt_file = filename_lower.endswith('.srt')

    if not (is_video or is_audio or is_text):
        yield await send_progress(
            f"{file_prefix}: 지원하지 않는 파일 형식입니다. (지원: 영상/음성/텍스트)",
            0,
            "error",
        )
        return

    if file.filename.startswith("recording_"):
        file_type = "recording"
    elif is_srt_file:
        file_type = "srt_project"
    elif is_text:
        file_type = "text"
    elif is_video:
        file_type = "video"
    else:
        file_type = "audio"

    unique_id = str(uuid.uuid4())
    file_suffix = Path(file.filename).suffix or ".bin"
    video_path = MEDIA_DIR / f"{unique_id}{file_suffix}"
    audio_path = UPLOAD_DIR / f"{unique_id}.wav"
    keep_media = False

    file_record = db.create_file_record(
        filename=file.filename,
        file_type=file_type,
        original_text="",
    )
    file_id = file_record["id"]
    upload_job = db.create_job(file_id, "upload_process", {"filename": file.filename})
    job_id = upload_job["id"]

    async def upload_progress(message: str, progress: int, status: str = "processing"):
        if status in {"started", "processing"}:
            db.update_job(job_id, status="running", progress=progress, message=message)
        elif status == "completed":
            db.update_job(job_id, status="completed", progress=progress, message=message)
        elif status == "error":
            db.update_job(job_id, status="failed", progress=progress, message=message)
        data = {
            "message": message,
            "progress": progress,
            "status": status,
            "file_id": file_id,
            "job_id": job_id,
            "filename": file.filename,
        }
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    try:
        yield await upload_progress(f"{file_prefix}: 업로드 작업 생성 완료", 1, "started")
        yield await upload_progress(f"{file_prefix}: 업로드 중...", 5, "processing")
        content = await file.read()

        yield await upload_progress(f"{file_prefix}: 파일 저장 중...", 15, "processing")
        with open(video_path, "wb") as buffer:
            buffer.write(content)
        print(f"비디오 파일 저장 완료: {video_path}")

        yield await upload_progress(f"{file_prefix}: 파일 검증 중...", 25, "processing")
        await asyncio.sleep(0.3)

        srt_text = ""
        english_srt_text = ""

        if is_text:
            yield await upload_progress(f"{file_prefix}: 텍스트 파일 읽는 중...", 30, "processing")
            try:
                text = content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    text = content.decode('cp949')
                except:
                    text = content.decode('latin-1')

            yield await upload_progress(f"{file_prefix}: 텍스트 읽기 완료", 90, "processing")
            print(f"텍스트 파일 읽기 완료! 텍스트 길이: {len(text)}")

            text = text.lstrip("\ufeff")
            if parse_srt(text):
                has_korean = bool(re.search(r"[\uac00-\ud7a3]", text))
                if has_korean:
                    srt_text = text
                else:
                    english_srt_text = text

        elif is_audio:
            keep_media = True
            yield await upload_progress(f"{file_prefix}: 음성 파일 확인 완료", 30, "processing")

            yield await upload_progress(f"{file_prefix}: 음성 전처리 중...", 40, "processing")
            try:
                await asyncio.to_thread(export_preprocessed_audio, str(video_path), str(audio_path))
            except Exception as e:
                print(f"음성 전처리 오류: {e}")
                db.update_job(job_id, status="failed", progress=0, message="음성 전처리 실패", error=str(e))
                yield await upload_progress(f"{file_prefix}: 음성 전처리 실패", 0, "error")
                return

            yield await upload_progress(f"{file_prefix}: 음성 파일 준비 완료", 55, "processing")
        else:
            keep_media = True
            yield await upload_progress(f"{file_prefix}: 오디오 추출 준비 중...", 30, "processing")
            await asyncio.sleep(0.2)

            yield await upload_progress(f"{file_prefix}: 오디오 추출 중...", 35, "processing")
            print("오디오 추출 중...")
            if not await extract_audio_from_video_async(str(video_path), str(audio_path)):
                db.update_job(job_id, status="failed", progress=0, message="오디오 추출 실패")
                yield await upload_progress(f"{file_prefix}: 오디오 추출 실패", 0, "error")
                return

            yield await upload_progress(f"{file_prefix}: 오디오 추출 완료", 55, "processing")
            print("오디오 추출 완료!")

        if not is_text:
            yield await upload_progress(f"{file_prefix}: 음성 인식 엔진 준비 중...", 60, "processing")
            await asyncio.sleep(0.2)

            yield await upload_progress(f"{file_prefix}: 음성 인식 시작 (대기 중일 수 있습니다)", 65, "processing")
            print(f"음성 인식 시작: {file.filename}")

            text = None
            async for status in transcribe_audio_async_generator(str(audio_path), language="ko"):
                if status["type"] == "waiting":
                    total = status.get("total", 0)
                    yield await upload_progress(f"{file_prefix}: GPU 음성 인식 대기 중 ({total} 구간 준비 완료)", 64, "processing")
                elif status["type"] == "gpu_start":
                    total = status.get("total", 0)
                    yield await upload_progress(f"{file_prefix}: GPU 음성 인식 시작 ({total} 구간)", 65, "processing")
                elif status["type"] == "progress":
                    current = status["current"]
                    total = status["total"]
                    prog = 65 + int((current / total) * 25)
                    yield await upload_progress(f"{file_prefix}: 음성 인식 중... ({current}/{total} 구간)", prog, "processing")
                elif status["type"] == "result":
                    text = status["text"]
                    srt_text = status.get("srt_text", "")
                elif status["type"] == "error":
                    db.update_job(job_id, status="failed", progress=0, message="음성 인식 실패", error=status["error"])
                    yield await upload_progress(f"{file_prefix}: 음성 인식 실패 - {status['error']}", 0, "error")
                    return

            if text is None:
                db.update_job(job_id, status="failed", progress=0, message="음성 인식 실패")
                yield await upload_progress(f"{file_prefix}: 음성 인식 실패", 0, "error")
                return

            yield await upload_progress(f"{file_prefix}: 음성 인식 완료", 90, "processing")
            print(f"음성 인식 완료! 텍스트 길이: {len(text)}")

        yield await upload_progress(f"{file_prefix}: 데이터베이스 저장 중...", 93, "processing")

        thumbnail_path = ""
        if file_type == "video" and keep_media:
            candidate_thumbnail = THUMBNAIL_DIR / f"{unique_id}.jpg"
            if await asyncio.to_thread(generate_video_thumbnail, video_path, candidate_thumbnail):
                thumbnail_path = str(candidate_thumbnail)

        db.update_file_fields(
            file_id,
            original_text=text,
            srt_text=srt_text,
            english_srt_text=english_srt_text,
            media_path=str(video_path) if keep_media else "",
            thumbnail_path=thumbnail_path,
        )

        yield await upload_progress(f"{file_prefix}: 결과 정리 중...", 96, "processing")
        await asyncio.sleep(0.2)

        result = {
            "message": f"{file_prefix}: 완료!",
            "progress": 100,
            "status": "completed",
            "filename": file.filename,
            "text": text,
            "srt_text": srt_text,
            "file_id": file_id,
            "file_type": file_type,
            "media_available": bool(keep_media),
            "has_srt": bool(srt_text),
            "thumbnail_url": f"/api/files/{file_id}/thumbnail" if thumbnail_path else None,
        }
        db.update_job(job_id, status="completed", progress=100, message=f"{file_prefix}: 완료")
        yield f"data: {json.dumps(result, ensure_ascii=False)}\n\n"

    except Exception as e:
        print(f"오류 발생: {e}")
        error_msg = f"{file_prefix}: 처리 중 오류 발생 - {str(e)}"
        db.update_job(job_id, status="failed", progress=0, message="업로드 처리 실패", error=str(e))
        yield await upload_progress(error_msg, 0, "error")

    finally:
        try:
            if video_path.exists() and not keep_media:
                video_path.unlink()
            if audio_path.exists():
                audio_path.unlink()
        except Exception as e:
            print(f"임시 파일 삭제 오류: {e}")


@app.post("/upload")
async def upload_videos(files: List[UploadFile] = File(...)):
    """여러 MP4 파일을 업로드하고 텍스트로 변환합니다 (SSE 스트리밍)."""
    
    async def event_generator():
        try:
            total_files = len(files)
            yield await send_progress(f"총 {total_files}개 파일 처리 시작", 0, "started")
            
            # 각 파일을 순차적으로 처리
            for idx, file in enumerate(files, 1):
                async for progress_msg in process_single_file(file, idx, total_files):
                    yield progress_msg
            
            # 모든 파일 처리 완료
            yield await send_progress("모든 파일 처리 완료!", 100, "all_completed")
            
        except Exception as e:
            print(f"전체 처리 오류: {e}")
            yield await send_progress(f"오류 발생: {str(e)}", 0, "error")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ============ 대시보드 API ============

async def run_lecture_project_job(job_id: str, file_id: str, metadata: Dict):
    async def job_progress(progress: int, message: str) -> None:
        db.update_job(job_id, status="running", progress=progress, message=message)

    usage_token = ai_usage.AI_USAGE_CONTEXT.set({"file_id": file_id, "job_id": job_id})
    db.update_job(job_id, status="running", progress=4, message="Lecture slide project started.")
    try:
        file = db.get_file_by_id(file_id)
        if not file:
            raise HTTPException(status_code=404, detail="File not found.")
        timeline_items = metadata.get("timeline_items") or []
        slide_paths = {name: Path(path) for name, path in (metadata.get("slide_manifest") or {}).items()}
        language = (metadata.get("language") or "ko").lower()
        final_output = metadata.get("final_output") or "captioned_dub_video"
        if final_output not in {"audio", "subtitle_video", "dub_video", "captioned_dub_video"}:
            final_output = "captioned_dub_video"

        await job_progress(10, "Generating natural slide-by-slide voice.")
        base_name = sanitize_output_name(file.get("filename") or "lecture_slide_project")
        audio_output_path = OUTPUT_DIR / f"{base_name}_{language}_lecture_audio_{uuid.uuid4().hex[:8]}.mp3"
        audio_metadata = await synthesize_lecture_audio_by_slides(
            timeline_items,
            metadata.get("script_text", ""),
            language,
            audio_output_path,
            voice_name=metadata.get("voice_name"),
            style_prompt=metadata.get("style_prompt"),
            tts_provider=metadata.get("tts_provider"),
            progress_callback=job_progress,
            progress_start=12,
            progress_end=56,
        )
        audio_artifact = db.create_artifact(
            file_id,
            "audio",
            language,
            str(audio_output_path),
            audio_output_path.name,
            {**audio_metadata, "srt_source": "generated", "variant": "lecture_natural_slide"},
        )

        await job_progress(60, "Transcribing generated voice into actual SRT.")
        generated_text, generated_srt = await transcribe_generated_lecture_audio(audio_output_path, language=language)
        if not generated_srt:
            raise HTTPException(status_code=500, detail="Generated audio transcription returned no SRT.")
        generated_timeline_items = audio_metadata.get("generated_timeline_items") or timeline_items
        aligned_srt, alignment_metadata = align_generated_srt_to_lecture_scripts(generated_srt, generated_timeline_items)
        metadata["srt_alignment"] = alignment_metadata
        if language == "en":
            db.update_file_fields(file_id, original_text=file.get("original_text", ""), english_srt_text=aligned_srt)
            metadata["srt_source"] = "english"
        else:
            db.update_file_fields(file_id, original_text=file.get("original_text", ""), srt_text=aligned_srt)
            metadata["srt_source"] = "original"
        file = db.get_file_by_id(file_id)

        await job_progress(68, "Creating slide video from generated voice durations.")
        slide_video_path = OUTPUT_DIR / f"{base_name}_slides_{uuid.uuid4().hex[:8]}.mp4"
        await asyncio.to_thread(create_lecture_slide_video, generated_timeline_items, slide_paths, slide_video_path)
        thumbnail_path = ""
        candidate_thumbnail = THUMBNAIL_DIR / f"{slide_video_path.stem}.jpg"
        if await asyncio.to_thread(generate_video_thumbnail, slide_video_path, candidate_thumbnail):
            thumbnail_path = str(candidate_thumbnail)
        db.update_file_fields(file_id, media_path=str(slide_video_path), thumbnail_path=thumbnail_path)
        file = db.get_file_by_id(file_id)

        await job_progress(76, "Slide video ready. Creating requested output.")
        subtitle_style = SubtitleStyleRequest(**metadata["subtitle_style"]) if metadata.get("subtitle_style") else None
        result_artifact_id = audio_artifact["id"]
        if final_output == "audio":
            db.update_job(job_id, status="completed", progress=100, message="Lecture audio generated.", result_artifact_id=result_artifact_id)
            return

        file = db.get_file_by_id(file_id)
        if final_output == "subtitle_video":
            artifact = await create_subtitle_video_artifact_for_file(
                file,
                language,
                srt_source=metadata.get("srt_source") or ("english" if language == "en" else "original"),
                subtitle_style=subtitle_style,
                progress_callback=job_progress,
            )
        elif final_output == "dub_video":
            artifact = await create_video_artifact_for_file(
                file,
                language,
                srt_source=metadata.get("srt_source") or ("english" if language == "en" else "original"),
                audio_artifact_id=audio_artifact["id"],
                require_existing_audio=True,
                progress_callback=job_progress,
                progress_start=78,
                progress_end=94,
            )
        else:
            artifact = await create_captioned_dub_video_artifact_for_file(
                file,
                language,
                srt_source=metadata.get("srt_source") or ("english" if language == "en" else "original"),
                subtitle_style=subtitle_style,
                audio_artifact_id=audio_artifact["id"],
                require_existing_audio=True,
                progress_callback=job_progress,
                progress_start=78,
                progress_end=96,
            )
        result_artifact_id = artifact["id"]
        db.update_job(job_id, status="completed", progress=100, message="Lecture video generated.", result_artifact_id=result_artifact_id)
    except Exception as e:
        detail = getattr(e, "detail", str(e))
        db.update_job(job_id, status="failed", progress=0, message="Lecture project failed.", error=str(detail))
    finally:
        ai_usage.AI_USAGE_CONTEXT.reset(usage_token)


async def run_ai_video_project_job(job_id: str, file_id: str, metadata: Dict):
    async def job_progress(progress: int, message: str) -> None:
        db.update_job(job_id, status="running", progress=progress, message=message)

    usage_token = ai_usage.AI_USAGE_CONTEXT.set({"file_id": file_id, "job_id": job_id})
    db.update_job(job_id, status="running", progress=4, message="AI video project started.")
    try:
        file = db.get_file_by_id(file_id)
        if not file:
            raise HTTPException(status_code=404, detail="AI video project file not found.")
        language = metadata.get("language") or "ko"
        final_output = metadata.get("final_output") or "captioned_dub_video"
        scenes = metadata.get("scenes") or []
        timeline_items = metadata.get("timeline_items") or ai_video_timeline_items(scenes)
        project_dir = Path(metadata.get("project_dir") or MEDIA_DIR / f"ai_video_{file_id}")
        project_dir.mkdir(parents=True, exist_ok=True)
        base_name = sanitize_output_name(file.get("filename") or "ai_video_project")

        if normalize_ai_video_visual_mode(metadata.get("visual_mode")) == "veo":
            await job_progress(10, "Generating Veo short-form clips.")
            clip_paths, clip_metadata, planned_srt = await generate_ai_video_scene_clips(
                scenes,
                project_dir,
                language,
                metadata.get("voice_name"),
                metadata.get("style_prompt"),
                metadata.get("tts_provider"),
                metadata.get("visual_provider"),
                progress_callback=job_progress,
            )
            if not clip_paths:
                raise HTTPException(status_code=500, detail="No generated scene clips.")
            metadata["clip_generation"] = clip_metadata
            metadata["srt_source"] = "original"
            if language == "en":
                db.update_file_fields(file_id, english_srt_text=planned_srt)
                metadata["srt_source"] = "english"
            else:
                db.update_file_fields(file_id, srt_text=planned_srt)
            db.update_job(job_id, metadata=metadata)

            await job_progress(74, "Editing short-form clips.")
            short_video_path = OUTPUT_DIR / f"{base_name}_veo_shorts_{uuid.uuid4().hex[:8]}.mp4"
            if len(clip_paths) == 1:
                shutil.copyfile(clip_paths[0], short_video_path)
            else:
                await asyncio.to_thread(concat_video_sequence, clip_paths, short_video_path)
            thumbnail_path = ""
            candidate_thumbnail = THUMBNAIL_DIR / f"{short_video_path.stem}.jpg"
            if await asyncio.to_thread(generate_video_thumbnail, short_video_path, candidate_thumbnail):
                thumbnail_path = str(candidate_thumbnail)
            db.update_file_fields(file_id, media_path=str(short_video_path), thumbnail_path=thumbnail_path)

            video_artifact = db.create_artifact(
                file_id,
                "video",
                language,
                str(short_video_path),
                short_video_path.name,
                {
                    "variant": "ai_video_veo_shorts",
                    "clip_count": len(clip_paths),
                    "clip_generation": clip_metadata,
                    "srt_source": metadata["srt_source"],
                    "duration_seconds": video_utils.media_duration_seconds(short_video_path),
                },
            )
            result_artifact = video_artifact
            if final_output == "audio":
                audio_path = OUTPUT_DIR / f"{base_name}_veo_audio_{uuid.uuid4().hex[:8]}.mp3"
                await asyncio.to_thread(export_preprocessed_audio, str(short_video_path), str(audio_path))
                result_artifact = db.create_artifact(
                    file_id,
                    "audio",
                    language,
                    str(audio_path),
                    audio_path.name,
                    {
                        "variant": "ai_video_veo_shorts",
                        "source_video_artifact_id": video_artifact["id"],
                        "clip_count": len(clip_paths),
                    },
                )
                db.update_job(job_id, status="completed", progress=100, message="AI Veo short audio generated.", result_artifact_id=result_artifact["id"])
                return
            if final_output in {"subtitle_video", "captioned_dub_video"} and planned_srt.strip():
                await job_progress(88, "Burning subtitles into Veo short.")
                subtitle_style = SubtitleStyleRequest(**metadata["subtitle_style"]) if metadata.get("subtitle_style") else None
                captioned_path = OUTPUT_DIR / f"{base_name}_veo_captioned_{uuid.uuid4().hex[:8]}.mp4"
                normalized_style = await asyncio.to_thread(
                    burn_subtitles_into_video,
                    short_video_path,
                    planned_srt,
                    captioned_path,
                    subtitle_style,
                )
                result_artifact = db.create_artifact(
                    file_id,
                    "captioned_dub_video" if final_output == "captioned_dub_video" else "subtitle_video",
                    language,
                    str(captioned_path),
                    captioned_path.name,
                    {
                        "variant": "ai_video_veo_shorts",
                        "source_video_artifact_id": video_artifact["id"],
                        "subtitle_style": normalized_style,
                        "srt_source": metadata["srt_source"],
                        "clip_count": len(clip_paths),
                    },
                )
            db.update_job(job_id, status="completed", progress=100, message="AI Veo short generated.", result_artifact_id=result_artifact["id"])
            return

        await job_progress(12, "Generating scene images.")
        slide_manifest, image_metadata = await generate_ai_video_scene_images(
            scenes,
            project_dir,
            visual_provider=metadata.get("visual_provider"),
            progress_callback=job_progress,
        )
        metadata["slide_manifest"] = slide_manifest
        metadata["image_generation"] = image_metadata
        db.update_job(job_id, metadata=metadata)

        await job_progress(50, "Generating narration voice.")
        audio_output_path = OUTPUT_DIR / f"{base_name}_{language}_ai_video_audio_{uuid.uuid4().hex[:8]}.mp3"
        audio_metadata = await synthesize_lecture_audio_by_slides(
            timeline_items,
            "",
            language,
            audio_output_path,
            voice_name=metadata.get("voice_name"),
            style_prompt=metadata.get("style_prompt"),
            tts_provider=metadata.get("tts_provider"),
            progress_callback=job_progress,
            progress_start=50,
            progress_end=72,
        )
        audio_artifact = db.create_artifact(
            file_id,
            "audio",
            language,
            str(audio_output_path),
            audio_output_path.name,
            {**audio_metadata, "srt_source": "generated", "variant": "ai_video_project"},
        )

        await job_progress(74, "Transcribing generated voice into actual SRT.")
        generated_text, generated_srt = await transcribe_generated_lecture_audio(audio_output_path, language=language)
        if not generated_srt:
            raise HTTPException(status_code=500, detail="Generated audio transcription returned no SRT.")
        generated_timeline_items = audio_metadata.get("generated_timeline_items") or timeline_items
        aligned_srt, alignment_metadata = align_generated_srt_to_lecture_scripts(generated_srt, generated_timeline_items)
        metadata["srt_alignment"] = alignment_metadata
        if language == "en":
            db.update_file_fields(file_id, original_text=file.get("original_text", ""), english_srt_text=aligned_srt)
            metadata["srt_source"] = "english"
        else:
            db.update_file_fields(file_id, original_text=file.get("original_text", ""), srt_text=aligned_srt)
            metadata["srt_source"] = "original"
        db.update_job(job_id, metadata=metadata)

        await job_progress(82, "Creating image video from generated voice durations.")
        slide_paths = {name: Path(path) for name, path in slide_manifest.items()}
        slide_video_path = OUTPUT_DIR / f"{base_name}_images_{uuid.uuid4().hex[:8]}.mp4"
        await asyncio.to_thread(create_lecture_slide_video, generated_timeline_items, slide_paths, slide_video_path)
        thumbnail_path = ""
        candidate_thumbnail = THUMBNAIL_DIR / f"{slide_video_path.stem}.jpg"
        if await asyncio.to_thread(generate_video_thumbnail, slide_video_path, candidate_thumbnail):
            thumbnail_path = str(candidate_thumbnail)
        db.update_file_fields(file_id, media_path=str(slide_video_path), thumbnail_path=thumbnail_path)

        await job_progress(88, "Creating requested output.")
        file = db.get_file_by_id(file_id)
        subtitle_style = SubtitleStyleRequest(**metadata["subtitle_style"]) if metadata.get("subtitle_style") else None
        result_artifact_id = audio_artifact["id"]
        if final_output == "audio":
            db.update_job(job_id, status="completed", progress=100, message="AI video audio generated.", result_artifact_id=result_artifact_id)
            return
        if final_output == "subtitle_video":
            artifact = await create_subtitle_video_artifact_for_file(
                file,
                language,
                srt_source=metadata.get("srt_source") or ("english" if language == "en" else "original"),
                subtitle_style=subtitle_style,
                progress_callback=job_progress,
                progress_start=88,
                progress_end=96,
            )
        elif final_output == "dub_video":
            artifact = await create_video_artifact_for_file(
                file,
                language,
                srt_source=metadata.get("srt_source") or ("english" if language == "en" else "original"),
                audio_artifact_id=audio_artifact["id"],
                require_existing_audio=True,
                progress_callback=job_progress,
                progress_start=88,
                progress_end=96,
            )
        else:
            artifact = await create_captioned_dub_video_artifact_for_file(
                file,
                language,
                srt_source=metadata.get("srt_source") or ("english" if language == "en" else "original"),
                subtitle_style=subtitle_style,
                audio_artifact_id=audio_artifact["id"],
                require_existing_audio=True,
                progress_callback=job_progress,
                progress_start=88,
                progress_end=98,
            )
        db.update_job(job_id, status="completed", progress=100, message="AI video generated.", result_artifact_id=artifact["id"])
    except Exception as e:
        detail = getattr(e, "detail", str(e))
        db.update_job(job_id, status="failed", progress=0, message="AI video project failed.", error=str(detail))
    finally:
        ai_usage.AI_USAGE_CONTEXT.reset(usage_token)


@app.get("/api/lecture-projects/template")
async def download_lecture_timeline_template():
    template = create_lecture_timeline_template()
    return StreamingResponse(
        io.BytesIO(template),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="lecture_timeline_template.xlsx"'},
    )


@app.post("/api/lecture-projects")
async def create_lecture_project(
    background_tasks: BackgroundTasks,
    slides: List[UploadFile] = File(...),
    timeline_file: UploadFile = File(...),
    language: str = Form("ko"),
    final_output: str = Form("captioned_dub_video"),
    tts_provider: Optional[str] = Form(None),
    voice_name: Optional[str] = Form(None),
    style_prompt: Optional[str] = Form(None),
    subtitle_style: Optional[str] = Form(None),
):
    if not slides:
        raise HTTPException(status_code=400, detail="At least one slide image or HTML file is required.")
    slide_payloads: List[Tuple[str, bytes]] = []
    seen_names = set()
    for slide in slides:
        filename = safe_upload_filename(slide.filename or "")
        if Path(filename).suffix.lower() not in LECTURE_SLIDE_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"Unsupported slide file: {filename}")
        if filename in seen_names:
            raise HTTPException(status_code=400, detail=f"Duplicate slide filename: {filename}")
        seen_names.add(filename)
        slide_payloads.append((filename, await slide.read()))
    timeline_content = await timeline_file.read()
    uploaded_names = [name for name, _ in slide_payloads]
    validation = parse_lecture_timeline_xlsx(timeline_content, lecture_available_slide_references(uploaded_names), "")
    document_slide_aliases: Dict[str, str] = {}
    if validation["errors"] and can_auto_map_missing_slides_to_single_document(validation, uploaded_names):
        document_filename = next(
            name for name in uploaded_names
            if Path(name).suffix.lower() in LECTURE_HTML_SLIDE_EXTENSIONS | LECTURE_PDF_SLIDE_EXTENSIONS
        )
        document_slide_aliases = build_single_document_slide_aliases(validation, document_filename)
        validation = parse_lecture_timeline_xlsx(
            timeline_content,
            lecture_available_slide_references(uploaded_names) + list(document_slide_aliases.keys()),
            "",
        )
        if document_slide_aliases and not validation["errors"]:
            validation["warnings"] = [
                warning for warning in validation["warnings"]
                if document_filename not in warning
            ]
            validation["warnings"].append(
                f"Mapped {len(document_slide_aliases)} XLSX slide filenames to '{document_filename}' pages by slide_no."
            )
    if validation["errors"]:
        raise HTTPException(status_code=400, detail={"errors": validation["errors"], "warnings": validation["warnings"]})
    script_text = "\n".join(f"{item['slide_no']}. {item['text']}" for item in validation.get("scripts", []))

    language = (language or "ko").lower()
    provider, normalized_voice = normalize_tts_selection(language, tts_provider, voice_name)
    subtitle_style_data = None
    if subtitle_style:
        try:
            subtitle_style_data = json.loads(subtitle_style)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="subtitle_style must be valid JSON.")
        SubtitleStyleRequest(**subtitle_style_data)

    project_name = Path(timeline_file.filename or "lecture_slide_project.xlsx").stem or "lecture_slide_project"
    file_record = db.create_file_record(
        filename=f"{project_name}.xlsx",
        file_type="lecture_slide_project",
        original_text=script_text,
        srt_text="",
        english_srt_text="",
    )
    project_dir = MEDIA_DIR / f"lecture_{file_record['id']}"
    project_dir.mkdir(parents=True, exist_ok=True)
    slide_manifest: Dict[str, str] = {}
    source_manifest: Dict[str, str] = {}
    html_paths: Dict[str, Path] = {}
    pdf_paths: Dict[str, Path] = {}
    for filename, content in slide_payloads:
        path = project_dir / filename
        path.write_bytes(content)
        source_manifest[filename] = str(path)
        suffix = Path(filename).suffix.lower()
        if suffix in LECTURE_IMAGE_SLIDE_EXTENSIONS:
            slide_manifest[filename] = str(path)
        elif suffix in LECTURE_HTML_SLIDE_EXTENSIONS:
            html_paths[filename] = path
        elif suffix in LECTURE_PDF_SLIDE_EXTENSIONS:
            pdf_paths[filename] = path

    requested_html_refs: Dict[str, List[str]] = {}
    requested_pdf_refs: Dict[str, List[str]] = {}
    rendered_aliases: Dict[str, str] = {}
    for item in validation["items"]:
        slide_ref = item["slide_file"]
        render_ref = document_slide_aliases.get(slide_ref, slide_ref)
        if render_ref != slide_ref:
            rendered_aliases[render_ref] = slide_ref
        document_filename, slide_index = split_html_slide_reference(render_ref)
        if document_filename in html_paths:
            requested_html_refs.setdefault(document_filename, []).append(render_ref)
        elif document_filename in pdf_paths:
            requested_pdf_refs.setdefault(document_filename, []).append(render_ref)
        elif Path(render_ref).suffix.lower() in LECTURE_HTML_SLIDE_EXTENSIONS and slide_index is None:
            requested_html_refs.setdefault(render_ref, []).append(render_ref)
        elif Path(render_ref).suffix.lower() in LECTURE_PDF_SLIDE_EXTENSIONS and slide_index is None:
            requested_pdf_refs.setdefault(render_ref, []).append(render_ref)

    if requested_html_refs:
        render_dir = project_dir / "rendered_html_slides"
        for html_filename, refs in requested_html_refs.items():
            html_path = html_paths.get(html_filename)
            if not html_path:
                raise HTTPException(status_code=400, detail=f"HTML slide file was not uploaded: {html_filename}")
            rendered_refs = await render_html_slide_refs(html_path, refs, render_dir)
            slide_manifest.update(rendered_refs)
            for rendered_ref, original_ref in rendered_aliases.items():
                if rendered_ref in rendered_refs:
                    slide_manifest[original_ref] = rendered_refs[rendered_ref]
    if requested_pdf_refs:
        render_dir = project_dir / "rendered_pdf_slides"
        for pdf_filename, refs in requested_pdf_refs.items():
            pdf_path = pdf_paths.get(pdf_filename)
            if not pdf_path:
                raise HTTPException(status_code=400, detail=f"PDF slide file was not uploaded: {pdf_filename}")
            rendered_refs = await asyncio.to_thread(render_pdf_slide_refs, pdf_path, refs, render_dir)
            slide_manifest.update(rendered_refs)
            for rendered_ref, original_ref in rendered_aliases.items():
                if rendered_ref in rendered_refs:
                    slide_manifest[original_ref] = rendered_refs[rendered_ref]

    timeline_path = project_dir / safe_upload_filename(timeline_file.filename or "timeline.xlsx")
    timeline_path.write_bytes(timeline_content)

    metadata = {
        "language": language,
        "final_output": final_output,
        "tts_provider": provider,
        "voice_name": normalized_voice,
        "style_prompt": style_prompt or "",
        "srt_source": "english" if language == "en" else "original",
        "subtitle_style": subtitle_style_data,
        "timeline_items": validation["items"],
        "script_text": script_text,
        "timeline_warnings": validation["warnings"],
        "slide_manifest": slide_manifest,
        "source_slide_manifest": source_manifest,
        "document_slide_aliases": document_slide_aliases,
        "timeline_path": str(timeline_path),
    }
    job = db.create_job(file_record["id"], "lecture_slide_project", metadata)
    background_tasks.add_task(run_lecture_project_job, job["id"], file_record["id"], metadata)
    return {
        "success": True,
        "file": prepare_file_for_api(db.get_file_by_id(file_record["id"]), include_original=True),
        "job": job,
        "validation": validation,
    }


@app.post("/api/ai-video-projects/draft")
async def create_ai_video_project_draft(request: AiVideoDraftRequest):
    draft = await asyncio.to_thread(generate_ai_video_draft, request)
    return {"success": True, "draft": draft}


@app.post("/api/ai-video-projects")
async def create_ai_video_project(
    request: AiVideoCreateRequest,
    background_tasks: BackgroundTasks,
):
    draft = AI_VIDEO_DRAFTS.get(request.draft_id or "") if request.draft_id else None
    source_scenes = request.scenes or [
        AiVideoSceneRequest(**scene)
        for scene in (draft.get("scenes", []) if draft else [])
    ]
    if not source_scenes:
        raise HTTPException(status_code=400, detail="At least one scene is required.")
    scene_limit = clamp_ai_video_scene_count(len(source_scenes))
    scenes = [
        normalize_ai_video_scene(scene.model_dump() if hasattr(scene, "model_dump") else scene.dict(), index + 1)
        for index, scene in enumerate(source_scenes[:scene_limit])
    ]
    character_assets = merge_ai_video_character_assets(
        default_ai_video_character_assets(),
        (draft or {}).get("character_assets") or [],
        request.character_assets or [],
    )
    attach_character_assets_to_scenes(scenes, character_assets)
    title = (request.title or (draft or {}).get("title") or request.topic or "ai_video_project").strip()
    topic = (request.topic or (draft or {}).get("topic") or title).strip()
    language = (request.language or (draft or {}).get("language") or "ko").lower()
    visual_mode = normalize_ai_video_visual_mode(request.visual_mode)
    aspect_ratio, aspect_warning = resolve_ai_video_aspect_ratio(
        request.image_style or (draft or {}).get("image_style") or "",
        visual_mode,
        request.aspect_ratio or (draft or {}).get("aspect_ratio"),
    )
    provider, normalized_voice = normalize_tts_selection(language, request.tts_provider, request.voice_name)
    script_text = ai_video_script_text(scenes)
    safe_title = sanitize_output_name(title or "ai_video_project")
    file_record = db.create_file_record(
        filename=f"{safe_title}.json",
        file_type="ai_video_project",
        original_text=script_text,
        srt_text="",
        english_srt_text="",
    )
    project_dir = MEDIA_DIR / f"ai_video_{file_record['id']}"
    project_dir.mkdir(parents=True, exist_ok=True)
    draft_path = project_dir / "draft.json"
    draft_payload = {
        "draft_id": request.draft_id or "",
        "title": title,
        "topic": topic,
        "language": language,
        "target_duration": request.target_duration or (draft or {}).get("target_duration") or "1-3분",
        "audience": request.audience or (draft or {}).get("audience") or "일반 시청자",
        "tone": request.tone or (draft or {}).get("tone") or "명확하고 자연스럽게",
        "image_style": request.image_style or (draft or {}).get("image_style") or "",
        "aspect_ratio": aspect_ratio,
        "aspect_ratio_warning": aspect_warning or "",
        "visual_mode": visual_mode,
        "visual_provider": normalize_ai_video_visual_provider(request.visual_provider),
        "character_assets": character_assets,
        "research_mode": (draft or {}).get("research_mode") or "manual",
        "scenes": scenes,
    }
    for scene in scenes:
        scene["aspect_ratio"] = aspect_ratio
    draft_path.write_text(json.dumps(draft_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    metadata = {
        **draft_payload,
        "language": language,
        "final_output": request.final_output or "captioned_dub_video",
        "tts_provider": provider,
        "voice_name": normalized_voice,
        "style_prompt": request.style_prompt or "",
        "srt_source": "english" if language == "en" else "original",
        "subtitle_style": request.subtitle_style.model_dump() if hasattr(request.subtitle_style, "model_dump") and request.subtitle_style else (request.subtitle_style.dict() if request.subtitle_style else None),
        "timeline_items": ai_video_timeline_items(scenes),
        "script_text": script_text,
        "project_dir": str(project_dir),
        "draft_path": str(draft_path),
    }
    job = db.create_job(file_record["id"], "ai_video_project", metadata)
    background_tasks.add_task(run_ai_video_project_job, job["id"], file_record["id"], metadata)
    return {
        "success": True,
        "file": prepare_file_for_api(db.get_file_by_id(file_record["id"]), include_original=True),
        "job": job,
    }


@app.post("/api/ai-video-projects/with-assets")
async def create_ai_video_project_with_assets(
    background_tasks: BackgroundTasks,
    payload: str = Form(...),
    character_images: Optional[List[UploadFile]] = File(None),
):
    try:
        payload_data = json.loads(payload)
        request = AiVideoCreateRequest(**payload_data)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid AI video payload: {exc}") from exc
    character_assets: List[Dict] = []
    asset_dir = AI_CHARACTER_ASSET_DIR
    asset_dir.mkdir(parents=True, exist_ok=True)
    for upload in character_images or []:
        filename = safe_upload_filename(upload.filename or f"character_{uuid.uuid4().hex}.png")
        suffix = Path(filename).suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg"}:
            raise HTTPException(status_code=400, detail=f"Unsupported character image file: {filename}")
        content = await upload.read()
        if not content:
            continue
        output_path = asset_dir / f"{uuid.uuid4().hex}_{filename}"
        output_path.write_bytes(content)
        character_assets.append({
            "name": Path(filename).stem,
            "filename": filename,
            "path": str(output_path),
        })
    request.character_assets = [*(request.character_assets or []), *character_assets]
    return await create_ai_video_project(request, background_tasks)


@app.get("/api/files")
async def get_all_files():
    """모든 파일 목록 조회"""
    try:
        files = [
            file for file in db.get_all_files()
            if file.get("type") != "video_edit" and file.get("file_type") != "video_edit"
        ]
        for file in files:
            prepare_file_for_api(file, include_original=False)
        
        return {"success": True, "files": files}
    except Exception as e:
        print(f"파일 목록 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/files/{file_id}")
async def get_file_detail(file_id: str):
    """파일 상세 정보 조회"""
    try:
        file = db.get_file_by_id(file_id)
        if not file:
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
        return {"success": True, "file": prepare_file_for_api(file, include_original=True)}
    except HTTPException:
        raise
    except Exception as e:
        print(f"파일 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/editor/upload")
async def upload_editor_videos(files: List[UploadFile] = File(...)):
    """Upload videos for the standalone editor without running subtitle or dubbing jobs."""
    try:
        if not files:
            raise HTTPException(status_code=400, detail="No video files were uploaded.")

        created_files = []
        allowed_extensions = (".mp4", ".mov", ".avi", ".mkv", ".webm")
        for upload_file in files:
            if not upload_file.filename:
                continue
            filename_lower = upload_file.filename.lower()
            if not filename_lower.endswith(allowed_extensions):
                raise HTTPException(status_code=400, detail="Only video files can be uploaded for editing.")

            suffix = Path(upload_file.filename).suffix.lower() or ".mp4"
            base_name = sanitize_output_name(Path(upload_file.filename).stem or "video")
            media_path = MEDIA_DIR / f"editor_{uuid.uuid4().hex}_{base_name}{suffix}"
            media_path.write_bytes(await upload_file.read())

            thumbnail_path = ""
            thumbnail_candidate = THUMBNAIL_DIR / f"{media_path.stem}.jpg"
            try:
                if await asyncio.to_thread(generate_video_thumbnail, media_path, thumbnail_candidate):
                    thumbnail_path = str(thumbnail_candidate)
            except Exception as exc:
                print(f"Editor thumbnail generation failed: {exc}")

            created = db.create_file_record(
                filename=upload_file.filename,
                file_type="video_edit",
                original_text="",
                media_path=str(media_path),
                thumbnail_path=thumbnail_path,
            )
            created_files.append(prepare_file_for_api(created, include_original=False))

        return {"success": True, "files": created_files}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Editor upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/editor/files")
async def get_editor_files():
    try:
        files = [
            file for file in db.get_all_files()
            if file.get("type") == "video_edit" or file.get("file_type") == "video_edit"
        ]
        for file in files:
            prepare_file_for_api(file, include_original=False)
        return {"success": True, "files": files}
    except Exception as e:
        print(f"Editor file list error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/editor/batch-logo-intro")
async def create_editor_logo_intro_batch(request: EditorLogoIntroBatchRequest):
    try:
        file_ids = [file_id for file_id in request.file_ids if file_id]
        if not file_ids:
            raise HTTPException(status_code=400, detail="Select at least one editor video.")
        position = (request.position or "before").lower()
        if position not in {"before", "after", "both"}:
            raise HTTPException(status_code=400, detail="Position must be before, after, or both.")
        if not DEFAULT_LOGO_INTRO_PATH.exists():
            raise HTTPException(status_code=404, detail="LogoIntro.mp4 preset is missing.")

        artifacts = []
        errors = []
        for file_id in file_ids:
            try:
                file = db.get_file_by_id(file_id)
                if not file:
                    raise HTTPException(status_code=404, detail="File not found.")
                if file.get("type") != "video_edit" and file.get("file_type") != "video_edit":
                    raise HTTPException(status_code=400, detail="Only standalone editor videos can use this batch action.")

                current_path = source_video_path_for_file(file)
                source_paths = []
                if position in {"before", "both"}:
                    source_paths.append(DEFAULT_LOGO_INTRO_PATH)
                source_paths.append(current_path)
                if position in {"after", "both"}:
                    source_paths.append(DEFAULT_LOGO_INTRO_PATH)

                base_name = sanitize_output_name(file.get("filename", "video"))
                output_path = OUTPUT_DIR / f"{base_name}_logo_intro_{position}_{uuid.uuid4().hex[:8]}.mp4"
                await asyncio.to_thread(concat_video_sequence, source_paths, output_path)
                artifact = db.create_artifact(
                    file_id,
                    "edited_video",
                    "ko",
                    str(output_path),
                    output_path.name,
                    {
                        "variant": "logo_intro",
                        "position": position,
                        "preset_filename": DEFAULT_LOGO_INTRO_PATH.name,
                        "duration_ms": int(media_duration_seconds(output_path) * 1000),
                    },
                )
                artifacts.append(artifact)
            except HTTPException as exc:
                errors.append({"file_id": file_id, "message": str(exc.detail)})
            except Exception as exc:
                errors.append({"file_id": file_id, "message": str(exc)})

        return {
            "success": True,
            "artifacts": artifacts,
            "errors": errors,
            "created_count": len(artifacts),
            "error_count": len(errors),
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Editor logo intro batch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/files/{file_id}/translate/en")
async def translate_file_to_english(file_id: str):
    try:
        file = db.get_file_by_id(file_id)
        if not file:
            raise HTTPException(status_code=404, detail="File not found.")
        if file.get("english_srt_text"):
            return {"success": True, "english_srt_text": file["english_srt_text"], "cached": True}
        usage_token = ai_usage.AI_USAGE_CONTEXT.set({"file_id": file_id})
        try:
            english_srt_text = await translate_srt_to_english(file.get("corrected_srt_text") or file.get("srt_text") or "")
        finally:
            ai_usage.AI_USAGE_CONTEXT.reset(usage_token)
        db.update_english_srt(file_id, english_srt_text)
        return {"success": True, "english_srt_text": english_srt_text, "cached": False}
    except HTTPException:
        raise
    except Exception as e:
        print(f"English SRT translation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/files/{file_id}/english-srt")
async def update_file_english_srt(file_id: str, request: EnglishSrtRequest):
    try:
        file = db.get_file_by_id(file_id)
        if not file:
            raise HTTPException(status_code=404, detail="File not found.")
        english_srt_text = (request.english_srt_text or "").strip()
        if not parse_srt(english_srt_text):
            raise HTTPException(status_code=400, detail="English SRT must include valid SRT timecodes.")
        db.update_english_srt(file_id, english_srt_text)
        return {"success": True, "english_srt_text": english_srt_text}
    except HTTPException:
        raise
    except Exception as e:
        print(f"English SRT update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/files/{file_id}/corrected-srt")
async def update_file_corrected_srt(file_id: str, request: CorrectedSrtRequest):
    try:
        file = db.get_file_by_id(file_id)
        if not file:
            raise HTTPException(status_code=404, detail="File not found.")
        corrected_srt_text = (request.corrected_srt_text or "").strip()
        if not parse_srt(corrected_srt_text):
            raise HTTPException(status_code=400, detail="Corrected SRT must include valid SRT timecodes.")
        db.update_file_fields(file_id, corrected_srt_text=corrected_srt_text)
        return {"success": True, "corrected_srt_text": corrected_srt_text}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Corrected SRT update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/files/{file_id}/srt/correct/ko")
async def correct_file_korean_srt(file_id: str):
    try:
        file = db.get_file_by_id(file_id)
        if not file:
            raise HTTPException(status_code=404, detail="File not found.")
        usage_token = ai_usage.AI_USAGE_CONTEXT.set({"file_id": file_id})
        try:
            corrected_srt_text = await correct_korean_srt(file.get("srt_text") or "")
        finally:
            ai_usage.AI_USAGE_CONTEXT.reset(usage_token)
        db.update_file_fields(file_id, corrected_srt_text=corrected_srt_text)
        return {"success": True, "corrected_srt_text": corrected_srt_text}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Korean SRT correction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/files/{file_id}/audio")
async def create_file_audio(file_id: str, request: LanguageRequest):
    try:
        file = db.get_file_by_id(file_id)
        if not file:
            raise HTTPException(status_code=404, detail="File not found.")
        artifact = await create_audio_artifact_for_file(
            file,
            request.language,
            voice_name=request.voice_name,
            style_prompt=request.style_prompt,
            srt_source=request.srt_source,
            tts_provider=request.tts_provider,
        )
        return artifact_api_response(artifact)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Audio generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/files/{file_id}/dub-video")
async def create_dubbed_video(file_id: str, request: LanguageRequest):
    try:
        file = db.get_file_by_id(file_id)
        if not file:
            raise HTTPException(status_code=404, detail="File not found.")
        artifact = await create_video_artifact_for_file(
            file,
            request.language,
            voice_name=request.voice_name,
            style_prompt=request.style_prompt,
            srt_source=request.srt_source,
            tts_provider=request.tts_provider,
            audio_artifact_id=request.audio_artifact_id,
        )
        return artifact_api_response(artifact)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Dubbed video generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/files/{file_id}/subtitle-video")
async def create_subtitled_video(file_id: str, request: LanguageRequest):
    try:
        file = db.get_file_by_id(file_id)
        if not file:
            raise HTTPException(status_code=404, detail="File not found.")
        artifact = await create_subtitle_video_artifact_for_file(
            file,
            request.language,
            srt_source=request.srt_source,
            subtitle_style=request.subtitle_style,
        )
        return artifact_api_response(artifact)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Subtitle video generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/files/{file_id}/captioned-dub-video")
async def create_captioned_dubbed_video(file_id: str, request: LanguageRequest):
    try:
        file = db.get_file_by_id(file_id)
        if not file:
            raise HTTPException(status_code=404, detail="File not found.")
        artifact = await create_captioned_dub_video_artifact_for_file(
            file,
            request.language,
            voice_name=request.voice_name,
            style_prompt=request.style_prompt,
            srt_source=request.srt_source,
            subtitle_style=request.subtitle_style,
            tts_provider=request.tts_provider,
            audio_artifact_id=request.audio_artifact_id,
        )
        return artifact_api_response(artifact)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Captioned dubbed video generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/files/{file_id}/edit/trim")
async def trim_file_video(file_id: str, request: TrimVideoRequest):
    file = db.get_file_by_id(file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found.")
    source_path = source_video_path_for_file(file)
    start = max(float(request.start_seconds or 0), 0.0)
    end = float(request.end_seconds or 0)
    if end <= start:
        raise HTTPException(status_code=400, detail="End time must be greater than start time.")
    base_name = sanitize_output_name(file.get("filename", "video"))
    output_path = OUTPUT_DIR / f"{base_name}_trim_{uuid.uuid4().hex[:8]}.mp4"
    await asyncio.to_thread(trim_video_file, source_path, output_path, start, end)
    artifact = db.create_artifact(
        file_id,
        "edited_video",
        "ko",
        str(output_path),
        output_path.name,
        {
            "variant": "trim",
            "source_video": "original",
            "start_seconds": start,
            "end_seconds": end,
            "duration_ms": int(max(end - start, 0) * 1000),
        },
    )
    return artifact_api_response(artifact)


@app.post("/api/files/{file_id}/edit/concat")
async def concat_file_video(
    file_id: str,
    position: str = Form("after"),
    existing_file_id: Optional[str] = Form(None),
    upload_file: Optional[UploadFile] = File(None),
    after_existing_file_id: Optional[str] = Form(None),
    after_upload_file: Optional[UploadFile] = File(None),
):
    file = db.get_file_by_id(file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found.")
    current_path = source_video_path_for_file(file)
    position = (position or "after").lower()
    if position not in {"before", "after", "both"}:
        raise HTTPException(status_code=400, detail="Position must be before, after, or both.")

    temp_upload_paths = []

    async def resolve_concat_source(upload: Optional[UploadFile], existing_id: Optional[str], role: str) -> Tuple[Path, str, str]:
        if upload and upload.filename:
            filename_lower = upload.filename.lower()
            if not filename_lower.endswith((".mp4", ".mov", ".avi", ".mkv", ".webm")):
                raise HTTPException(status_code=400, detail="Only video files can be concatenated.")
            temp_path = OUTPUT_DIR / f"concat_upload_{uuid.uuid4().hex}_{sanitize_output_name(upload.filename)}"
            temp_path.write_bytes(await upload.read())
            temp_upload_paths.append(temp_path)
            return temp_path, upload.filename, "upload"
        if existing_id:
            other_file = db.get_file_by_id(existing_id)
            if not other_file:
                raise HTTPException(status_code=404, detail=f"Selected {role} file was not found.")
            return source_video_path_for_file(other_file), other_file.get("filename") or existing_id, "existing_file"
        raise HTTPException(status_code=400, detail=f"Select a {role} video to concatenate.")

    before_path = before_label = before_source = None
    after_path = after_label = after_source = None
    if position in {"before", "both"}:
        before_path, before_label, before_source = await resolve_concat_source(upload_file, existing_file_id, "before")
    if position in {"after", "both"}:
        after_path, after_label, after_source = await resolve_concat_source(after_upload_file, after_existing_file_id, "after")

    source_paths = []
    if position in {"before", "both"}:
        source_paths.append(before_path)
    source_paths.append(current_path)
    if position in {"after", "both"}:
        source_paths.append(after_path)

    base_name = sanitize_output_name(file.get("filename", "video"))
    output_path = OUTPUT_DIR / f"{base_name}_concat_{position}_{uuid.uuid4().hex[:8]}.mp4"
    try:
        await asyncio.to_thread(concat_video_sequence, source_paths, output_path)
    finally:
        for temp_upload_path in temp_upload_paths:
            try:
                temp_upload_path.unlink()
            except OSError:
                pass

    artifact = db.create_artifact(
        file_id,
        "edited_video",
        "ko",
        str(output_path),
        output_path.name,
        {
            "variant": "concat",
            "position": position,
            "source_video": "original",
            "before_source": before_source or "",
            "before_filename": before_label or "",
            "after_source": after_source or "",
            "after_filename": after_label or "",
            "other_source": before_source or after_source or "",
            "other_file_id": existing_file_id or "",
            "other_filename": before_label or after_label or "",
            "after_file_id": after_existing_file_id or "",
            "duration_ms": int(media_duration_seconds(output_path) * 1000),
        },
    )
    return artifact_api_response(artifact)


@app.post("/api/script/audio")
async def create_script_audio(request: ScriptAudioRequest):
    try:
        script = (request.script or "").strip()
        if not script:
            raise HTTPException(status_code=400, detail="Script is empty.")
        language = (request.language or "ko").lower()
        base_name = sanitize_output_name(request.filename or "script_audio")
        output_path = OUTPUT_DIR / f"{base_name}_{language}_{uuid.uuid4().hex[:8]}.mp3"
        metadata = await synthesize_script_audio(
            script,
            language,
            output_path,
            voice_name=request.voice_name,
            style_prompt=request.style_prompt,
            tts_provider=request.tts_provider,
        )
        artifact = db.create_artifact(None, "audio", language, str(output_path), output_path.name, metadata)
        return artifact_api_response(artifact)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Script audio generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tts/voices")
async def get_tts_voices():
    voices = get_active_tts_voices()
    providers = {
        "google_cloud": {
            "label": "Google Cloud",
            "voices": CLOUD_TTS_VOICES,
            "defaults": defaults_for_provider("google_cloud"),
            "languages": ["ko", "en"],
        },
        "gemini": {
            "label": "Gemini",
            "voices": [
                {**voice, "languages": ["ko", "en"]}
                for voice in TTS_VOICES
            ],
            "defaults": defaults_for_provider("gemini"),
            "languages": ["ko", "en"],
        },
    }
    return {
        "success": True,
        "provider": active_tts_provider(),
        "voices": voices,
        "defaults": {"ko": default_voice_for_language("ko"), "en": default_voice_for_language("en")},
        "providers": providers,
        "supports": {"single_speaker": True, "multi_speaker": False, "style_prompt": False},
        "runtime": {
            "cuda_available": torch.cuda.is_available(),
            "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "",
        },
    }


@app.get("/api/tts/voice-samples")
async def list_voice_samples():
    samples = []
    for provider, provider_voices in voice_sample_providers().items():
        samples.extend(voice_sample_status(provider, voice) for voice in provider_voices)
    return {
        "success": True,
        "sample_text": VOICE_SAMPLE_TEXT,
        "samples": samples,
    }


@app.post("/api/tts/voice-samples/generate")
async def generate_all_voice_samples(request: VoiceSampleGenerateRequest):
    generated = []
    errors = []
    for provider, provider_voices in voice_sample_providers().items():
        for voice in provider_voices:
            try:
                generated.append(await generate_voice_sample(provider, voice["name"], force=request.force))
            except Exception as exc:
                errors.append({
                    "provider": provider,
                    "voice_name": voice["name"],
                    "error": str(exc),
                })
    return {
        "success": len(errors) == 0,
        "sample_text": VOICE_SAMPLE_TEXT,
        "samples": generated,
        "errors": errors,
    }


@app.get("/api/tts/voice-samples/{provider}/{voice_name}")
async def preview_voice_sample(provider: str, voice_name: str):
    provider, _ = validate_voice_sample(provider, voice_name)
    path = voice_sample_path(provider, voice_name)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Voice sample has not been generated yet.")
    return FileResponse(path, media_type="audio/mpeg", filename=path.name)


@app.get("/api/ai-usage")
async def get_ai_usage(start_at: Optional[str] = None, end_at: Optional[str] = None):
    return {
        "success": True,
        "summary": db.summarize_ai_usage(start_at=start_at, end_at=end_at),
        "events": db.list_ai_usage_events(limit=100, start_at=start_at, end_at=end_at),
        "range": {
            "start_at": start_at or "",
            "end_at": end_at or "",
        },
        "currency": "USD",
        "estimated": True,
        "pricing": ai_usage.pricing_config(),
    }


@app.get("/api/files/{file_id}/media")
async def get_file_media(file_id: str):
    file = db.get_file_by_id(file_id)
    if not file or not file.get("media_path"):
        raise HTTPException(status_code=404, detail="Media not found.")
    path = Path(file["media_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="Media file is missing.")
    return FileResponse(path, media_type=media_type_for_path(path), filename=file.get("filename") or path.name)


@app.get("/api/files/{file_id}/thumbnail")
async def get_file_thumbnail(file_id: str):
    file = db.get_file_by_id(file_id)
    if not file or not file.get("thumbnail_path"):
        raise HTTPException(status_code=404, detail="Thumbnail not found.")
    path = Path(file["thumbnail_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail file is missing.")
    return FileResponse(path, media_type="image/jpeg")


@app.get("/api/jobs")
async def get_jobs():
    return {"success": True, "jobs": db.get_jobs()}


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    job = db.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return {"success": True, "job": job}


async def run_file_job(job_id: str, file_id: str, job_type: str, metadata: Dict):
    async def job_progress(progress: int, message: str) -> None:
        db.update_job(job_id, status="running", progress=progress, message=message)

    usage_token = ai_usage.AI_USAGE_CONTEXT.set({"file_id": file_id, "job_id": job_id})
    db.update_job(job_id, status="running", progress=5, message="작업 시작")
    try:
        file = db.get_file_by_id(file_id)
        if not file:
            raise HTTPException(status_code=404, detail="File not found.")

        result_artifact_id = None
        if job_type == "auto_pipeline":
            language = (metadata.get("language") or "en").lower()
            final_output = metadata.get("final_output") or "captioned_dub_video"
            if final_output not in {"audio", "subtitle_video", "dub_video", "captioned_dub_video"}:
                final_output = "captioned_dub_video"

            if metadata.get("generate_corrected", True):
                db.update_job(job_id, progress=10, message="자동 제작: 한국어 SRT 보정 시작")
                corrected_srt_text = await correct_korean_srt(file.get("srt_text") or "")
                db.update_file_fields(file_id, corrected_srt_text=corrected_srt_text)
                file = db.get_file_by_id(file_id)
                db.update_job(job_id, progress=28, message="자동 제작: 보정 SRT 저장 완료")

            if language == "en" and metadata.get("generate_english", True):
                db.update_job(job_id, progress=32, message="자동 제작: English SRT 생성 시작")
                english_srt_text = await translate_srt_to_english(file.get("corrected_srt_text") or file.get("srt_text") or "")
                db.update_english_srt(file_id, english_srt_text)
                file = db.get_file_by_id(file_id)
                db.update_job(job_id, progress=48, message="자동 제작: English SRT 저장 완료")

            srt_source = metadata.get("srt_source") or ("english" if language == "en" else "corrected")
            db.update_job(job_id, progress=50, message="자동 제작: MP3 생성 시작")
            audio_artifact = await create_audio_artifact_for_file(
                file,
                language,
                voice_name=metadata.get("voice_name"),
                style_prompt=metadata.get("style_prompt"),
                srt_source=srt_source,
                tts_provider=metadata.get("tts_provider"),
                progress_callback=job_progress,
                progress_start=52,
                progress_end=72,
            )
            result_artifact_id = audio_artifact["id"]

            if final_output == "audio":
                db.update_job(job_id, status="completed", progress=100, message="자동 제작 완료: MP3 생성 완료", result_artifact_id=result_artifact_id)
                return

            file = db.get_file_by_id(file_id)
            if final_output == "subtitle_video":
                db.update_job(job_id, progress=74, message="자동 제작: 자막 영상 생성 시작")
                artifact = await create_subtitle_video_artifact_for_file(
                    file,
                    language,
                    srt_source=srt_source,
                    subtitle_style=SubtitleStyleRequest(**metadata["subtitle_style"]) if metadata.get("subtitle_style") else None,
                    progress_callback=job_progress,
                )
            elif final_output == "dub_video":
                db.update_job(job_id, progress=74, message="자동 제작: 더빙 영상 생성 시작")
                artifact = await create_video_artifact_for_file(
                    file,
                    language,
                    srt_source=srt_source,
                    audio_artifact_id=audio_artifact["id"],
                    require_existing_audio=True,
                    progress_callback=job_progress,
                    progress_start=74,
                    progress_end=96,
                )
            else:
                db.update_job(job_id, progress=74, message="자동 제작: 자막+더빙 영상 생성 시작")
                artifact = await create_captioned_dub_video_artifact_for_file(
                    file,
                    language,
                    srt_source=srt_source,
                    subtitle_style=SubtitleStyleRequest(**metadata["subtitle_style"]) if metadata.get("subtitle_style") else None,
                    audio_artifact_id=audio_artifact["id"],
                    require_existing_audio=True,
                    progress_callback=job_progress,
                    progress_start=74,
                    progress_end=96,
                )
            result_artifact_id = artifact["id"]
            db.update_job(job_id, status="completed", progress=100, message="자동 제작 완료", result_artifact_id=result_artifact_id)
            return

        if job_type == "correct_ko":
            db.update_job(job_id, progress=15, message="한국어 SRT 구조와 타임코드 분석 중")
            db.update_job(job_id, progress=35, message="Gemini로 한국어 SRT 보정 요청 중")
            corrected_srt_text = await correct_korean_srt(file.get("srt_text") or "")
            db.update_job(job_id, progress=82, message="보정 결과 수신 완료")
            db.update_job(job_id, progress=90, message="보정 SRT 저장 중")
            db.update_file_fields(file_id, corrected_srt_text=corrected_srt_text)
            db.update_job(job_id, status="completed", progress=100, message="한국어 SRT 보정 완료")
            return

        if job_type == "translate_en":
            db.update_job(job_id, progress=15, message="번역할 SRT 구조와 타임코드 준비 중")
            db.update_job(job_id, progress=35, message="Gemini로 영어 SRT 생성 요청 중")
            english_srt_text = await translate_srt_to_english(file.get("corrected_srt_text") or file.get("srt_text") or "")
            db.update_job(job_id, progress=82, message="English SRT 결과 수신 완료")
            db.update_job(job_id, progress=90, message="English SRT 저장 중")
            db.update_english_srt(file_id, english_srt_text)
            db.update_job(job_id, status="completed", progress=100, message="영어 SRT 생성 완료")
            return

        if job_type == "audio":
            db.update_job(job_id, progress=10, message="SRT 타임라인 분석 중")
            artifact = await create_audio_artifact_for_file(
                file,
                metadata.get("language", "ko"),
                voice_name=metadata.get("voice_name"),
                style_prompt=metadata.get("style_prompt"),
                srt_source=metadata.get("srt_source"),
                tts_provider=metadata.get("tts_provider"),
                progress_callback=job_progress,
                progress_start=20,
                progress_end=90,
            )
            result_artifact_id = artifact["id"]
            db.update_job(job_id, status="completed", progress=100, message="MP3 생성 완료", result_artifact_id=result_artifact_id)
            return

        if job_type == "dub_video":
            db.update_job(job_id, progress=10, message="더빙 영상 생성 준비 중")
            artifact = await create_video_artifact_for_file(
                file,
                metadata.get("language", "ko"),
                voice_name=metadata.get("voice_name"),
                style_prompt=metadata.get("style_prompt"),
                srt_source=metadata.get("srt_source"),
                tts_provider=metadata.get("tts_provider"),
                audio_artifact_id=metadata.get("audio_artifact_id"),
                require_existing_audio=True,
                progress_callback=job_progress,
                progress_start=18,
                progress_end=92,
            )
            result_artifact_id = artifact["id"]
            db.update_job(job_id, status="completed", progress=100, message="더빙 영상 생성 완료", result_artifact_id=result_artifact_id)
            return

        if job_type == "subtitle_video":
            db.update_job(job_id, progress=15, message="자막 스타일과 SRT 준비 중")
            artifact = await create_subtitle_video_artifact_for_file(
                file,
                metadata.get("language", "ko"),
                srt_source=metadata.get("srt_source"),
                subtitle_style=SubtitleStyleRequest(**metadata["subtitle_style"]) if metadata.get("subtitle_style") else None,
                progress_callback=job_progress,
            )
            result_artifact_id = artifact["id"]
            db.update_job(job_id, status="completed", progress=100, message="자막 영상 생성 완료", result_artifact_id=result_artifact_id)
            return

        if job_type == "captioned_dub_video":
            db.update_job(job_id, progress=8, message="자막+더빙 영상 생성 준비 중")
            artifact = await create_captioned_dub_video_artifact_for_file(
                file,
                metadata.get("language", "ko"),
                voice_name=metadata.get("voice_name"),
                style_prompt=metadata.get("style_prompt"),
                srt_source=metadata.get("srt_source"),
                subtitle_style=SubtitleStyleRequest(**metadata["subtitle_style"]) if metadata.get("subtitle_style") else None,
                tts_provider=metadata.get("tts_provider"),
                audio_artifact_id=metadata.get("audio_artifact_id"),
                require_existing_audio=True,
                progress_callback=job_progress,
            )
            result_artifact_id = artifact["id"]
            db.update_job(job_id, status="completed", progress=100, message="자막+더빙 영상 생성 완료", result_artifact_id=result_artifact_id)
            return

        raise HTTPException(status_code=400, detail="Unsupported job type.")
    except Exception as e:
        detail = getattr(e, "detail", str(e))
        db.update_job(job_id, status="failed", progress=0, message="작업 실패", error=str(detail))
    finally:
        ai_usage.AI_USAGE_CONTEXT.reset(usage_token)


@app.post("/api/files/{file_id}/jobs/{job_type}")
async def start_file_job(file_id: str, job_type: str, request: JobRequest, background_tasks: BackgroundTasks):
    allowed = {"correct_ko", "translate_en", "audio", "dub_video", "subtitle_video", "captioned_dub_video", "auto_pipeline"}
    if job_type not in allowed:
        raise HTTPException(status_code=400, detail="Unsupported job type.")
    file = db.get_file_by_id(file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found.")
    metadata = request.model_dump()
    if file.get("english_srt_text") and not (file.get("srt_text") or file.get("corrected_srt_text")):
        metadata["language"] = "en"
        if not metadata.get("srt_source") or metadata.get("srt_source") in {"original", "corrected"}:
            metadata["srt_source"] = "english"
    if job_type in {"audio", "auto_pipeline"}:
        language = (metadata.get("language") or "ko").lower()
        provider, voice = normalize_tts_selection(language, metadata.get("tts_provider"), metadata.get("voice_name"))
        metadata["tts_provider"] = provider
        metadata["voice_name"] = voice
    if job_type in {"dub_video", "captioned_dub_video"} and not metadata.get("audio_artifact_id"):
        raise HTTPException(status_code=400, detail="더빙 영상을 만들려면 먼저 생성된 MP3를 선택하세요.")
    if job_type in {"dub_video", "captioned_dub_video"} and metadata.get("audio_artifact_id"):
        audio_artifact = get_selected_audio_artifact(file, metadata.get("audio_artifact_id"), metadata.get("language", "ko"))
        audio_metadata = audio_artifact.get("metadata") or {}
        metadata["tts_provider"] = audio_metadata.get("tts_provider") or provider_for_voice_name(audio_metadata.get("voice_name")) or metadata.get("tts_provider")
        metadata["voice_name"] = audio_metadata.get("voice_name") or metadata.get("voice_name")
    job = db.create_job(file_id, job_type, metadata)
    background_tasks.add_task(run_file_job, job["id"], file_id, job_type, metadata)
    return {"success": True, "job": job}


@app.post("/api/script/jobs")
async def create_script_job(request: ScriptJobRequest):
    script = (request.script or "").strip()
    if not script:
        raise HTTPException(status_code=400, detail="Script is empty.")
    if not parse_srt(script):
        raise HTTPException(status_code=400, detail="SRT-only jobs require valid SRT timecodes.")
    language = (request.language or "ko").lower()
    filename = request.filename.strip() if request.filename else "srt_project.srt"
    if not Path(filename).suffix:
        filename = f"{filename}.srt"
    file = db.create_file_record(
        filename=filename,
        file_type="srt_project",
        original_text=script,
        srt_text=script if language != "en" else "",
        english_srt_text=script if language == "en" else "",
    )
    job = db.create_job(file["id"], "srt_project", {"language": language})
    db.update_job(job["id"], status="completed", progress=100, message="SRT 새 작업 생성 완료")
    return {"success": True, "file": prepare_file_for_api(db.get_file_by_id(file["id"]), include_original=True)}


SRT_ARTIFACT_SOURCES = {
    "original": {"field": "srt_text", "language": "ko", "label": "한국어 SRT", "suffix": "ko"},
    "corrected": {"field": "corrected_srt_text", "language": "ko", "label": "보정 SRT", "suffix": "corrected_ko"},
    "english": {"field": "english_srt_text", "language": "en", "label": "English SRT", "suffix": "en"},
}


def srt_artifact_id(file_id: str, source: str) -> str:
    return f"srt:{file_id}:{source}"


def parse_srt_artifact_id(artifact_id: str) -> Optional[Tuple[str, str]]:
    parts = (artifact_id or "").split(":")
    if len(parts) == 3 and parts[0] == "srt" and parts[2] in SRT_ARTIFACT_SOURCES:
        return parts[1], parts[2]
    return None


def srt_filename_for_file(file: Dict, source: str) -> str:
    source_info = SRT_ARTIFACT_SOURCES[source]
    base_name = sanitize_output_name(Path(file.get("filename") or "subtitle").stem)
    return f"{base_name}_{source_info['suffix']}.srt"


def srt_virtual_artifact(file: Dict, source: str, text: str) -> Dict:
    source_info = SRT_ARTIFACT_SOURCES[source]
    artifact_id = srt_artifact_id(file["id"], source)
    return {
        "id": artifact_id,
        "file_id": file["id"],
        "kind": "srt",
        "language": source_info["language"],
        "path": "",
        "filename": srt_filename_for_file(file, source),
        "created_at": file.get("last_updated") or file.get("uploaded_at"),
        "metadata": {
            "srt_source": source,
            "srt_label": source_info["label"],
            "cue_count": len(parse_srt(text)),
        },
        "source_filename": file.get("filename"),
        "exists": True,
        "download_url": f"/api/artifacts/{artifact_id}/download",
        "preview_url": f"/api/artifacts/{artifact_id}/preview",
    }


def get_srt_virtual_artifact(artifact_id: str) -> Optional[Tuple[Dict, str, str]]:
    parsed = parse_srt_artifact_id(artifact_id)
    if not parsed:
        return None
    file_id, source = parsed
    file = db.get_file_by_id(file_id)
    if not file:
        return None
    source_info = SRT_ARTIFACT_SOURCES[source]
    text = file.get(source_info["field"]) or ""
    if not text.strip():
        return None
    return srt_virtual_artifact(file, source, text), text, source


def clear_srt_virtual_artifact(artifact_id: str) -> bool:
    parsed = parse_srt_artifact_id(artifact_id)
    if not parsed:
        return False
    file_id, source = parsed
    source_info = SRT_ARTIFACT_SOURCES[source]
    return db.update_file_fields(file_id, **{source_info["field"]: ""})


@app.get("/api/artifacts")
async def list_artifacts():
    artifacts = []
    for artifact in db.get_all_artifacts():
        path = Path(artifact.get("path") or "")
        if not path.is_absolute():
            path = Path.cwd() / path
        artifact["exists"] = path.exists()
        artifact["download_url"] = f"/api/artifacts/{artifact['id']}/download"
        artifact["preview_url"] = f"/api/artifacts/{artifact['id']}/preview"
        artifacts.append(artifact)
    for file in db.get_all_files():
        for source, source_info in SRT_ARTIFACT_SOURCES.items():
            text = file.get(source_info["field"]) or ""
            if text.strip():
                artifacts.append(srt_virtual_artifact(file, source, text))
    artifacts.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return {"success": True, "artifacts": artifacts}


@app.get("/api/artifacts/{artifact_id}/download")
async def download_artifact(artifact_id: str):
    srt_artifact = get_srt_virtual_artifact(artifact_id)
    if srt_artifact:
        artifact, text, _ = srt_artifact
        headers = {"Content-Disposition": f'attachment; filename="{artifact["filename"]}"'}
        return StreamingResponse(io.BytesIO(text.encode("utf-8")), media_type="text/plain; charset=utf-8", headers=headers)
    artifact = db.get_artifact_by_id(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found.")
    path = Path(artifact.get("path") or "")
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact file is missing.")
    return FileResponse(path, filename=artifact.get("filename") or path.name)


@app.get("/api/artifacts/{artifact_id}/preview")
async def preview_artifact(artifact_id: str):
    srt_artifact = get_srt_virtual_artifact(artifact_id)
    if srt_artifact:
        _, text, _ = srt_artifact
        return StreamingResponse(io.BytesIO(text.encode("utf-8")), media_type="text/plain; charset=utf-8")
    artifact = db.get_artifact_by_id(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found.")
    path = Path(artifact.get("path") or "")
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact file is missing.")
    return FileResponse(path, media_type=media_type_for_path(path))


@app.post("/api/artifacts/batch-download")
async def batch_download_artifacts(request: ArtifactBatchRequest):
    artifact_ids = [artifact_id for artifact_id in request.artifact_ids if artifact_id]
    if not artifact_ids:
        raise HTTPException(status_code=400, detail="No artifacts selected.")

    zip_buffer = io.BytesIO()
    added_names = set()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for artifact_id in artifact_ids:
            srt_artifact = get_srt_virtual_artifact(artifact_id)
            if srt_artifact:
                artifact, text, _ = srt_artifact
                filename = sanitize_output_name(artifact["filename"])
                stem = Path(filename).stem
                suffix = Path(filename).suffix or ".srt"
                archive_name = filename
                counter = 2
                while archive_name in added_names:
                    archive_name = f"{stem}_{counter}{suffix}"
                    counter += 1
                added_names.add(archive_name)
                zip_file.writestr(archive_name, text)
                continue
            artifact = db.get_artifact_by_id(artifact_id)
            if not artifact:
                continue
            path = Path(artifact.get("path") or "")
            if not path.exists():
                continue
            filename = sanitize_output_name(artifact.get("filename") or path.name)
            stem = Path(filename).stem
            suffix = Path(filename).suffix
            archive_name = filename
            counter = 2
            while archive_name in added_names:
                archive_name = f"{stem}_{counter}{suffix}"
                counter += 1
            added_names.add(archive_name)
            zip_file.write(path, archive_name)

    if not added_names:
        raise HTTPException(status_code=404, detail="Selected artifact files are missing.")

    zip_buffer.seek(0)
    headers = {"Content-Disposition": 'attachment; filename="selected_artifacts.zip"'}
    return StreamingResponse(zip_buffer, media_type="application/zip", headers=headers)


@app.delete("/api/artifacts/{artifact_id}")
async def delete_artifact_api(artifact_id: str):
    if parse_srt_artifact_id(artifact_id):
        if not clear_srt_virtual_artifact(artifact_id):
            raise HTTPException(status_code=404, detail="SRT artifact not found.")
        return {"success": True}
    artifact = db.get_artifact_by_id(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found.")
    path = Path(artifact.get("path") or "")
    db.delete_artifact(artifact_id)
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass
    return {"success": True}


@app.post("/api/artifacts/batch-delete")
async def batch_delete_artifacts(request: ArtifactBatchRequest):
    deleted = 0
    for artifact_id in request.artifact_ids:
        if parse_srt_artifact_id(artifact_id):
            if clear_srt_virtual_artifact(artifact_id):
                deleted += 1
            continue
        artifact = db.get_artifact_by_id(artifact_id)
        if not artifact:
            continue
        path = Path(artifact.get("path") or "")
        if db.delete_artifact(artifact_id):
            deleted += 1
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass
    return {"success": True, "deleted": deleted}


@app.delete("/api/files/{file_id}/summary/{summary_type}")
async def delete_summary_api(file_id: str, summary_type: str):
    """요약 삭제"""
    try:
        success = db.delete_summary(file_id, summary_type)
        if not success:
            raise HTTPException(status_code=404, detail="요약을 찾을 수 없습니다.")
        return {"success": True, "message": "요약이 삭제되었습니다."}
    except HTTPException:
        raise
    except Exception as e:
        print(f"요약 삭제 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/files/{file_id}")
async def delete_file_api(file_id: str):
    """파일 삭제"""
    try:
        success = db.delete_file(file_id)
        if not success:
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
        return {"success": True, "message": "파일이 삭제되었습니다."}
    except HTTPException:
        raise
    except Exception as e:
        print(f"파일 삭제 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/files/{file_id}/summarize")
async def generate_summary(file_id: str, summary_type: str):
    """파일 요약 생성"""
    try:
        # 파일 조회
        file = db.get_file_by_id(file_id)
        if not file:
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
        
        # 이미 해당 타입의 요약이 있는지 확인
        if summary_type in file.get("summaries", {}):
            return {
                "success": True,
                "summary": file["summaries"][summary_type],
                "cached": True
            }
        
        # 요약 생성
        original_text = file.get("original_text", "")
        if not original_text:
            raise HTTPException(status_code=400, detail="원본 텍스트가 없습니다.")
        
        summary = await summarize_with_gemini(original_text, summary_type)
        
        # DB에 저장
        db.update_summary(file_id, summary_type, summary)
        
        return {
            "success": True,
            "summary": summary,
            "cached": False
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"요약 생성 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/search")
async def search_files_api(q: str):
    """파일 검색"""
    try:
        results = db.search_files(q)
        for file in results:
            prepare_file_for_api(file, include_original=False)
        
        return {"success": True, "results": results}
    except Exception as e:
        print(f"검색 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ API 키 설정 ============

@app.post("/api/set-api-key")
async def set_api_key(request: ApiKeyRequest):
    """Gemini API 키 설정 및 검증"""
    try:
        api_key = request.api_key
        
        if not api_key or len(api_key) < 10:
            return {"success": False, "message": "유효하지 않은 API 키입니다."}
        
        success = set_gemini_api_key(api_key)
        
        if success:
            persist_gemini_api_key(api_key)
            return {"success": True, "message": "API 키가 성공적으로 설정되었고 .env에 저장되었습니다!"}
        else:
            return {"success": False, "message": "API 키 검증에 실패했습니다. 올바른 키인지 확인해주세요."}
    except Exception as e:
        print(f"API 키 설정 오류: {e}")
        return {"success": False, "message": f"오류가 발생했습니다: {str(e)}"}


@app.get("/api/check-api-key")
async def check_api_key():
    """API 키 설정 상태 확인"""
    project = get_google_cloud_project()
    is_vertex = GEMINI_PROVIDER in {"vertex_ai", "vertex", "google_cloud"}
    return {
        "success": True,
        "has_key": gemini_text_client is not None,
        "key_preview": f"Vertex AI ({project})" if is_vertex and project else (f"{gemini_api_key[:10]}..." if gemini_api_key else None),
        "provider": "vertex_ai" if is_vertex else "api_key",
        "project": project,
        "location": VERTEX_AI_LOCATION,
        "model": GEMINI_TEXT_MODEL,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)






