import os
from contextvars import ContextVar
from typing import Any, Dict, Optional

import database as db


AI_USAGE_CONTEXT: ContextVar[Dict[str, Optional[str]]] = ContextVar("AI_USAGE_CONTEXT", default={})

GEMINI_INPUT_USD_PER_1M_TOKENS = float(os.getenv("AI_COST_GEMINI_INPUT_USD_PER_1M_TOKENS", "0.30"))
GEMINI_OUTPUT_USD_PER_1M_TOKENS = float(os.getenv("AI_COST_GEMINI_OUTPUT_USD_PER_1M_TOKENS", "2.50"))
GEMINI_TTS_INPUT_USD_PER_1M_TOKENS = float(os.getenv("AI_COST_GEMINI_TTS_INPUT_USD_PER_1M_TOKENS", "0.50"))
GOOGLE_CLOUD_TTS_USD_PER_1M_CHARS = float(os.getenv("AI_COST_GOOGLE_CLOUD_TTS_USD_PER_1M_CHARS", "16.0"))


def estimate_tokens_from_text(text: str) -> int:
    return max(1, int(len(text or "") / 4) + 1)


def usage_metadata_value(metadata: Any, *names: str) -> int:
    for name in names:
        if metadata is None:
            continue
        value = getattr(metadata, name, None)
        if value is None and isinstance(metadata, dict):
            value = metadata.get(name)
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                return 0
    return 0


def estimate_gemini_text_cost(input_tokens: int, output_tokens: int) -> float:
    return ((input_tokens or 0) / 1_000_000 * GEMINI_INPUT_USD_PER_1M_TOKENS) + (
        (output_tokens or 0) / 1_000_000 * GEMINI_OUTPUT_USD_PER_1M_TOKENS
    )


def estimate_gemini_tts_cost(input_tokens: int) -> float:
    return (input_tokens or 0) / 1_000_000 * GEMINI_TTS_INPUT_USD_PER_1M_TOKENS


def estimate_google_cloud_tts_cost(characters: int) -> float:
    return (characters or 0) / 1_000_000 * GOOGLE_CLOUD_TTS_USD_PER_1M_CHARS


def record_ai_usage(
    provider: str,
    model: str,
    operation: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    total_tokens: int = 0,
    characters: int = 0,
    request_count: int = 1,
    estimated_cost_usd: float = 0.0,
    metadata: Optional[Dict] = None,
) -> Dict:
    context = AI_USAGE_CONTEXT.get() or {}
    return db.create_ai_usage_event(
        provider=provider,
        model=model,
        operation=operation,
        file_id=context.get("file_id"),
        job_id=context.get("job_id"),
        artifact_id=context.get("artifact_id"),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens or (input_tokens or 0) + (output_tokens or 0),
        characters=characters,
        request_count=request_count,
        estimated_cost_usd=estimated_cost_usd,
        metadata=metadata or {},
    )


def pricing_config() -> Dict[str, float]:
    return {
        "gemini_input_usd_per_1m_tokens": GEMINI_INPUT_USD_PER_1M_TOKENS,
        "gemini_output_usd_per_1m_tokens": GEMINI_OUTPUT_USD_PER_1M_TOKENS,
        "gemini_tts_input_usd_per_1m_tokens": GEMINI_TTS_INPUT_USD_PER_1M_TOKENS,
        "google_cloud_tts_usd_per_1m_chars": GOOGLE_CLOUD_TTS_USD_PER_1M_CHARS,
    }
