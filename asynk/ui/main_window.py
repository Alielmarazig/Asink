"""
asynk main window.

Dark cinematic UI with purple/coral accent system,
waveform alignment panel, stat cards, and full sync workflow.
"""

import sys
import logging
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTableWidget, QTableWidgetItem,
    QProgressBar, QComboBox, QStatusBar, QFrame,
    QHeaderView, QMessageBox, QSpinBox, QAbstractItemView, QSizePolicy,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QAction, QColor, QDragEnterEvent, QDropEvent, QFont

from ..core.sync_engine import SyncEngine, SyncSession
from ..core.media_handler import (
    probe_file, MediaInfo, is_supported, SUPPORTED_EXTENSIONS
)
from ..exporters.export_manager import (
    ExportFormat, FORMAT_LABELS, export_session
)
from . import theme
from .stat_cards import StatsRow
from .waveform_widget import WaveformWidget

logger = logging.getLogger(__name__)


# ── Sync worker thread ──

class SyncWorker(QThread):
    progress = Signal(int, int, str)
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, clip_paths: list[Path], reference_index: int = 0):
        super().__init__()
        self.clip_paths = clip_paths
        self.reference_index = reference_index

    def run(self):
        try:
            engine = SyncEngine()
            session = engine.sync_clips(
                self.clip_paths,
                reference_index=self.reference_index,
                progress_callback=lambda c, t, m: self.progress.emit(c, t, m),
            )
            self.finished.emit(session)
        except Exception as e:
            self.error.emit(str(e))


# ── Table columns ──

COLUMNS = ["", "File", "Duration", "Codec", "Size", "Offset", "Confidence", "Status"]
COL_ICON = 0
COL_FILE = 1
COL_DURATION = 2
COL_CODEC = 3
COL_SIZE = 4
COL_OFFSET = 5
COL_CONF = 6
COL_STATUS = 7


