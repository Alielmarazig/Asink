"""
Waveform alignment visualization widget.

Draws a multi-track waveform display showing how clips
align after sync. Reference track highlighted in purple,
video tracks in gray, audio-only tracks in coral.
"""

import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, QRectF, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QLinearGradient
from pathlib import Path
from typing import Optional

from . import theme


class WaveformWidget(QWidget):
    """
    Multi-track waveform alignment display.

    Shows each clip as a horizontal waveform bar with position
    offset from the sync engine. Playhead scrubs across.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(160)
        self.setMaximumHeight(220)

        self.tracks: list[dict] = []
        self.playhead_pos: float = 0.35  # 0-1 normalized
        self.total_duration: float = 0.0

        # Animate playhead
        self._animating = False
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._tick_playhead)

        # Generate placeholder waveform data
        self._rng = np.random.default_rng(42)

    def set_tracks(self, track_data: list[dict]):
        """
        Set track data for display.

        Each dict: {
            'name': str,
            'offset_seconds': float,
            'duration_seconds': float,
            'is_reference': bool,
            'is_audio_only': bool,
            'confidence': float,
            'waveform': Optional[np.ndarray],  # normalized 0-1 peaks
        }
        """
        self.tracks = track_data

        if track_data:
            max_end = max(
                t['offset_seconds'] + t['duration_seconds']
                for t in track_data
            )
            min_start = min(t['offset_seconds'] for t in track_data)
            self.total_duration = max_end - min_start
        else:
            self.total_duration = 0.0

        self.update()

    def start_animation(self):
        """Start playhead scrub animation."""
        self.playhead_pos = 0.0
        self._animating = True
        self._anim_timer.start(30)

    def stop_animation(self):
        """Stop playhead animation."""
        self._animating = False
        self._anim_timer.stop()

    def _tick_playhead(self):
        self.playhead_pos += 0.003
        if self.playhead_pos > 1.0:
            self.playhead_pos = 0.0
        self.update()

    def _generate_waveform(self, length: int, seed: int) -> np.ndarray:
        """Generate a pseudo-random waveform envelope."""
        rng = np.random.default_rng(seed)
        raw = rng.random(length)
        # Smooth it
        kernel = np.ones(5) / 5
        smoothed = np.convolve(raw, kernel, mode='same')
        # Add some peaks
        peaks = rng.choice(length, size=length // 8, replace=False)
        smoothed[peaks] *= 1.6
        return np.clip(smoothed, 0.05, 1.0)

    def paintEvent(self, event):
        if not self.tracks:
            self._paint_empty(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        label_width = 64
        track_area_x = label_width + 8
        track_area_w = w - track_area_x - 16
        track_count = len(self.tracks)
        track_height = min(22, max(14, (h - 20) // max(track_count, 1)))
        track_gap = max(4, min(8, (h - track_count * track_height) // max(track_count, 1)))
        total_tracks_h = track_count * track_height + (track_count - 1) * track_gap
        start_y = max(8, (h - total_tracks_h) // 2)

        # Find offset range
        min_offset = min(t['offset_seconds'] for t in self.tracks)
        max_end = max(t['offset_seconds'] + t['duration_seconds'] for t in self.tracks)
        time_span = max_end - min_offset if max_end > min_offset else 1.0

        # Draw each track
        mono_font = QFont(theme.FONT_MONO.split(",")[0].strip("'"), 8)
        painter.setFont(mono_font)

        for i, track in enumerate(self.tracks):
            y = start_y + i * (track_height + track_gap)

            # Track label
            painter.setPen(QColor(theme.TEXT_DIM))
            name = track['name']
            if len(name) > 8:
                name = name[:7] + ".."
            painter.drawText(
                QRectF(4, y, label_width, track_height),
                Qt.AlignVCenter | Qt.AlignRight,
                name,
            )

            # Track background bar
            clip_x = track_area_x + ((track['offset_seconds'] - min_offset) / time_span) * track_area_w
            clip_w = (track['duration_seconds'] / time_span) * track_area_w

            if track.get('is_reference'):
                bg_color = QColor(108, 92, 231, 18)
                bar_color = QColor(theme.PURPLE)
            elif track.get('is_audio_only'):
                bg_color = QColor(240, 153, 123, 12)
                bar_color = QColor(theme.CORAL)
            else:
                bg_color = QColor(255, 255, 255, 8)
                bar_color = QColor(theme.TEXT_MUTED)

            painter.setPen(Qt.NoPen)
            painter.setBrush(bg_color)
            painter.drawRoundedRect(QRectF(clip_x, y, clip_w, track_height), 3, 3)

            # Waveform bars
            waveform = track.get('waveform')
            if waveform is None:
                waveform = self._generate_waveform(
                    int(clip_w / 3), seed=hash(track['name']) & 0xFFFFFF
                )

            num_bars = min(len(waveform), int(clip_w / 3))
            if num_bars < 2:
                continue

            bar_width = max(1.5, clip_w / num_bars * 0.55)
            bar_spacing = clip_w / num_bars

            opacity = 0.85 if track.get('is_reference') else 0.65
            bar_color.setAlphaF(opacity)
            painter.setBrush(bar_color)

            for j in range(num_bars):
                val = waveform[j % len(waveform)]
                bar_h = val * (track_height - 4)
                bx = clip_x + j * bar_spacing + (bar_spacing - bar_width) / 2
                by = y + (track_height - bar_h) / 2
                painter.drawRoundedRect(QRectF(bx, by, bar_width, bar_h), 1, 1)

        # Playhead
        ph_x = track_area_x + self.playhead_pos * track_area_w
        pen = QPen(QColor(theme.PURPLE))
        pen.setWidthF(1.5)
        painter.setPen(pen)
        painter.drawLine(
            int(ph_x), start_y - 4,
            int(ph_x), start_y + total_tracks_h + 4,
        )

        # Playhead triangle
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(theme.PURPLE))
        from PySide6.QtGui import QPolygonF
        from PySide6.QtCore import QPointF
        tri = QPolygonF([
            QPointF(ph_x - 4, start_y - 6),
            QPointF(ph_x + 4, start_y - 6),
            QPointF(ph_x, start_y - 1),
        ])
        painter.drawPolygon(tri)

        painter.end()

    def _paint_empty(self, event):
        """Paint placeholder when no tracks loaded."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.setPen(QColor(theme.TEXT_LABEL))
        font = QFont(theme.FONT_FAMILY.split(",")[0].strip("'"), 12)
        painter.setFont(font)
        painter.drawText(
            self.rect(), Qt.AlignCenter,
            "Waveform alignment will appear here after sync"
        )
        painter.end()

    def mousePressEvent(self, event):
        """Click to move playhead."""
        label_width = 72
        track_area_x = label_width
        track_area_w = self.width() - track_area_x - 16

        if event.position().x() >= track_area_x:
            self.playhead_pos = (event.position().x() - track_area_x) / track_area_w
            self.playhead_pos = max(0.0, min(1.0, self.playhead_pos))
            self.update()

    def mouseMoveEvent(self, event):
        """Drag to scrub playhead."""
        if event.buttons() & Qt.LeftButton:
            self.mousePressEvent(event)
