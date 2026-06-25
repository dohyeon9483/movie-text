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


initialize_gemini_from_env()

# 디렉토리 생성
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
MEDIA_DIR = Path("media")
MEDIA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)
VOICE_SAMPLE_DIR = OUTPUT_DIR / "voice_samples"
VOICE_SAMPLE_DIR.mkdir(exist_ok=True)
ASSET_DIR = Path("assets")
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

VOICE_SAMPLE_TEXT = "안녕하세요? 반갑습니다. 저는 AI 말하기 모델입니다!\nHello? Nice to meet you. I'm an AI speech model!"
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


def build_ass_subtitles(srt_text: str, style: Optional[SubtitleStyleRequest] = None) -> Tuple[str, Dict]:
    cues = parse_srt(srt_text)
    normalized = normalize_subtitle_style(style)
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
        "PlayResX: 1920",
        "PlayResY: 1080",
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
        ass_text, normalized_style = build_ass_subtitles(srt_text, subtitle_style)
        temp_ass_path.write_text(ass_text, encoding="utf-8")
        subtitle_filter = f"subtitles={temp_ass_path.name}"
        command = [
            "ffmpeg", "-y",
            "-i", str(source_video_path.resolve()),
            "-vf", subtitle_filter,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "23",
            "-c:a", "copy",
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
        raise HTTPException(status_code=400, detail="At least one slide image is required.")
    slide_payloads: List[Tuple[str, bytes]] = []
    seen_names = set()
    for slide in slides:
        filename = safe_upload_filename(slide.filename or "")
        if Path(filename).suffix.lower() not in LECTURE_SLIDE_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"Unsupported slide image: {filename}")
        if filename in seen_names:
            raise HTTPException(status_code=400, detail=f"Duplicate slide filename: {filename}")
        seen_names.add(filename)
        slide_payloads.append((filename, await slide.read()))
    timeline_content = await timeline_file.read()
    validation = parse_lecture_timeline_xlsx(timeline_content, [name for name, _ in slide_payloads], "")
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
    for filename, content in slide_payloads:
        path = project_dir / filename
        path.write_bytes(content)
        slide_manifest[filename] = str(path)
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






