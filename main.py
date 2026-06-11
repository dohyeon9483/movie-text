import os
import uuid
import json
import asyncio
import re
import base64
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Optional, List, Tuple, Dict
from dotenv import load_dotenv, set_key
from pydantic import BaseModel

import whisper
import torch
import numpy as np
import database as db
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
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


def format_srt_time(seconds: float) -> str:
    """Converts seconds to SRT timecode format: HH:MM:SS,mmm."""
    if seconds is None:
        seconds = 0
    seconds = max(float(seconds), 0.0)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    whole_seconds = int(seconds % 60)
    milliseconds = int(round((seconds - int(seconds)) * 1000))
    if milliseconds == 1000:
        whole_seconds += 1
        milliseconds = 0
    if whole_seconds == 60:
        minutes += 1
        whole_seconds = 0
    if minutes == 60:
        hours += 1
        minutes = 0
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d},{milliseconds:03d}"


def format_srt_entry(index: int, start_seconds: float, end_seconds: float, text: str) -> str:
    """Builds one SRT subtitle block."""
    if end_seconds <= start_seconds:
        end_seconds = start_seconds + 2.0
    return (
        f"{index}\n"
        f"{format_srt_time(start_seconds)} --> {format_srt_time(end_seconds)}\n"
        f"{text.strip()}"
    )
# Pydantic 모델
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
    style_prompt: Optional[str] = None
    srt_source: Optional[str] = None
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
    style_prompt: Optional[str] = None

class ScriptJobRequest(BaseModel):
    filename: str
    script: str
    language: str = "ko"

class JobRequest(BaseModel):
    language: str = "ko"
    voice_name: Optional[str] = None
    style_prompt: Optional[str] = None
    srt_source: Optional[str] = None
    subtitle_style: Optional[SubtitleStyleRequest] = None

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
GEMINI_TTS_MODEL = os.getenv("GEMINI_TTS_MODEL", "gemini-3.1-flash-tts-preview")
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


def generate_gemini_text(prompt: str) -> str:
    response = gemini_text_client.models.generate_content(
        model=GEMINI_TEXT_MODEL,
        contents=prompt,
    )
    return getattr(response, "text", "") or ""


initialize_gemini_from_env()

# 디렉토리 생성
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
MEDIA_DIR = Path("media")
MEDIA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)
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
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    return text.strip()


def should_skip_segment(segment: dict, text: str) -> bool:
    """Whisper가 낮은 확신도로 만든 환각 가능성이 큰 세그먼트를 제외합니다."""
    compact_text = re.sub(r"\s+", "", text)
    if not compact_text:
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
    async with transcription_semaphore:
        try:
            # pydub을 사용하여 오디오 파일 로드 (비동기)
            audio = await asyncio.to_thread(AudioSegment.from_file, audio_path)
            chunks = build_transcription_ranges(audio)
            if not chunks:
                yield {"type": "result", "text": ""}
                return
            
            full_text_with_timestamps = [] # 타임스탬프가 포함된 전체 텍스트를 저장할 리스트
            srt_entries = []
            skipped_segments = 0
            decode_options = {}
            if WHISPER_BEAM_SIZE > 1:
                decode_options["beam_size"] = WHISPER_BEAM_SIZE
            
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
        return await asyncio.to_thread(generate_gemini_text, prompt)
        
    except Exception as e:
        print(f"Gemini 요약 오류: {e}")
        return f"요약 생성 중 오류가 발생했습니다: {str(e)}"


SRT_TIME_RE = re.compile(
    r"(?P<start>\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(?P<end>\d{2}:\d{2}:\d{2},\d{3})"
)

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


def active_tts_provider() -> str:
    return "gemini" if TTS_PROVIDER in {"gemini", "gemini_api"} else "google_cloud"


def get_active_tts_voices() -> List[Dict]:
    return TTS_VOICES if active_tts_provider() == "gemini" else CLOUD_TTS_VOICES


