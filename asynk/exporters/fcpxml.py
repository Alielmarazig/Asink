"""
Final Cut Pro X FCPXML exporter.

Generates FCPXML v1.9 (compatible with FCP X 10.2.3+).
Creates a project with all synced clips on separate tracks,
offset by their calculated sync positions.
"""

from lxml import etree
from pathlib import Path
from ..core.sync_engine import SyncSession
from ..core.media_handler import probe_file
import math


def frames_from_seconds(seconds: float, fps: float) -> int:
    """Convert seconds to frame count."""
    return int(round(seconds * fps))


def rational_time(seconds: float, fps: float) -> str:
    """
    Convert seconds to FCPXML rational time format.
    Example: "1001/30000s" for 30fps NTSC
    """
    # Use frame-based rational: frames/fps as integer fraction
    frames = frames_from_seconds(abs(seconds), fps)
    fps_int = int(round(fps))

    # Handle common NTSC rates
    if abs(fps - 23.976) < 0.01:
        return f"{frames * 1001}/24000s"
    elif abs(fps - 29.97) < 0.01:
        return f"{frames * 1001}/30000s"
    elif abs(fps - 59.94) < 0.01:
        return f"{frames * 1001}/60000s"
    else:
        return f"{frames}/{fps_int}s"


def duration_rational(seconds: float, fps: float) -> str:
    """Duration as rational time, always positive."""
    return rational_time(abs(seconds), fps)


def export_fcpxml(
    session: SyncSession,
    output_path: Path,
    project_name: str = "asynk Synced Timeline",
    fps: float = 24.0,
) -> Path:
    """
    Export a synced session as FCPXML v1.9.

    Args:
        session: completed SyncSession
        output_path: where to write the .fcpxml file
        project_name: name shown in FCP X
        fps: timeline frame rate

    Returns:
        Path to the exported file
    """
    # Root element
    fcpxml = etree.Element("fcpxml", version="1.9")

    # Resources
    resources = etree.SubElement(fcpxml, "resources")

    # Format resource
    fps_int = int(round(fps))
    if abs(fps - 23.976) < 0.01:
        frame_dur = "1001/24000s"
    elif abs(fps - 29.97) < 0.01:
        frame_dur = "1001/30000s"
    else:
        frame_dur = f"100/{fps_int * 100}s"

    etree.SubElement(resources, "format", id="r0",
                     frameDuration=frame_dur, width="1920", height="1080")

    # Add asset resources for each clip
    asset_ids = {}
    for i, result in enumerate(session.results):
        if not result.success:
            continue

        asset_id = f"r{i + 1}"
        asset_ids[result.clip_path] = asset_id

        # Probe for duration
        try:
            info = probe_file(result.clip_path)
            dur = duration_rational(info.duration_seconds, fps)
        except Exception:
            dur = "0/1s"

        asset = etree.SubElement(resources, "asset",
                                 id=asset_id,
                                 name=result.clip_path.stem,
                                 src=str(result.clip_path.resolve()),
                                 duration=dur,
                                 format="r0",
                                 hasVideo="1" if info.has_video else "0",
                                 hasAudio="1" if info.has_audio else "0")

    # Library > Event > Project > Sequence
    library = etree.SubElement(fcpxml, "library")
    event = etree.SubElement(library, "event", name="asynk Sync")
    project = etree.SubElement(event, "project", name=project_name)

    # Find total duration (max end point across all clips)
    max_end = 0.0
    for result in session.results:
        if not result.success:
            continue
        try:
            info = probe_file(result.clip_path)
            clip_end = result.offset_seconds + info.duration_seconds
            max_end = max(max_end, clip_end)
        except Exception:
            pass

    sequence = etree.SubElement(
        project, "sequence",
        duration=duration_rational(max_end, fps),
        format="r0"
    )

    spine = etree.SubElement(sequence, "spine")

    # Calculate the earliest offset (most negative) to shift everything
    min_offset = 0.0
    for result in session.results:
        if result.success:
            min_offset = min(min_offset, result.offset_seconds)

    # Place clips on the spine
    # First clip on spine, rest as connected clips (FCP X model)
    first_placed = False
    for result in session.results:
        if not result.success or result.clip_path not in asset_ids:
            continue

        asset_id = asset_ids[result.clip_path]
        adjusted_offset = result.offset_seconds - min_offset

        try:
            info = probe_file(result.clip_path)
            dur = duration_rational(info.duration_seconds, fps)
        except Exception:
            continue

        if not first_placed:
            # Primary storyline clip
            clip_elem = etree.SubElement(
                spine, "asset-clip",
                ref=asset_id,
                duration=dur,
                offset=rational_time(adjusted_offset, fps),
                name=result.clip_path.stem,
            )
            first_placed = True
        else:
            # Connected clip (secondary tracks)
            clip_elem = etree.SubElement(
                spine, "asset-clip",
                ref=asset_id,
                duration=dur,
                offset=rational_time(adjusted_offset, fps),
                name=result.clip_path.stem,
                lane=str(session.results.index(result)),
            )

    # Write
    tree = etree.ElementTree(fcpxml)
    output_path = Path(output_path)
    if not output_path.suffix:
        output_path = output_path.with_suffix(".fcpxml")

    tree.write(
        str(output_path),
        xml_declaration=True,
        encoding="UTF-8",
        pretty_print=True,
    )

    return output_path
