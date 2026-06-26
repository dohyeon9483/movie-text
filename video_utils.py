import json
import os
import subprocess
import uuid
from pathlib import Path
from typing import Dict, List, Tuple

from fastapi import HTTPException

VIDEO_TRANSCODE_PRESET = os.getenv("AI_VIDEO_TRANSCODE_PRESET", "medium")
VIDEO_TRANSCODE_CRF = os.getenv("AI_VIDEO_TRANSCODE_CRF", "18")


def generate_video_thumbnail(video_path: Path, output_path: Path) -> bool:
    command = [
        "ffmpeg", "-y",
        "-ss", "00:00:01",
        "-i", str(video_path),
        "-frames:v", "1",
        "-vf", "scale=480:-1",
        str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return result.returncode == 0 and output_path.exists()


def create_black_video(duration_ms: int, output_path: Path) -> None:
    duration = max(duration_ms / 1000, 0.1)
    command = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "color=c=black:s=1280x720:r=30",
        "-t", f"{duration:.3f}",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"black video generation failed: {result.stderr[-1000:]}")


def create_slide_segment(
    slide_path: Path,
    duration_seconds: float,
    output_path: Path,
    fade_seconds: float = 0.35,
    target_width: int = 1920,
    target_height: int = 1080,
) -> None:
    duration = max(float(duration_seconds or 0), 0.1)
    fade = min(max(float(fade_seconds or 0), 0.0), max((duration - 0.05) / 2, 0.0))
    fade_out_start = max(duration - fade, 0.0)
    target_width = max(2, int(target_width) - (int(target_width) % 2))
    target_height = max(2, int(target_height) - (int(target_height) % 2))
    video_filter = (
        f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
        f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:black,"
        "setsar=1,format=yuv420p"
    )
    if fade > 0.01:
        video_filter = f"{video_filter},fade=t=in:st=0:d={fade:.3f},fade=t=out:st={fade_out_start:.3f}:d={fade:.3f}"
    command = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-t", f"{duration:.3f}",
        "-i", str(slide_path.resolve()),
        "-vf", video_filter,
        "-r", "30",
        "-an",
        "-c:v", "libx264",
        "-preset", VIDEO_TRANSCODE_PRESET,
        "-crf", VIDEO_TRANSCODE_CRF,
        str(output_path.resolve()),
    ]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"slide segment generation failed: {result.stderr[-1000:]}")


def ffprobe_json(path: Path) -> Dict:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-print_format", "json",
            "-show_streams",
            "-show_format",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"ffprobe failed: {result.stderr[-1000:]}")
    return json.loads(result.stdout or "{}")


def media_duration_seconds(path: Path) -> float:
    info = ffprobe_json(path)
    duration = (info.get("format") or {}).get("duration")
    try:
        return max(float(duration), 0.1)
    except (TypeError, ValueError):
        return 0.1


def media_video_dimensions(path: Path) -> Tuple[int, int]:
    info = ffprobe_json(path)
    for stream in info.get("streams", []):
        if stream.get("codec_type") != "video":
            continue
        try:
            width = int(stream.get("width") or 0)
            height = int(stream.get("height") or 0)
        except (TypeError, ValueError):
            continue
        if width > 0 and height > 0:
            return width - (width % 2), height - (height % 2)
    return 1280, 720


def has_audio_stream(path: Path) -> bool:
    info = ffprobe_json(path)
    return any(stream.get("codec_type") == "audio" for stream in info.get("streams", []))


def trim_video_file(source_path: Path, output_path: Path, start_seconds: float, end_seconds: float) -> None:
    start = max(float(start_seconds or 0), 0.0)
    end = max(float(end_seconds or 0), start + 0.1)
    command = [
        "ffmpeg", "-y",
        "-ss", f"{start:.3f}",
        "-to", f"{end:.3f}",
        "-i", str(source_path),
        "-map", "0:v:0",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-c:a", "aac",
        "-movflags", "+faststart",
        str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"trim failed: {result.stderr[-1000:]}")


