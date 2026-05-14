"""
Media file handler. Probes files for metadata using FFmpeg/FFprobe.
"""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

SUPPORTED_VIDEO = {
    ".mp4", ".mov", ".avi", ".mkv", ".mxf", ".wmv", ".flv",
    ".m4v", ".mpg", ".mpeg", ".ts", ".webm", ".3gp",
    ".r3d", ".braw", ".ari",  # camera raw
}

SUPPORTED_AUDIO = {
    ".wav", ".mp3", ".aac", ".flac", ".ogg", ".wma",
    ".m4a", ".aiff", ".aif", ".opus",
}

SUPPORTED_EXTENSIONS = SUPPORTED_VIDEO | SUPPORTED_AUDIO


@dataclass
class MediaInfo:
    """Metadata extracted from a media file."""
    path: Path
    filename: str
    duration_seconds: float
    has_video: bool
    has_audio: bool
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    file_size_mb: float = 0.0
    timecode: Optional[str] = None  # embedded TC if present


def probe_file(filepath: Path) -> MediaInfo:
    """
    Run ffprobe on a file and return structured MediaInfo.
    """
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(filepath),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, check=True, text=True)
        data = json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Cannot probe {filepath.name}: {e}")

    fmt = data.get("format", {})
    streams = data.get("streams", [])

    video_stream = next(
        (s for s in streams if s.get("codec_type") == "video"),
        None
    )
    audio_stream = next(
        (s for s in streams if s.get("codec_type") == "audio"),
        None
    )

    # Parse FPS from video stream
    fps = None
    if video_stream:
        r_frame_rate = video_stream.get("r_frame_rate", "0/1")
        try:
            num, den = map(int, r_frame_rate.split("/"))
            fps = num / den if den else None
        except (ValueError, ZeroDivisionError):
            fps = None

    # Parse timecode from format tags
    timecode = None
    tags = fmt.get("tags", {})
    timecode = tags.get("timecode") or tags.get("TIMECODE")

    return MediaInfo(
        path=filepath,
        filename=filepath.name,
        duration_seconds=float(fmt.get("duration", 0)),
        has_video=video_stream is not None,
        has_audio=audio_stream is not None,
        video_codec=video_stream.get("codec_name") if video_stream else None,
        audio_codec=audio_stream.get("codec_name") if audio_stream else None,
        width=int(video_stream["width"]) if video_stream and "width" in video_stream else None,
        height=int(video_stream["height"]) if video_stream and "height" in video_stream else None,
        fps=fps,
        sample_rate=int(audio_stream["sample_rate"]) if audio_stream and "sample_rate" in audio_stream else None,
        channels=int(audio_stream["channels"]) if audio_stream and "channels" in audio_stream else None,
        file_size_mb=float(fmt.get("size", 0)) / (1024 * 1024),
        timecode=timecode,
    )


def scan_directory(directory: Path, recursive: bool = False) -> list[MediaInfo]:
    """Scan a directory for supported media files."""
    results = []
    pattern = "**/*" if recursive else "*"

    for f in sorted(directory.glob(pattern)):
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS:
            try:
                info = probe_file(f)
                results.append(info)
            except Exception as e:
                logger.warning(f"Skipping {f.name}: {e}")

    return results


def is_supported(filepath: Path) -> bool:
    """Check if a file extension is supported."""
    return filepath.suffix.lower() in SUPPORTED_EXTENSIONS
