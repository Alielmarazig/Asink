"""
Unified export manager. Single interface to export to any supported format.
"""

from enum import Enum
from pathlib import Path
from ..core.sync_engine import SyncSession
from .fcpxml import export_fcpxml
from .premiere_xml import export_premiere_xml
from .edl import export_edl


class ExportFormat(Enum):
    FCPXML = "fcpxml"          # Final Cut Pro X 10.2.3+
    PREMIERE_XML = "premiere"   # Premiere Pro CS6 / CC
    EDL = "edl"                # Vegas Pro / EDIUS / universal
    ALL = "all"                # Export all formats


FORMAT_EXTENSIONS = {
    ExportFormat.FCPXML: ".fcpxml",
    ExportFormat.PREMIERE_XML: ".xml",
    ExportFormat.EDL: ".edl",
}

FORMAT_LABELS = {
    ExportFormat.FCPXML: "Final Cut Pro X",
    ExportFormat.PREMIERE_XML: "Adobe Premiere Pro",
    ExportFormat.EDL: "EDL (Vegas / EDIUS / Universal)",
}


def export_session(
    session: SyncSession,
    output_dir: Path,
    format: ExportFormat = ExportFormat.ALL,
    project_name: str = "asynk Synced Timeline",
    fps: float = 24.0,
) -> list[Path]:
    """
    Export a sync session to one or more timeline formats.

    Args:
        session: completed SyncSession
        output_dir: directory for output files
        format: which format(s) to export
        project_name: name used inside timeline files
        fps: timeline frame rate

    Returns:
        List of exported file paths
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = project_name.replace(" ", "_")
    exported = []

    formats_to_export = (
        [ExportFormat.FCPXML, ExportFormat.PREMIERE_XML, ExportFormat.EDL]
        if format == ExportFormat.ALL
        else [format]
    )

    for fmt in formats_to_export:
        ext = FORMAT_EXTENSIONS[fmt]
        out_path = output_dir / f"{base_name}{ext}"

        if fmt == ExportFormat.FCPXML:
            export_fcpxml(session, out_path, project_name, fps)
        elif fmt == ExportFormat.PREMIERE_XML:
            export_premiere_xml(session, out_path, project_name, int(fps))
        elif fmt == ExportFormat.EDL:
            export_edl(session, out_path, project_name, fps)

        exported.append(out_path)

    return exported
