"""
Adobe Premiere Pro XML exporter.

Generates FCP XML v5 (Interchange format), which Premiere Pro CS6
through CC 2017+ can import. This is the legacy XML format, not FCPXML.
"""

from lxml import etree
from pathlib import Path
from ..core.sync_engine import SyncSession
from ..core.media_handler import probe_file
import uuid


def seconds_to_ticks(seconds: float, timebase: int = 30) -> int:
    """Convert seconds to Premiere timeline ticks (frames)."""
    return int(round(seconds * timebase))


def export_premiere_xml(
    session: SyncSession,
    output_path: Path,
    project_name: str = "asynk Synced Timeline",
    timebase: int = 30,
) -> Path:
    """
    Export synced session as Premiere Pro compatible XML (FCP Interchange v5).

    Args:
        session: completed SyncSession
        output_path: destination .xml file
        project_name: sequence name in Premiere
        timebase: frames per second for the timeline

    Returns:
        Path to exported file
    """
    xmeml = etree.Element("xmeml", version="5")
    sequence = etree.SubElement(xmeml, "sequence")
    etree.SubElement(sequence, "name").text = project_name
    etree.SubElement(sequence, "duration").text = "0"  # updated later

    # Rate
    rate = etree.SubElement(sequence, "rate")
    etree.SubElement(rate, "timebase").text = str(timebase)
    etree.SubElement(rate, "ntsc").text = "FALSE"

    # Timecode
    tc = etree.SubElement(sequence, "timecode")
    tc_rate = etree.SubElement(tc, "rate")
    etree.SubElement(tc_rate, "timebase").text = str(timebase)
    etree.SubElement(tc_rate, "ntsc").text = "FALSE"
    etree.SubElement(tc, "string").text = "00:00:00:00"
    etree.SubElement(tc, "frame").text = "0"

    # Media
    media = etree.SubElement(sequence, "media")

    # --- Video tracks ---
    video = etree.SubElement(media, "video")

    # Calculate offset shift (make all offsets non-negative)
    min_offset = 0.0
    for result in session.results:
        if result.success:
            min_offset = min(min_offset, result.offset_seconds)

    max_end = 0
    track_index = 0

    for result in session.results:
        if not result.success:
            continue

        try:
            info = probe_file(result.clip_path)
        except Exception:
            continue

        if not info.has_video:
            continue

        track = etree.SubElement(video, "track")
        adjusted_offset = result.offset_seconds - min_offset
        start_frame = seconds_to_ticks(adjusted_offset, timebase)
        duration_frames = seconds_to_ticks(info.duration_seconds, timebase)
        end_frame = start_frame + duration_frames
        max_end = max(max_end, end_frame)

        clip_item = etree.SubElement(track, "clipitem", id=f"clip-{track_index}")
        etree.SubElement(clip_item, "name").text = result.clip_path.stem
        etree.SubElement(clip_item, "duration").text = str(duration_frames)

        clip_rate = etree.SubElement(clip_item, "rate")
        etree.SubElement(clip_rate, "timebase").text = str(timebase)
        etree.SubElement(clip_rate, "ntsc").text = "FALSE"

        etree.SubElement(clip_item, "start").text = str(start_frame)
        etree.SubElement(clip_item, "end").text = str(end_frame)
        etree.SubElement(clip_item, "in").text = "0"
        etree.SubElement(clip_item, "out").text = str(duration_frames)

        # File reference
        file_elem = etree.SubElement(
            clip_item, "file", id=f"file-{track_index}"
        )
        etree.SubElement(file_elem, "name").text = result.clip_path.name
        etree.SubElement(file_elem, "pathurl").text = (
            f"file://localhost{result.clip_path.resolve()}"
        )

        file_rate = etree.SubElement(file_elem, "rate")
        etree.SubElement(file_rate, "timebase").text = str(timebase)
        etree.SubElement(file_rate, "ntsc").text = "FALSE"

        etree.SubElement(file_elem, "duration").text = str(duration_frames)

        # Media info inside file
        file_media = etree.SubElement(file_elem, "media")
        file_video = etree.SubElement(file_media, "video")
        file_audio = etree.SubElement(file_media, "audio")

        track_index += 1

    # --- Audio tracks ---
    audio_section = etree.SubElement(media, "audio")
    track_index = 0

    for result in session.results:
        if not result.success:
            continue

        try:
            info = probe_file(result.clip_path)
        except Exception:
            continue

        if not info.has_audio:
            continue

        track = etree.SubElement(audio_section, "track")
        adjusted_offset = result.offset_seconds - min_offset
        start_frame = seconds_to_ticks(adjusted_offset, timebase)
        duration_frames = seconds_to_ticks(info.duration_seconds, timebase)
        end_frame = start_frame + duration_frames

        clip_item = etree.SubElement(
            track, "clipitem", id=f"audio-clip-{track_index}"
        )
        etree.SubElement(clip_item, "name").text = result.clip_path.stem
        etree.SubElement(clip_item, "duration").text = str(duration_frames)

        clip_rate = etree.SubElement(clip_item, "rate")
        etree.SubElement(clip_rate, "timebase").text = str(timebase)
        etree.SubElement(clip_rate, "ntsc").text = "FALSE"

        etree.SubElement(clip_item, "start").text = str(start_frame)
        etree.SubElement(clip_item, "end").text = str(end_frame)
        etree.SubElement(clip_item, "in").text = "0"
        etree.SubElement(clip_item, "out").text = str(duration_frames)

        # Reference the same file element
        etree.SubElement(
            clip_item, "file", id=f"file-{track_index}"
        )

        track_index += 1

    # Update total duration
    sequence.find("duration").text = str(max_end)

    # Write
    output_path = Path(output_path)
    if not output_path.suffix:
        output_path = output_path.with_suffix(".xml")

    tree = etree.ElementTree(xmeml)
    tree.write(
        str(output_path),
        xml_declaration=True,
        encoding="UTF-8",
        pretty_print=True,
    )

    return output_path