def normalize_video_for_concat(source_path: Path, output_path: Path, target_width: int, target_height: int) -> None:
    duration = media_duration_seconds(source_path)
    target_width = max(2, int(target_width) - (int(target_width) % 2))
    target_height = max(2, int(target_height) - (int(target_height) % 2))
    video_filter = (
        f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
        f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2,"
        "setsar=1,fps=24,format=yuv420p"
    )
    if has_audio_stream(source_path):
        command = [
            "ffmpeg", "-y",
            "-i", str(source_path),
            "-vf", video_filter,
            "-map", "0:v:0",
            "-map", "0:a:0",
            "-c:v", "libx264",
            "-preset", VIDEO_TRANSCODE_PRESET,
            "-crf", VIDEO_TRANSCODE_CRF,
            "-c:a", "aac",
            "-ar", "44100",
            "-ac", "2",
            "-shortest",
            str(output_path),
        ]
    else:
        command = [
            "ffmpeg", "-y",
            "-i", str(source_path),
            "-f", "lavfi",
            "-t", f"{duration:.3f}",
            "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-vf", video_filter,
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "libx264",
            "-preset", VIDEO_TRANSCODE_PRESET,
            "-crf", VIDEO_TRANSCODE_CRF,
            "-c:a", "aac",
            "-shortest",
            str(output_path),
        ]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"normalize failed: {result.stderr[-1000:]}")


def concat_video_files(first_path: Path, second_path: Path, output_path: Path, temp_dir: Path) -> None:
    concat_video_sequence([first_path, second_path], output_path, temp_dir)


def concat_video_sequence(source_paths: List[Path], output_path: Path, temp_dir: Path) -> None:
    if len(source_paths) < 2:
        raise HTTPException(status_code=400, detail="At least two videos are required.")
    temp_paths = [temp_dir / f"concat_{index}_{uuid.uuid4().hex}.mp4" for index, _ in enumerate(source_paths)]
    concat_list = temp_dir / f"concat_{uuid.uuid4().hex}.txt"
    try:
        target_width, target_height = media_video_dimensions(source_paths[0])
        for source_path, temp_path in zip(source_paths, temp_paths):
            normalize_video_for_concat(source_path, temp_path, target_width, target_height)
        concat_list.write_text(
            "".join(f"file '{path.resolve().as_posix()}'\n" for path in temp_paths),
            encoding="utf-8",
        )
        command = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list),
            "-c", "copy",
            "-movflags", "+faststart",
            str(output_path),
        ]
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"concat failed: {result.stderr[-1000:]}")
    finally:
        for path in [*temp_paths, concat_list]:
            try:
                path.unlink()
            except OSError:
                pass


def crossfade_video_sequence(source_paths: List[Path], display_durations: List[float], output_path: Path, transition_seconds: float = 0.4) -> None:
    if not source_paths:
        raise HTTPException(status_code=400, detail="At least one video is required.")
    if len(source_paths) != len(display_durations):
        raise HTTPException(status_code=400, detail="Video count and duration count must match.")
    if len(source_paths) == 1:
        command = [
            "ffmpeg", "-y",
            "-i", str(source_paths[0]),
            "-c", "copy",
            "-movflags", "+faststart",
            str(output_path),
        ]
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"single slide copy failed: {result.stderr[-1000:]}")
        return

    transition = max(float(transition_seconds or 0), 0.0)
    if transition <= 0.01:
        temp_dir = output_path.parent
        concat_video_sequence(source_paths, output_path, temp_dir)
        return

    inputs = []
    for path in source_paths:
        inputs.extend(["-i", str(path)])

    filter_parts = []
    previous_label = "0:v"
    cumulative = max(float(display_durations[0] or 0), 0.1)
    for index in range(1, len(source_paths)):
        output_label = f"v{index}"
        safe_duration = min(transition, max(float(display_durations[index - 1] or 0) / 2, 0.05), max(float(display_durations[index] or 0) / 2, 0.05))
        filter_parts.append(
            f"[{previous_label}][{index}:v]xfade=transition=fade:duration={safe_duration:.3f}:offset={cumulative:.3f}[{output_label}]"
        )
        previous_label = output_label
        cumulative += max(float(display_durations[index] or 0), 0.1)

    command = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", ";".join(filter_parts),
        "-map", f"[{previous_label}]",
        "-an",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"crossfade failed: {result.stderr[-1000:]}")
