"""
Stat card widget.

Compact metric display card with a muted label and large value.
Used in the stats row at the top of the main window.
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from . import theme


class StatCard(QFrame):
    """Single stat metric card."""

    def __init__(self, label: str, value: str = "0", color: str = None, parent=None):
        super().__init__(parent)
        self._color = color or theme.TEXT_PRIMARY

        self.setStyleSheet(f"""
            StatCard {{
                background: {theme.BG_CARD};
                border: 1px solid {theme.BORDER_SUBTLE};
                border-radius: 10px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        self._label = QLabel(label.upper())
        self._label.setStyleSheet(f"""
            font-size: 10px;
            font-weight: 700;
            color: {theme.TEXT_HINT};
            letter-spacing: 0.8px;
        """)
        layout.addWidget(self._label)

        self._value = QLabel(value)
        self._value.setStyleSheet(f"""
            font-size: 22px;
            font-weight: 600;
            color: {self._color};
        """)
        layout.addWidget(self._value)

    def set_value(self, value: str):
        self._value.setText(value)

    def set_color(self, color: str):
        self._color = color
        self._value.setStyleSheet(f"""
            font-size: 22px;
            font-weight: 600;
            color: {self._color};
        """)


class StatsRow(QFrame):
    """Horizontal row of 4 stat cards."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent; border: none;")

        from PySide6.QtWidgets import QHBoxLayout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.clips_card = StatCard("Clips loaded", "0")
        self.synced_card = StatCard("Synced", "0", theme.GREEN)
        self.confidence_card = StatCard("Avg confidence", "--", theme.PURPLE)
        self.duration_card = StatCard("Total duration", "00:00")

        layout.addWidget(self.clips_card)
        layout.addWidget(self.synced_card)
        layout.addWidget(self.confidence_card)
        layout.addWidget(self.duration_card)

    def update_stats(
        self,
        clip_count: int = 0,
        synced_count: int = 0,
        avg_confidence: float = 0.0,
        total_duration_sec: float = 0.0,
    ):
        self.clips_card.set_value(str(clip_count))
        self.synced_card.set_value(str(synced_count))

        if avg_confidence > 0:
            self.confidence_card.set_value(f"{avg_confidence:.1f}%")
        else:
            self.confidence_card.set_value("--")

        m, s = divmod(int(total_duration_sec), 60)
        h, m = divmod(m, 60)
        if h > 0:
            self.duration_card.set_value(f"{h}:{m:02d}:{s:02d}")
        else:
            self.duration_card.set_value(f"{m:02d}:{s:02d}")

    def reset(self):
        self.update_stats()