def default_voice_for_language(language: str) -> str:
    language = (language or "ko").lower()
    voices = get_active_tts_voices()
    default_key = "default_ko" if language == "ko" else "default_en"
    for voice in voices:
        if voice.get(default_key):
            return voice["name"]
    return voices[0]["name"]


def parse_srt_timecode(value: str) -> float:
    hours, minutes, rest = value.split(":")
    seconds, milliseconds = rest.split(",")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000


def parse_srt(srt_text: str) -> List[Dict]:
    blocks = re.split(r"\n\s*\n", (srt_text or "").replace("\r\n", "\n").strip())
    cues = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 3:
            continue
        time_match = SRT_TIME_RE.search(lines[1])
        if not time_match:
            continue
        try:
            index = int(lines[0])
        except ValueError:
            index = len(cues) + 1
        cues.append({
            "index": index,
            "start_code": time_match.group("start"),
            "end_code": time_match.group("end"),
            "start": parse_srt_timecode(time_match.group("start")),
            "end": parse_srt_timecode(time_match.group("end")),
            "text": "\n".join(lines[2:]).strip(),
        })
    return cues


def build_srt(cues: List[Dict], texts: List[str]) -> str:
    entries = []
    for cue, text in zip(cues, texts):
        entries.append(f"{cue['index']}\n{cue['start_code']} --> {cue['end_code']}\n{text.strip()}")
    return "\n\n".join(entries)


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
    return file.get("corrected_srt_text") or file.get("srt_text") or ""


def normalize_voice_name(language: str, voice_name: Optional[str]) -> str:
    default_voice = default_voice_for_language(language)
    if not voice_name:
        return default_voice
    valid_voice_names = {voice["name"] for voice in get_active_tts_voices()}
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


def require_tts_ready():
    if active_tts_provider() == "google_cloud":
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
    raw_text = (await asyncio.to_thread(generate_gemini_text, prompt)).strip()
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


async def generate_tts_wav(text: str, language: str, wav_path: Path, voice_name: Optional[str] = None, style_prompt: Optional[str] = None) -> None:
    require_tts_ready()
    language = (language or "ko").lower()
    voice_name = normalize_voice_name(language, voice_name)
    if active_tts_provider() == "google_cloud":
        await generate_cloud_tts_wav(text, language, wav_path, voice_name)
        return
    await generate_gemini_tts_wav(text, language, wav_path, voice_name, style_prompt=style_prompt)


async def generate_gemini_tts_wav(text: str, language: str, wav_path: Path, voice_name: str, style_prompt: Optional[str] = None) -> None:
    prompt_language = "Korean" if language == "ko" else "English"
    style = (style_prompt or "Read clearly at a steady narration pace.").strip()
    prompt = f"{style}\nRead the following {prompt_language} text exactly:\n{text.strip()}"
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


def cloud_language_code(language: str) -> str:
    return "ko-KR" if (language or "ko").lower() == "ko" else "en-US"


async def generate_cloud_tts_wav(text: str, language: str, wav_path: Path, voice_name: str) -> None:
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


async def synthesize_audio_from_srt(srt_text: str, language: str, output_path: Path, voice_name: Optional[str] = None, style_prompt: Optional[str] = None) -> Dict:
    cues = parse_srt(srt_text)
    if not cues:
        raise HTTPException(status_code=400, detail="No valid SRT cues found.")
    total_duration_ms = int(max(cue["end"] for cue in cues) * 1000)
    timeline = AudioSegment.silent(duration=total_duration_ms).set_channels(2)
    temp_paths = []
    groups = tts_groups_for_mode(cues)
    try:
        for group in groups:
            wav_path = OUTPUT_DIR / f"{uuid.uuid4()}.wav"
            temp_paths.append(wav_path)
            await generate_tts_wav(text_for_tts_group(group), language, wav_path, voice_name=voice_name, style_prompt=style_prompt)
            with open(wav_path, "rb") as wav_file:
                segment = AudioSegment.from_file(wav_file, format="wav").set_channels(2)
            group_start_ms = int(group[0]["start"] * 1000)
            group_duration_ms = int((group[-1]["end"] - group[0]["start"]) * 1000)
            segment = fit_audio_to_duration(segment, group_duration_ms)
            timeline = timeline.overlay(segment, position=group_start_ms)
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
        "voice_name": normalize_voice_name(language, voice_name),
        "style_prompt": style_prompt or "",
    }


