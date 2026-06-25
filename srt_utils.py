import re
from typing import Dict, List, Optional


SRT_TIME_RE = re.compile(
    r"(?P<start>\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(?P<end>\d{2}:\d{2}:\d{2},\d{3})"
)
FILLER_ONLY_RE = re.compile(r"^\s*(?:\uc5b4+|\uc74c+|\uc544+|\uadf8+|\uc800+|\ubb50+|\uc57d\uac04|\uc774\uc81c|\uadf8\ub7ec\ub2c8\uae4c|\uadf8\ub7ec\uba74|\uc790)\s*[.\u2026,!?\-~]*\s*$", re.IGNORECASE)
FILLER_PREFIX_RE = re.compile(r"^\s*(?:\uc5b4+|\uc74c+|\uc544+|\uc800+|\uadf8+|\ubb50+|\uc790)\s*[.\u2026,!?\-~]*\s+", re.IGNORECASE)
FILLER_REPEAT_RE = re.compile(r"\b(?:\uc5b4|\uc74c|\uc544|\uc800|\uadf8)\s*[.\u2026,!?\-~]+\s*(?=\S)")


def format_srt_time(seconds: float) -> str:
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
    if end_seconds <= start_seconds:
        end_seconds = start_seconds + 2.0
    return (
        f"{index}\n"
        f"{format_srt_time(start_seconds)} --> {format_srt_time(end_seconds)}\n"
        f"{text.strip()}"
    )


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


def parse_gemini_srt_time(value) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return max(float(value), 0.0)
    text = str(value).strip().replace(".", ",")
    if re.fullmatch(r"\d{2}:\d{2}:\d{2},\d{3}", text):
        return parse_srt_timecode(text)
    return None


def build_srt_from_timed_items(items: List[Dict]) -> str:
    entries = []
    for index, item in enumerate(items, start=1):
        entries.append(format_srt_entry(index, item["start"], item["end"], item["text"]))
    return "\n\n".join(entries)


def clean_corrected_subtitle_text(text: str, fallback: str = "") -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if not cleaned:
        return fallback.strip()
    if FILLER_ONLY_RE.fullmatch(cleaned):
        return fallback.strip() or cleaned
    previous = None
    while previous != cleaned:
        previous = cleaned
        cleaned = FILLER_PREFIX_RE.sub("", cleaned).strip()
    cleaned = FILLER_REPEAT_RE.sub("", cleaned).strip()
    cleaned = re.sub(r"\s+([,.!?;:])", r"\1", cleaned)
    return cleaned or fallback.strip()


def normalize_corrected_srt_by_index(corrected_items: List[Dict], original_cues: List[Dict]) -> Optional[str]:
    if not isinstance(corrected_items, list):
        return None
    corrected_by_index = {}
    for item in corrected_items:
        if not isinstance(item, dict) or item.get("index") is None:
            continue
        try:
            index = int(item.get("index"))
        except (TypeError, ValueError):
            continue
        text = str(item.get("text", "")).strip()
        if text:
            corrected_by_index[index] = {
                "text": text,
                "start": parse_gemini_srt_time(item.get("start") or item.get("start_code")),
                "end": parse_gemini_srt_time(item.get("end") or item.get("end_code")),
            }
    if not corrected_by_index:
        return None

    entries = []
    for cue in original_cues:
        corrected = corrected_by_index.get(cue["index"]) or {}
        text = clean_corrected_subtitle_text(corrected.get("text") or cue["text"], cue["text"])
        start = corrected.get("start") if corrected.get("start") is not None else cue["start"]
        end = corrected.get("end") if corrected.get("end") is not None else cue["end"]
        if end <= start:
            start, end = cue["start"], cue["end"]
        entries.append(format_srt_entry(len(entries) + 1, start, end, text))
    return "\n\n".join(entries)


def normalize_corrected_srt_items(corrected_items: List[Dict], original_cues: List[Dict]) -> List[Dict]:
    original_by_index = {int(cue["index"]): cue for cue in original_cues}
    original_start = min((cue["start"] for cue in original_cues), default=0.0)
    original_end = max((cue["end"] for cue in original_cues), default=0.0)
    normalized = []

    for item in corrected_items:
        if not isinstance(item, dict):
            continue
        text = clean_corrected_subtitle_text(str(item.get("text", "")).strip())
        if not text:
            continue
        original = None
        try:
            original = original_by_index.get(int(item.get("index")))
        except (TypeError, ValueError):
            original = None
        start = parse_gemini_srt_time(item.get("start") or item.get("start_code"))
        end = parse_gemini_srt_time(item.get("end") or item.get("end_code"))
        if (start is None or end is None) and original:
            start = original["start"]
            end = original["end"]
        if start is None or end is None or end <= start:
            continue
        start = max(original_start, min(start, original_end))
        end = max(original_start, min(end, original_end))
        if end <= start:
            continue
        normalized.append({"start": start, "end": end, "text": text})

    normalized.sort(key=lambda cue: (cue["start"], cue["end"]))
    repaired = []
    previous_end = original_start
    for cue in normalized:
        start = max(cue["start"], previous_end)
        end = max(cue["end"], start + 0.2)
        end = min(end, original_end)
        if end <= start:
            continue
        repaired.append({"start": start, "end": end, "text": cue["text"]})
        previous_end = end
    return repaired
