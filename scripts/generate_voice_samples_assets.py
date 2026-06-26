import ast
import base64
import json
import os
import re
import time
import wave
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydub import AudioSegment


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_TEXT = "안녕하세요? 저는 AI 모델입니다. Hello? I am AI Speech Model"
STYLE_PROMPT = "Read this short Korean and English voice sample naturally, clearly, and warmly."
ASSET_SAMPLE_DIR = ROOT / "assets" / "voice_samples"
TMP_DIR = ROOT / "outputs"


def sanitize_output_name(filename: str) -> str:
    stem = Path(filename or "output").stem
    stem = re.sub(r"[^\w가-힣.-]+", "_", stem, flags=re.UNICODE).strip("._")
    return stem or "output"


def load_tts_voices() -> list[dict]:
    tree = ast.parse((ROOT / "main.py").read_text(encoding="utf-8-sig"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "TTS_VOICES":
                    return ast.literal_eval(node.value)
    raise RuntimeError("TTS_VOICES was not found in main.py")


def service_account_project_id() -> str | None:
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not credentials_path:
        return None
    path = Path(credentials_path)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8")).get("project_id")


def make_client():
    provider = os.getenv("GEMINI_PROVIDER", "gemini_api").lower()
    if provider in {"vertex_ai", "vertex", "google_cloud"}:
        project = (
            os.getenv("GOOGLE_CLOUD_PROJECT")
            or os.getenv("GOOGLE_CLOUD_PROJECT_ID")
            or service_account_project_id()
        )
        if not project:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT or service account project_id is required.")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", os.getenv("VERTEX_AI_LOCATION", "global"))
        return genai.Client(
            vertexai=True,
            project=project,
            location=location,
            http_options=types.HttpOptions(api_version="v1"),
        )

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY is required.")
    return genai.Client(api_key=api_key)


def extract_tts_pcm(response) -> bytes:
    part = response.candidates[0].content.parts[0]
    inline_data = getattr(part, "inline_data", None) or getattr(part, "inlineData", None)
    data = getattr(inline_data, "data", None)
    if isinstance(data, bytes):
        return data
    if isinstance(data, str):
        return base64.b64decode(data)
    raise RuntimeError("Gemini TTS response did not include audio data.")


def write_wave_file(path: Path, pcm: bytes) -> None:
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(24000)
        wav_file.writeframes(pcm)


def generate_voice_sample(client, model: str, voice_name: str, output_path: Path) -> None:
    prompt = f"{STYLE_PROMPT}\nRead the following Korean and English text exactly:\n{SAMPLE_TEXT}"
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                )
            ),
        ),
    )
    wav_path = TMP_DIR / f"voice_sample_{sanitize_output_name(voice_name)}.wav"
    write_wave_file(wav_path, extract_tts_pcm(response))
    try:
        audio = AudioSegment.from_file(wav_path, format="wav")
        with open(output_path, "wb") as mp3_file:
            audio.export(mp3_file, format="mp3", bitrate="192k")
    finally:
        wav_path.unlink(missing_ok=True)


def main() -> int:
    load_dotenv(ROOT / ".env")
    credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if credentials and not Path(credentials).is_absolute():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(ROOT / credentials)

    ASSET_SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(exist_ok=True)

    voices = load_tts_voices()
    client = make_client()
    model = os.getenv("GEMINI_TTS_MODEL", "gemini-2.5-flash-tts")
    failures = []

    for index, voice in enumerate(voices, start=1):
        voice_name = voice["name"]
        output_path = ASSET_SAMPLE_DIR / f"gemini_{sanitize_output_name(voice_name)}.mp3"
        print(f"[{index}/{len(voices)}] generating {voice_name} -> {output_path}")
        try:
            generate_voice_sample(client, model, voice_name, output_path)
        except Exception as exc:
            failures.append({"voice": voice_name, "error": str(exc)})
            print(f"  failed: {exc}")
        time.sleep(0.3)

    print(f"done: {len(voices) - len(failures)} generated, {len(failures)} failed")
    if failures:
        print(json.dumps(failures, ensure_ascii=False, indent=2))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