async def synthesize_audio_from_text(script: str, language: str, output_path: Path, voice_name: Optional[str] = None, style_prompt: Optional[str] = None) -> Dict:
    wav_path = OUTPUT_DIR / f"{uuid.uuid4()}.wav"
    try:
        await generate_tts_wav(script, language, wav_path, voice_name=voice_name, style_prompt=style_prompt)
        with open(wav_path, "rb") as wav_file:
            audio = AudioSegment.from_file(wav_file, format="wav")
        with open(output_path, "wb") as mp3_file:
            audio.export(mp3_file, format="mp3", bitrate="192k")
        return {
            "cue_count": 0,
            "duration_ms": len(audio),
            "voice_name": normalize_voice_name(language, voice_name),
            "style_prompt": style_prompt or "",
        }
    finally:
        try:
            wav_path.unlink()
        except OSError:
            pass


async def synthesize_script_audio(script: str, language: str, output_path: Path, voice_name: Optional[str] = None, style_prompt: Optional[str] = None) -> Dict:
    if parse_srt(script):
        return await synthesize_audio_from_srt(script, language, output_path, voice_name=voice_name, style_prompt=style_prompt)
    return await synthesize_audio_from_text(script, language, output_path, voice_name=voice_name, style_prompt=style_prompt)


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
    border_style = 3 if normalized["background_enabled"] else 1
    back_opacity = normalized["background_opacity"] if normalized["background_enabled"] else 0
    style_line = ",".join([
        "Default",
        normalized["font_family"],
        str(normalized["font_size"]),
        ass_color(normalized["text_color"], 100),
        ass_color(normalized["text_color"], 100),
        ass_color(normalized["outline_color"], 100),
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


async def create_subtitle_video_artifact_for_file(file: Dict, language: str, srt_source: Optional[str] = None, subtitle_style: Optional[SubtitleStyleRequest] = None) -> Dict:
    language = (language or "ko").lower()
    srt_text = get_srt_for_language(file, language, srt_source=srt_source)
    if not srt_text:
        raise HTTPException(status_code=400, detail=f"No {language} SRT is available.")

    cues = parse_srt(srt_text)
    duration_ms = int(max((cue["end"] for cue in cues), default=1.0) * 1000)
    base_name = sanitize_output_name(file.get("filename", "subtitle_video"))
    output_path = OUTPUT_DIR / f"{base_name}_{language}_subtitled_{uuid.uuid4().hex[:8]}.mp4"
    media_path = Path(file.get("media_path") or "")
    black_video_path = None
    try:
        if media_path.exists():
            source_video_path = media_path
            source_video = "original"
        else:
            black_video_path = OUTPUT_DIR / f"{base_name}_black_{uuid.uuid4().hex[:8]}.mp4"
            await asyncio.to_thread(create_black_video, duration_ms, black_video_path)
            source_video_path = black_video_path
            source_video = "black"
        normalized_style = await asyncio.to_thread(burn_subtitles_into_video, source_video_path, srt_text, output_path, subtitle_style)
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


async def create_audio_artifact_for_file(file: Dict, language: str, voice_name: Optional[str] = None, style_prompt: Optional[str] = None, srt_source: Optional[str] = None) -> Dict:
    language = (language or "ko").lower()
    srt_text = get_srt_for_language(file, language, srt_source=srt_source)
    if not srt_text:
        raise HTTPException(status_code=400, detail=f"No {language} SRT is available.")
    base_name = sanitize_output_name(file.get("filename", "audio"))
    output_path = OUTPUT_DIR / f"{base_name}_{language}_{uuid.uuid4().hex[:8]}.mp3"
    metadata = await synthesize_audio_from_srt(
        srt_text,
        language,
        output_path,
        voice_name=voice_name,
        style_prompt=style_prompt,
    )
    metadata["srt_source"] = srt_source or ("english" if language == "en" else ("corrected" if file.get("corrected_srt_text") else "original"))
    return db.create_artifact(file["id"], "audio", language, str(output_path), output_path.name, metadata)


def desired_srt_source(file: Dict, language: str, srt_source: Optional[str]) -> str:
    return srt_source or ("english" if language == "en" else ("corrected" if file.get("corrected_srt_text") else "original"))


def find_reusable_audio_artifact(file: Dict, language: str, voice_name: Optional[str], srt_source: Optional[str]) -> Optional[Dict]:
    language = (language or "ko").lower()
    expected_voice = normalize_voice_name(language, voice_name)
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
        artifact_voice = metadata.get("voice_name") or normalize_voice_name(language, None)
        artifact_srt_source = metadata.get("srt_source") or desired_srt_source(file, language, None)
        artifact_sync_mode = metadata.get("tts_sync_mode") or "grouped"
        if artifact_sync_mode != expected_sync_mode:
            continue
        if artifact_voice == expected_voice and artifact_srt_source == expected_srt_source:
            return artifact
        if fallback is None and artifact_srt_source == expected_srt_source:
            fallback = artifact
    return fallback


async def create_video_artifact_for_file(file: Dict, language: str, voice_name: Optional[str] = None, style_prompt: Optional[str] = None, srt_source: Optional[str] = None) -> Dict:
    language = (language or "ko").lower()
    srt_text = get_srt_for_language(file, language, srt_source=srt_source)
    if not srt_text:
        raise HTTPException(status_code=400, detail=f"No {language} SRT is available.")
    base_name = sanitize_output_name(file.get("filename", "video"))
    video_output_path = OUTPUT_DIR / f"{base_name}_{language}_dubbed_{uuid.uuid4().hex[:8]}.mp4"
    audio_artifact = find_reusable_audio_artifact(file, language, voice_name, srt_source)
    reused_audio = audio_artifact is not None
    if audio_artifact:
        audio_path = Path(audio_artifact["path"])
        metadata = dict(audio_artifact.get("metadata") or {})
    else:
        audio_artifact = await create_audio_artifact_for_file(
            file,
            language,
            voice_name=voice_name,
            style_prompt=style_prompt,
            srt_source=srt_source,
        )
        audio_path = Path(audio_artifact["path"])
        metadata = dict(audio_artifact.get("metadata") or {})
    media_path = Path(file.get("media_path") or "")
    black_video_path = None
    if media_path.exists():
        source_video_path = media_path
    else:
        black_video_path = OUTPUT_DIR / f"{base_name}_black_{uuid.uuid4().hex[:8]}.mp4"
        await asyncio.to_thread(create_black_video, metadata["duration_ms"], black_video_path)
        source_video_path = black_video_path
    await asyncio.to_thread(mux_video_with_audio, source_video_path, audio_path, video_output_path)
    if black_video_path:
        try:
            black_video_path.unlink()
        except OSError:
            pass
    metadata["srt_source"] = desired_srt_source(file, language, srt_source)
    metadata["source_video"] = "original" if media_path.exists() else "black"
    metadata["audio_artifact_id"] = audio_artifact["id"]
    metadata["reused_audio"] = reused_audio
    return db.create_artifact(file["id"], "video", language, str(video_output_path), video_output_path.name, metadata)


async def create_captioned_dub_video_artifact_for_file(
    file: Dict,
    language: str,
    voice_name: Optional[str] = None,
    style_prompt: Optional[str] = None,
    srt_source: Optional[str] = None,
    subtitle_style: Optional[SubtitleStyleRequest] = None,
) -> Dict:
    language = (language or "ko").lower()
    srt_text = get_srt_for_language(file, language, srt_source=srt_source)
    if not srt_text:
        raise HTTPException(status_code=400, detail=f"No {language} SRT is available.")

    base_name = sanitize_output_name(file.get("filename", "captioned_dub_video"))
    dubbed_artifact = await create_video_artifact_for_file(
        file,
        language,
        voice_name=voice_name,
        style_prompt=style_prompt,
        srt_source=srt_source,
    )
    output_path = OUTPUT_DIR / f"{base_name}_{language}_captioned_dub_{uuid.uuid4().hex[:8]}.mp4"
    normalized_style = await asyncio.to_thread(
        burn_subtitles_into_video,
        Path(dubbed_artifact["path"]),
        srt_text,
        output_path,
        subtitle_style,
    )

    metadata = dict(dubbed_artifact.get("metadata") or {})
    metadata["srt_source"] = desired_srt_source(file, language, srt_source)
    metadata["dubbed_video_artifact_id"] = dubbed_artifact["id"]
    metadata["variant"] = "captioned_dub"
    metadata["subtitle_style"] = normalized_style
    return db.create_artifact(file["id"], "captioned_dub_video", language, str(output_path), output_path.name, metadata)


def generate_video_thumbnail(video_path: Path, output_path: Path) -> bool:
    command = [
        "ffmpeg", "-y",
        "-ss", "00:00:01",
        "-i", str(video_path),
        "-frames:v", "1",
        "-vf", "scale=480:-1",
        str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    return result.returncode == 0 and output_path.exists()


def create_black_video(duration_ms: int, output_path: Path) -> None:
    duration = max(duration_ms / 1000, 1.0)
    command = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "color=c=black:s=1280x720:r=30",
        "-t", f"{duration:.3f}",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"black video generation failed: {result.stderr[-1000:]}")


async def correct_korean_srt(srt_text: str) -> str:
    require_gemini_ready()
    cues = parse_srt(srt_text)
    if not cues:
        raise HTTPException(status_code=400, detail="No valid Korean SRT cues found.")
    source_items = [{"index": cue["index"], "text": cue["text"]} for cue in cues]
    prompt = (
        "Correct Korean subtitle cue texts for typos, spacing, and obvious speech-to-text mistakes. "
        "Return JSON only as an array of objects with index and text. "
        "Do not translate. Do not add, remove, merge, split, or reorder items. "
        "Preserve the intended meaning and technical terms.\n\n"
        f"{json.dumps(source_items, ensure_ascii=False)}"
    )
    raw_text = (await asyncio.to_thread(generate_gemini_text, prompt)).strip()
    raw_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text, flags=re.IGNORECASE | re.DOTALL).strip()
    try:
        corrected_items = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f"Correction response was not valid JSON: {exc}")
    corrected_by_index = {
        int(item.get("index")): str(item.get("text", "")).strip()
        for item in corrected_items
        if isinstance(item, dict) and item.get("index") is not None
    }
    return build_srt(cues, [corrected_by_index.get(cue["index"], cue["text"]) for cue in cues])


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """메인 페이지를 반환합니다."""
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()


