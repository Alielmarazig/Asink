"""
CMX 3600 EDL exporter.

Generates standard Edit Decision Lists compatible with:
- Sony Vegas Pro 13
- Magix Vegas Pro 14+
- EDIUS 7.5+
- Most NLEs that support EDL import

EDL is a simple text format listing edit events with timecodes.
"""

from pathlib import Path
from ..core.sync_engine import SyncSession
from ..core.media_handler import probe_file


def seconds_to_timecode(seconds: float, fps: float = 30.0) -> str:
    """
    Convert seconds to SMPTE timecode HH:MM:SS:FF.
    """
    if seconds < 0:
        seconds = 0.0

    total_frames = int(round(seconds * fps))
    ff = total_frames % int(fps)
    total_seconds = total_frames // int(fps)
    ss = total_seconds % 60
    total_minutes = total_seconds // 60
    mm = total_minutes % 60
    hh = total_minutes // 60

    return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"


def export_edl(
    session: SyncSession,
    output_path: Path,
    title: str = "asynk Synced Timeline",
    fps: float = 30.0,
) -> Path:
    """
    Export synced session as CMX 3600 EDL.

    Each synced clip becomes an edit event. The record timecode
    reflects the sync offset so clips align when imported.

    Args:
        session: completed SyncSession
        output_path: destination .edl file
        title: EDL title
        fps: frame rate for timecode calculation

    Returns:
        Path to exported file
    """
    lines = []
    lines.append(f"TITLE: {title}")
    lines.append(f"FCM: NON-DROP FRAME")
    lines.append("")

    # Shift offsets so the earliest clip starts at 01:00:00:00
    # (standard EDL convention for program start)
    min_offset = 0.0
    for result in session.results:
        if result.success:
            min_offset = min(min_offset, result.offset_seconds)

    program_start = 3600.0  # 01:00:00:00 in seconds
    event_num = 1

    for result in session.results:
        if not result.success:
            continue

        try:
            info = probe_file(result.clip_path)
        except Exception:
            continue

        # Source timecodes (from start of the source clip)
        src_in = 0.0
        src_out = info.duration_seconds

        # Record timecodes (where this clip lands on the timeline)
        adjusted_offset = result.offset_seconds - min_offset
        rec_in = program_start + adjusted_offset
        rec_out = rec_in + info.duration_seconds

        # Determine edit type
        if info.has_video and info.has_audio:
            channels = "B"    # Both
        elif info.has_video:
            channels = "V"    # Video only
        else:
            channels = "A"    # Audio only

        # Event line: EDL_NUM  REEL  CHANNEL  TRANSITION  SRC_IN  SRC_OUT  REC_IN  REC_OUT
        # Use filename (truncated to 8 chars) as reel name for compatibility
        reel = result.clip_path.stem[:8].upper().ljust(8)

        event_line = (
            f"{event_num:03d}  "
            f"{reel}  "
            f"{channels:4s} "
            f"C        "  # Cut transition
            f"{seconds_to_timecode(src_in, fps)} "
            f"{seconds_to_timecode(src_out, fps)} "
            f"{seconds_to_timecode(rec_in, fps)} "
            f"{seconds_to_timecode(rec_out, fps)}"
        )
        lines.append(event_line)

        # Source file comment (helps NLEs find the actual file)
        lines.append(
            f"* FROM CLIP NAME: {result.clip_path.name}"
        )
        lines.append(
            f"* SOURCE FILE: {result.clip_path.resolve()}"
        )

        # Confidence comment
        lines.append(
            f"* SYNC CONFIDENCE: {result.confidence:.3f}"
        )
        lines.append("")

        event_num += 1

    # Write
    output_path = Path(output_path)
    if not output_path.suffix:
        output_path = output_path.with_suffix(".edl")

    output_path.write_text("\n".join(lines), encoding="utf-8")

    return output_path