# ── Main Window ──

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("asynk")
        self.setMinimumSize(940, 640)
        self.resize(1120, 740)

        self.clips: list[MediaInfo] = []
        self.clip_paths: list[Path] = []
        self.session: Optional[SyncSession] = None
        self.worker: Optional[SyncWorker] = None

        self.setAcceptDrops(True)
        self.setStyleSheet(theme.global_stylesheet())

        self._build_menu()
        self._build_ui()
        self._build_statusbar()

    # ────────────────────────────────────────────
    # Menu
    # ────────────────────────────────────────────

    def _build_menu(self):
        mb = self.menuBar()

        file_menu = mb.addMenu("File")
        self._add_action(file_menu, "Import Clips...", "Ctrl+O", self._on_import)
        self._add_action(file_menu, "Import Folder...", "", self._on_import_folder)
        file_menu.addSeparator()
        self._add_action(file_menu, "Export Timeline...", "Ctrl+E", self._on_export)
        file_menu.addSeparator()
        self._add_action(file_menu, "Quit", "Ctrl+Q", self.close)

        edit_menu = mb.addMenu("Edit")
        self._add_action(edit_menu, "Clear All Clips", "", self._on_clear)
        self._add_action(edit_menu, "Remove Selected", "Delete", self._on_remove_selected)

        mb.addMenu("View")
        mb.addMenu("Help")

    def _add_action(self, menu, text, shortcut, slot):
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(shortcut)
        action.triggered.connect(slot)
        menu.addAction(action)

    # ────────────────────────────────────────────
    # UI
    # ────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Toolbar ──
        toolbar = QFrame()
        toolbar.setStyleSheet(f"""
            QFrame {{
                background: {theme.BG_MID};
                border-bottom: 1px solid {theme.BORDER_SUBTLE};
            }}
        """)
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(16, 8, 16, 8)
        tb_layout.setSpacing(10)

        self.btn_import = QPushButton("Import")
        self.btn_import.clicked.connect(self._on_import)
        tb_layout.addWidget(self.btn_import)

        self._add_separator(tb_layout)

        ref_label = QLabel("Reference")
        ref_label.setObjectName("dimLabel")
        tb_layout.addWidget(ref_label)

        self.ref_spinner = QSpinBox()
        self.ref_spinner.setMinimum(1)
        self.ref_spinner.setMaximum(1)
        self.ref_spinner.setFixedWidth(52)
        tb_layout.addWidget(self.ref_spinner)

        self._add_separator(tb_layout)

        self.btn_sync = QPushButton("Sync")
        self.btn_sync.setObjectName("syncBtn")
        self.btn_sync.setEnabled(False)
        self.btn_sync.clicked.connect(self._on_sync)
        tb_layout.addWidget(self.btn_sync)

        tb_layout.addStretch()

        self.btn_export = QPushButton("Export")
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self._on_export)
        tb_layout.addWidget(self.btn_export)

        root.addWidget(toolbar)

        # ── Content area ──
        content = QWidget()
        content.setStyleSheet(f"background: {theme.BG_DARK};")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.setSpacing(16)

        # Stats row
        self.stats_row = StatsRow()
        cl.addWidget(self.stats_row)

        # Drop zone (hidden when clips exist)
        self.drop_zone = QLabel("Drop video and audio files here, or click Import")
        self.drop_zone.setAlignment(Qt.AlignCenter)
        self.drop_zone.setMinimumHeight(80)
        self.drop_zone.setStyleSheet(f"""
            QLabel {{
                border: 2px dashed {theme.TEXT_LABEL};
                border-radius: 10px;
                padding: 24px;
                color: {theme.TEXT_DIM};
                font-size: 13px;
                background: {theme.BG_CARD};
            }}
        """)
        cl.addWidget(self.drop_zone)

        # Clip table
        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setVisible(False)

        # Column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(COL_ICON, QHeaderView.Fixed)
        header.resizeSection(COL_ICON, 32)
        header.setSectionResizeMode(COL_FILE, QHeaderView.Stretch)
        header.setSectionResizeMode(COL_DURATION, QHeaderView.Fixed)
        header.resizeSection(COL_DURATION, 70)
        header.setSectionResizeMode(COL_CODEC, QHeaderView.Fixed)
        header.resizeSection(COL_CODEC, 130)
        header.setSectionResizeMode(COL_SIZE, QHeaderView.Fixed)
        header.resizeSection(COL_SIZE, 70)
        header.setSectionResizeMode(COL_OFFSET, QHeaderView.Fixed)
        header.resizeSection(COL_OFFSET, 80)
        header.setSectionResizeMode(COL_CONF, QHeaderView.Fixed)
        header.resizeSection(COL_CONF, 85)
        header.setSectionResizeMode(COL_STATUS, QHeaderView.Fixed)
        header.resizeSection(COL_STATUS, 70)

        cl.addWidget(self.table, stretch=1)

        # Waveform panel
        wf_header = QLabel("WAVEFORM ALIGNMENT")
        wf_header.setObjectName("sectionLabel")
        cl.addWidget(wf_header)

        self.waveform = WaveformWidget()
        self.waveform.setStyleSheet(f"""
            WaveformWidget {{
                background: {theme.BG_CARD};
                border: 1px solid {theme.BORDER_SUBTLE};
                border-radius: 10px;
            }}
        """)
        cl.addWidget(self.waveform)

        # Bottom export bar
        bottom = QHBoxLayout()
        bottom.setSpacing(12)

        fmt_label = QLabel("FORMAT")
        fmt_label.setObjectName("sectionLabel")
        bottom.addWidget(fmt_label)

        self.format_combo = QComboBox()
        self.format_combo.addItem("All formats", ExportFormat.ALL)
        for fmt, label in FORMAT_LABELS.items():
            self.format_combo.addItem(label, fmt)
        bottom.addWidget(self.format_combo)

        fps_label = QLabel("FPS")
        fps_label.setObjectName("sectionLabel")
        bottom.addWidget(fps_label)

        self.fps_combo = QComboBox()
        for fps_val in ["23.976", "24", "25", "29.97", "30", "50", "59.94", "60"]:
            self.fps_combo.addItem(fps_val)
        self.fps_combo.setCurrentText("24")
        bottom.addWidget(self.fps_combo)

        bottom.addStretch()

        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.progress.setFixedHeight(6)
        self.progress.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        bottom.addWidget(self.progress, stretch=2)

        self.progress_label = QLabel("")
        self.progress_label.setObjectName("dimLabel")
        bottom.addWidget(self.progress_label)

        cl.addLayout(bottom)

        root.addWidget(content, stretch=1)

    def _build_statusbar(self):
        sb = QStatusBar()
        self.setStatusBar(sb)

        self.status_left = QLabel("Ready")
        self.status_left.setStyleSheet(f"color: {theme.TEXT_LABEL}; font-size: 11px;")
        sb.addWidget(self.status_left, 1)

        version_label = QLabel("v0.1.0")
        version_label.setStyleSheet(f"color: {theme.TEXT_LABEL}; font-size: 11px;")
        sb.addPermanentWidget(version_label)

    def _add_separator(self, layout):
        sep = QFrame()
        sep.setFixedSize(1, 24)
        sep.setStyleSheet(f"background: {theme.BORDER_LIGHT};")
        layout.addWidget(sep)

    # ────────────────────────────────────────────
    # Drag and drop
    # ────────────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.drop_zone.setStyleSheet(f"""
                QLabel {{
                    border: 2px dashed {theme.PURPLE};
                    border-radius: 10px;
                    padding: 24px;
                    color: {theme.PURPLE};
                    font-size: 13px;
                    background: {theme.PURPLE_BG};
                }}
            """)

    def dragLeaveEvent(self, event):
        self._reset_drop_zone_style()

    def dropEvent(self, event: QDropEvent):
        self._reset_drop_zone_style()
        urls = event.mimeData().urls()
        paths = []
        for url in urls:
            p = Path(url.toLocalFile())
            if p.is_file() and is_supported(p):
                paths.append(p)
            elif p.is_dir():
                for f in sorted(p.iterdir()):
                    if f.is_file() and is_supported(f):
                        paths.append(f)
        if paths:
            self._add_clips(paths)

    def _reset_drop_zone_style(self):
        self.drop_zone.setStyleSheet(f"""
            QLabel {{
                border: 2px dashed {theme.TEXT_LABEL};
                border-radius: 10px;
                padding: 24px;
                color: {theme.TEXT_DIM};
                font-size: 13px;
                background: {theme.BG_CARD};
            }}
        """)

    # ────────────────────────────────────────────
    # Clip management
    # ────────────────────────────────────────────

    def _add_clips(self, paths: list[Path]):
        existing = {c.path for c in self.clips}

        for path in paths:
            if path in existing:
                continue
            try:
                info = probe_file(path)
                self.clips.append(info)
                self.clip_paths.append(path)
                existing.add(path)
            except Exception as e:
                logger.warning(f"Cannot import {path.name}: {e}")

        self._refresh_table()
        self._update_clip_stats()
        self.ref_spinner.setMaximum(max(len(self.clips), 1))
        self.btn_sync.setEnabled(len(self.clips) >= 2)

        # Toggle drop zone vs table
        has_clips = len(self.clips) > 0
        self.drop_zone.setVisible(not has_clips)
        self.table.setVisible(has_clips)

        self.status_left.setText(f"{len(self.clips)} clip(s) loaded")

    def _refresh_table(self):
        self.table.setRowCount(len(self.clips))

        for row, info in enumerate(self.clips):
            self.table.setRowHeight(row, 36)

            # Row number
            num_item = QTableWidgetItem(str(row + 1))
            num_item.setTextAlignment(Qt.AlignCenter)
            num_item.setForeground(QColor(theme.TEXT_DIM))
            self.table.setItem(row, COL_ICON, num_item)

            # File name
            name_item = QTableWidgetItem(info.filename)
            name_item.setForeground(QColor(theme.TEXT_PRIMARY))
            font = name_item.font()
            font.setWeight(QFont.DemiBold)
            name_item.setFont(font)
            self.table.setItem(row, COL_FILE, name_item)

            # Duration
            dur = info.duration_seconds
            m, s = divmod(int(dur), 60)
            h_val, m = divmod(m, 60)
            dur_str = f"{m:02d}:{s:02d}" if h_val == 0 else f"{h_val}:{m:02d}:{s:02d}"
            dur_item = QTableWidgetItem(dur_str)
            dur_item.setForeground(QColor(theme.TEXT_MUTED))
            dur_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, COL_DURATION, dur_item)

            # Codec
            if info.has_video and info.video_codec:
                codec = f"{info.video_codec}"
                if info.width and info.height:
                    codec += f" {info.width}x{info.height}"
            elif info.audio_codec:
                codec = f"{info.audio_codec}"
                if info.sample_rate:
                    codec += f" {info.sample_rate}Hz"
            else:
                codec = "---"
            codec_item = QTableWidgetItem(codec)
            codec_item.setForeground(QColor(theme.TEXT_MUTED))
            self.table.setItem(row, COL_CODEC, codec_item)

            # Size
            if info.file_size_mb >= 1024:
                size_str = f"{info.file_size_mb / 1024:.1f} GB"
            elif info.file_size_mb >= 1:
                size_str = f"{info.file_size_mb:.0f} MB"
            else:
                size_str = f"{info.file_size_mb * 1024:.0f} KB"
            size_item = QTableWidgetItem(size_str)
            size_item.setForeground(QColor(theme.TEXT_MUTED))
            size_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, COL_SIZE, size_item)

            # Offset, Confidence, Status (filled after sync)
            for col in [COL_OFFSET, COL_CONF, COL_STATUS]:
                placeholder = QTableWidgetItem("---" if col != COL_STATUS else "Pending")
                placeholder.setForeground(QColor(theme.TEXT_LABEL))
                placeholder.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, placeholder)

    def _update_clip_stats(self):
        total_dur = sum(c.duration_seconds for c in self.clips)
        self.stats_row.update_stats(
            clip_count=len(self.clips),
            total_duration_sec=total_dur,
        )

    # ────────────────────────────────────────────
    # Actions
    # ────────────────────────────────────────────

    def _on_import(self):
        exts = " ".join(f"*{e}" for e in sorted(SUPPORTED_EXTENSIONS))
        files, _ = QFileDialog.getOpenFileNames(
            self, "Import Media Files", "",
            f"Media Files ({exts});;All Files (*)",
        )
        if files:
            self._add_clips([Path(f) for f in files])

    def _on_import_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Import Folder")
        if folder:
            p = Path(folder)
            files = [f for f in sorted(p.iterdir()) if f.is_file() and is_supported(f)]
            if files:
                self._add_clips(files)
            else:
                self.status_left.setText("No supported media files found in folder")

    def _on_clear(self):
        self.clips.clear()
        self.clip_paths.clear()
        self.session = None
        self.table.setRowCount(0)
        self.table.setVisible(False)
        self.drop_zone.setVisible(True)
        self.btn_sync.setEnabled(False)
        self.btn_export.setEnabled(False)
        self.progress.setValue(0)
        self.progress_label.setText("")
        self.ref_spinner.setMaximum(1)
        self.stats_row.reset()
        self.waveform.set_tracks([])
        self.status_left.setText("All clips cleared")

    def _on_remove_selected(self):
        rows = sorted(
            set(idx.row() for idx in self.table.selectedIndexes()),
            reverse=True,
        )
        for row in rows:
            if 0 <= row < len(self.clips):
                self.clips.pop(row)
                self.clip_paths.pop(row)

        self._refresh_table()
        self._update_clip_stats()
        self.ref_spinner.setMaximum(max(len(self.clips), 1))
        self.btn_sync.setEnabled(len(self.clips) >= 2)

        if not self.clips:
            self.table.setVisible(False)
            self.drop_zone.setVisible(True)

    def _on_sync(self):
        if len(self.clips) < 2:
            return

        ref_idx = self.ref_spinner.value() - 1
        self.btn_sync.setEnabled(False)
        self.btn_import.setEnabled(False)
        self.btn_export.setEnabled(False)
        self.progress_label.setText("Starting sync...")
        self.progress_label.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 11px;")

        self.worker = SyncWorker(list(self.clip_paths), ref_idx)
        self.worker.progress.connect(self._on_sync_progress)
        self.worker.finished.connect(self._on_sync_finished)
        self.worker.error.connect(self._on_sync_error)
        self.worker.start()

    def _on_sync_progress(self, current: int, total: int, message: str):
        pct = int((current / max(total, 1)) * 100)
        self.progress.setValue(pct)
        self.progress_label.setText(message)
        self.status_left.setText(message)

    def _on_sync_finished(self, session: SyncSession):
        self.session = session
        self.btn_sync.setEnabled(True)
        self.btn_import.setEnabled(True)
        self.btn_export.setEnabled(True)
        self.progress.setValue(100)
        self.progress_label.setText("Sync complete")
        self.progress_label.setStyleSheet(f"color: {theme.GREEN}; font-size: 11px;")

        ref_idx = self.ref_spinner.value() - 1
        confidences = []
        waveform_tracks = []

        for i, result in enumerate(session.results):
            if i >= self.table.rowCount():
                break

            is_ref = (i == ref_idx)
            info = self.clips[i] if i < len(self.clips) else None
            is_audio = info and not info.has_video if info else False

            # Offset column
            if is_ref:
                off_text = "0.000s"
                off_color = theme.PURPLE
            elif result.success:
                off_text = f"{result.offset_seconds:+.3f}s"
                off_color = theme.TEXT_PRIMARY
            else:
                off_text = "FAILED"
                off_color = theme.RED

            off_item = QTableWidgetItem(off_text)
            off_item.setForeground(QColor(off_color))
            off_item.setTextAlignment(Qt.AlignCenter)
            font = off_item.font()
            font.setWeight(QFont.DemiBold)
            off_item.setFont(font)
            self.table.setItem(i, COL_OFFSET, off_item)

            # Confidence column
            conf_val = result.confidence * 100
            conf_text = f"{conf_val:.0f}%"
            if conf_val > 80:
                conf_color = theme.GREEN
            elif conf_val > 40:
                conf_color = theme.YELLOW
            else:
                conf_color = theme.RED
            conf_item = QTableWidgetItem(conf_text)
            conf_item.setForeground(QColor(conf_color))
            conf_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, COL_CONF, conf_item)

            # Status column
            if is_ref:
                status_text, status_color = "REF", theme.PURPLE
            elif result.success:
                status_text, status_color = "Synced", theme.GREEN
            elif result.error:
                status_text, status_color = "Error", theme.RED
            else:
                status_text, status_color = "Low", theme.YELLOW

            stat_item = QTableWidgetItem(status_text)
            stat_item.setForeground(QColor(status_color))
            stat_item.setTextAlignment(Qt.AlignCenter)
            font = stat_item.font()
            font.setWeight(QFont.DemiBold)
            stat_item.setFont(font)
            self.table.setItem(i, COL_STATUS, stat_item)

            # Highlight reference row background
            if is_ref:
                for col in range(self.table.columnCount()):
                    item = self.table.item(i, col)
                    if item:
                        item.setBackground(QColor(108, 92, 231, 10))

            if result.success:
                confidences.append(conf_val)

            # Waveform track data
            if info:
                waveform_tracks.append({
                    'name': info.filename[:12],
                    'offset_seconds': result.offset_seconds,
                    'duration_seconds': info.duration_seconds,
                    'is_reference': is_ref,
                    'is_audio_only': is_audio,
                    'confidence': result.confidence,
                    'waveform': None,
                })

        synced_total = sum(1 for r in session.results if r.success)
        avg_conf = sum(confidences) / len(confidences) if confidences else 0
        total_dur = sum(c.duration_seconds for c in self.clips)

        self.stats_row.update_stats(
            clip_count=len(self.clips),
            synced_count=synced_total,
            avg_confidence=avg_conf,
            total_duration_sec=total_dur,
        )

        self.waveform.set_tracks(waveform_tracks)
        self.waveform.start_animation()

        self.status_left.setText(f"{synced_total}/{len(session.results)} clips synced")

    def _on_sync_error(self, error_msg: str):
        self.btn_sync.setEnabled(True)
        self.btn_import.setEnabled(True)
        self.progress.setValue(0)
        self.progress_label.setText("Sync failed")
        self.progress_label.setStyleSheet(f"color: {theme.RED}; font-size: 11px;")
        QMessageBox.critical(self, "Sync Error", error_msg)

    def _on_export(self):
        if not self.session:
            QMessageBox.information(
                self, "No sync data",
                "Run a sync first before exporting.",
            )
            return

        output_dir = QFileDialog.getExistingDirectory(self, "Choose Export Folder")
        if not output_dir:
            return

        fmt = self.format_combo.currentData()
        fps = float(self.fps_combo.currentText())

        try:
            exported = export_session(
                self.session,
                Path(output_dir),
                format=fmt,
                project_name="asynk_Synced_Timeline",
                fps=fps,
            )

            file_list = "\n".join(f"  {p.name}" for p in exported)
            QMessageBox.information(
                self, "Export complete",
                f"Exported {len(exported)} file(s) to:\n"
                f"{output_dir}\n\n{file_list}",
            )
            self.status_left.setText(
                f"Exported {len(exported)} timeline(s) to {output_dir}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Export error", f"Export failed:\n{e}")