async def process_single_file(file: UploadFile, file_index: int, total_files: int):
    """단일 파일을 처리하고 진행 상황을 생성합니다."""
    file_prefix = f"[{file_index}/{total_files}] {file.filename}"
    
    # 파일 확장자 검증 및 타입 확인
    filename_lower = file.filename.lower()
    
    # 지원하는 확장자
    video_extensions = ('.mp4', '.mov', '.avi', '.mkv', '.webm')
    audio_extensions = ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma', '.opus', '.webm')
    text_extensions = ('.txt',)
    
    is_video = filename_lower.endswith(video_extensions)
    is_audio = filename_lower.endswith(audio_extensions)
    is_text = filename_lower.endswith(text_extensions)
    
    if not (is_video or is_audio or is_text):
        yield await send_progress(
            f"{file_prefix}: 지원하지 않는 파일 형식입니다. (지원: 영상/음성/텍스트)", 
            0, 
            "error"
        )
        return
    
    # 고유한 파일명 생성
    unique_id = str(uuid.uuid4())
    file_suffix = Path(file.filename).suffix or ".bin"
    video_path = MEDIA_DIR / f"{unique_id}{file_suffix}"
    audio_path = UPLOAD_DIR / f"{unique_id}.wav"
    keep_media = False
    
    try:
        # 1. 파일 업로드 중
        yield await send_progress(f"{file_prefix}: 업로드 중...", 5, "processing")
        content = await file.read()
        
        # 2. 파일 저장 중
        yield await send_progress(f"{file_prefix}: 파일 저장 중...", 15, "processing")
        with open(video_path, "wb") as buffer:
            buffer.write(content)
        print(f"비디오 파일 저장 완료: {video_path}")
        
        # 3. 파일 검증 중
        yield await send_progress(f"{file_prefix}: 파일 검증 중...", 25, "processing")
        await asyncio.sleep(0.3)  # 사용자가 진행 상황을 볼 수 있도록
        
        # TXT 파일인 경우 텍스트 직접 읽기
        if is_text:
            yield await send_progress(f"{file_prefix}: 텍스트 파일 읽는 중...", 30, "processing")
            try:
                text = content.decode('utf-8')
            except UnicodeDecodeError:
                # UTF-8 실패 시 다른 인코딩 시도
                try:
                    text = content.decode('cp949')
                except:
                    text = content.decode('latin-1')
            
            yield await send_progress(f"{file_prefix}: 텍스트 읽기 완료", 90, "processing")
            print(f"텍스트 파일 읽기 완료! 텍스트 길이: {len(text)}")
            
        # 음성 파일인 경우 Whisper용 WAV로 바로 전처리
        elif is_audio:
            keep_media = True
            yield await send_progress(f"{file_prefix}: 음성 파일 확인 완료", 30, "processing")

            yield await send_progress(f"{file_prefix}: 음성 전처리 중...", 40, "processing")
            try:
                await asyncio.to_thread(export_preprocessed_audio, str(video_path), str(audio_path))
            except Exception as e:
                print(f"음성 전처리 오류: {e}")
                yield await send_progress(f"{file_prefix}: 음성 전처리 실패", 0, "error")
                return
            
            yield await send_progress(f"{file_prefix}: 음성 파일 준비 완료", 55, "processing")
        else:
            keep_media = True
            # 영상 파일인 경우 오디오 추출
            # 4. 오디오 추출 준비
            yield await send_progress(f"{file_prefix}: 오디오 추출 준비 중...", 30, "processing")
            await asyncio.sleep(0.2)
            
            # 5. 오디오 추출 중
            yield await send_progress(f"{file_prefix}: 오디오 추출 중...", 35, "processing")
            print("오디오 추출 중...")
            if not await extract_audio_from_video_async(str(video_path), str(audio_path)):
                yield await send_progress(f"{file_prefix}: 오디오 추출 실패", 0, "error")
                return
            
            # 6. 오디오 추출 완료
            yield await send_progress(f"{file_prefix}: 오디오 추출 완료", 55, "processing")
            print("오디오 추출 완료!")
        
        srt_text = ""

        # 텍스트 파일이 아닌 경우만 음성 인식 수행
        if not is_text:
            # 7. 음성 인식 준비
            yield await send_progress(f"{file_prefix}: 음성 인식 엔진 준비 중...", 60, "processing")
            await asyncio.sleep(0.2)
            
            # 8. 음성 인식 중 (가장 시간이 오래 걸림)
            yield await send_progress(f"{file_prefix}: 음성 인식 시작 (대기 중일 수 있습니다)", 65, "processing")
            print(f"음성 인식 시작: {file.filename}")
            
            # 비동기로 음성 인식 실행 (세마포어 적용됨) - 무음 제외 구간 단위로 분할 처리
            text = None
            async for status in transcribe_audio_async_generator(str(audio_path), language="ko"):
                if status["type"] == "progress":
                    current = status["current"]
                    total = status["total"]
                    # 65% ~ 90% 사이를 진행률에 맞게 매핑
                    prog = 65 + int((current / total) * 25)
                    yield await send_progress(f"{file_prefix}: 음성 인식 중... ({current}/{total} 구간)", prog, "processing")
                elif status["type"] == "result":
                    text = status["text"]
                    srt_text = status.get("srt_text", "")
                elif status["type"] == "error":
                    yield await send_progress(f"{file_prefix}: 음성 인식 실패 - {status['error']}", 0, "error")
                    return
            
            if text is None:
                yield await send_progress(f"{file_prefix}: 음성 인식 실패", 0, "error")
                return
            
            # 9. 음성 인식 완료
            yield await send_progress(f"{file_prefix}: 음성 인식 완료", 90, "processing")
            print(f"음성 인식 완료! 텍스트 길이: {len(text)}")
        
        # 10. 데이터베이스에 저장
        yield await send_progress(f"{file_prefix}: 데이터베이스 저장 중...", 93, "processing")
        
        # 파일 타입 결정
        if file.filename.startswith("recording_"):
            file_type = "recording"
        elif is_text:
            file_type = "text"
        elif is_video:
            file_type = "video"
        else:
            file_type = "audio"

        thumbnail_path = ""
        if file_type == "video" and keep_media:
            candidate_thumbnail = THUMBNAIL_DIR / f"{unique_id}.jpg"
            if await asyncio.to_thread(generate_video_thumbnail, video_path, candidate_thumbnail):
                thumbnail_path = str(candidate_thumbnail)
        
        # DB에 저장
        file_record = db.create_file_record(
            filename=file.filename,
            file_type=file_type,
            original_text=text,
            srt_text=srt_text,
            media_path=str(video_path) if keep_media else "",
            thumbnail_path=thumbnail_path,
        )
        file_id = file_record["id"]
        
        # 11. 후처리 중
        yield await send_progress(f"{file_prefix}: 결과 정리 중...", 96, "processing")
        await asyncio.sleep(0.2)
        
        # 12. 완료
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
        yield f"data: {json.dumps(result)}\n\n"
        
    except Exception as e:
        print(f"오류 발생: {e}")
        error_msg = f"{file_prefix}: 처리 중 오류 발생 - {str(e)}"
        yield await send_progress(error_msg, 0, "error")
    
    finally:
        # 임시 파일 정리
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

@app.get("/api/files")
async def get_all_files():
    """모든 파일 목록 조회"""
    try:
        files = db.get_all_files()
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


@app.post("/api/files/{file_id}/translate/en")
async def translate_file_to_english(file_id: str):
    try:
        file = db.get_file_by_id(file_id)
        if not file:
            raise HTTPException(status_code=404, detail="File not found.")
        if file.get("english_srt_text"):
            return {"success": True, "english_srt_text": file["english_srt_text"], "cached": True}
        english_srt_text = await translate_srt_to_english(file.get("corrected_srt_text") or file.get("srt_text") or "")
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
        corrected_srt_text = await correct_korean_srt(file.get("srt_text") or "")
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
        )
        return artifact_api_response(artifact)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Captioned dubbed video generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    return {
        "success": True,
        "provider": active_tts_provider(),
        "voices": voices,
        "defaults": {"ko": default_voice_for_language("ko"), "en": default_voice_for_language("en")},
        "supports": {"single_speaker": True, "multi_speaker": False, "style_prompt": False},
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
    db.update_job(job_id, status="running", progress=5, message="작업 시작")
    try:
        file = db.get_file_by_id(file_id)
        if not file:
            raise HTTPException(status_code=404, detail="File not found.")

        result_artifact_id = None
        if job_type == "correct_ko":
            db.update_job(job_id, progress=25, message="Gemini로 한국어 SRT 보정 중")
            corrected_srt_text = await correct_korean_srt(file.get("srt_text") or "")
            db.update_file_fields(file_id, corrected_srt_text=corrected_srt_text)
            db.update_job(job_id, status="completed", progress=100, message="한국어 SRT 보정 완료")
            return

        if job_type == "translate_en":
            db.update_job(job_id, progress=25, message="Gemini로 영어 SRT 생성 중")
            english_srt_text = await translate_srt_to_english(file.get("corrected_srt_text") or file.get("srt_text") or "")
            db.update_english_srt(file_id, english_srt_text)
            db.update_job(job_id, status="completed", progress=100, message="영어 SRT 생성 완료")
            return

        if job_type == "audio":
            db.update_job(job_id, progress=20, message="SRT 타임라인에 맞춰 MP3 생성 중")
            artifact = await create_audio_artifact_for_file(
                file,
                metadata.get("language", "ko"),
                voice_name=metadata.get("voice_name"),
                style_prompt=metadata.get("style_prompt"),
                srt_source=metadata.get("srt_source"),
            )
            result_artifact_id = artifact["id"]
            db.update_job(job_id, status="completed", progress=100, message="MP3 생성 완료", result_artifact_id=result_artifact_id)
            return

        if job_type == "dub_video":
            db.update_job(job_id, progress=20, message="음성 생성 및 영상 합성 중")
            artifact = await create_video_artifact_for_file(
                file,
                metadata.get("language", "ko"),
                voice_name=metadata.get("voice_name"),
                style_prompt=metadata.get("style_prompt"),
                srt_source=metadata.get("srt_source"),
            )
            result_artifact_id = artifact["id"]
            db.update_job(job_id, status="completed", progress=100, message="더빙 영상 생성 완료", result_artifact_id=result_artifact_id)
            return

        if job_type == "subtitle_video":
            db.update_job(job_id, progress=20, message="자막 영상 생성 중")
            artifact = await create_subtitle_video_artifact_for_file(
                file,
                metadata.get("language", "ko"),
                srt_source=metadata.get("srt_source"),
                subtitle_style=SubtitleStyleRequest(**metadata["subtitle_style"]) if metadata.get("subtitle_style") else None,
            )
            result_artifact_id = artifact["id"]
            db.update_job(job_id, status="completed", progress=100, message="자막 영상 생성 완료", result_artifact_id=result_artifact_id)
            return

        if job_type == "captioned_dub_video":
            db.update_job(job_id, progress=20, message="더빙 음성 생성 및 자막 합성 중")
            artifact = await create_captioned_dub_video_artifact_for_file(
                file,
                metadata.get("language", "ko"),
                voice_name=metadata.get("voice_name"),
                style_prompt=metadata.get("style_prompt"),
                srt_source=metadata.get("srt_source"),
                subtitle_style=SubtitleStyleRequest(**metadata["subtitle_style"]) if metadata.get("subtitle_style") else None,
            )
            result_artifact_id = artifact["id"]
            db.update_job(job_id, status="completed", progress=100, message="자막+더빙 영상 생성 완료", result_artifact_id=result_artifact_id)
            return

        raise HTTPException(status_code=400, detail="Unsupported job type.")
    except Exception as e:
        detail = getattr(e, "detail", str(e))
        db.update_job(job_id, status="failed", progress=0, message="작업 실패", error=str(detail))


@app.post("/api/files/{file_id}/jobs/{job_type}")
async def start_file_job(file_id: str, job_type: str, request: JobRequest, background_tasks: BackgroundTasks):
    allowed = {"correct_ko", "translate_en", "audio", "dub_video", "subtitle_video", "captioned_dub_video"}
    if job_type not in allowed:
        raise HTTPException(status_code=400, detail="Unsupported job type.")
    if not db.get_file_by_id(file_id):
        raise HTTPException(status_code=404, detail="File not found.")
    metadata = request.model_dump()
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
    return {"success": True, "file": prepare_file_for_api(db.get_file_by_id(file["id"]), include_original=True)}


@app.get("/api/artifacts/{artifact_id}/download")
async def download_artifact(artifact_id: str):
    artifact = db.get_artifact_by_id(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found.")
    path = Path(artifact.get("path") or "")
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact file is missing.")
    return FileResponse(path, filename=artifact.get("filename") or path.name)


@app.get("/api/artifacts/{artifact_id}/preview")
async def preview_artifact(artifact_id: str):
    artifact = db.get_artifact_by_id(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found.")
    path = Path(artifact.get("path") or "")
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact file is missing.")
    return FileResponse(path, media_type=media_type_for_path(path))


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

