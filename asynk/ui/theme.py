"""
asynk design system.

All colors, fonts, and reusable style constants live here.
Matches the dark cinematic UI mockup: deep charcoal base,
purple primary accent, coral for audio, green for success.
"""

# ── Base palette ──

BG_DARKEST = "#0a0a0f"
BG_DARK = "#0f0f14"
BG_MID = "#111118"
BG_CARD = "#15151e"
BG_INPUT = "#1a1a24"

TEXT_PRIMARY = "#e2e2ea"
TEXT_SECONDARY = "#c8c8d4"
TEXT_MUTED = "#8a8a98"
TEXT_DIM = "#6b6b78"
TEXT_HINT = "#5a5a6a"
TEXT_LABEL = "#4a4a58"

BORDER_SUBTLE = "rgba(255,255,255,0.04)"
BORDER_LIGHT = "rgba(255,255,255,0.06)"
BORDER_INPUT = "rgba(255,255,255,0.08)"
BORDER_HOVER = "rgba(255,255,255,0.12)"

# ── Accent colors ──

PURPLE = "#6c5ce7"
PURPLE_DARK = "#5541d8"
PURPLE_BG = "rgba(108,92,231,0.04)"
PURPLE_BG_HOVER = "rgba(108,92,231,0.08)"

CORAL = "#f0997b"
CORAL_BG = "rgba(240,153,123,0.06)"

GREEN = "#28c840"
GREEN_BG = "rgba(40,200,64,0.12)"

YELLOW = "#febc2e"
YELLOW_BG = "rgba(254,188,46,0.12)"

RED = "#ff5f57"
RED_BG = "rgba(255,95,87,0.12)"

# ── Traffic lights ──

LIGHT_CLOSE = "#ff5f57"
LIGHT_MINIMIZE = "#febc2e"
LIGHT_MAXIMIZE = "#28c840"

# ── Font ──

FONT_FAMILY = "'Segoe UI', 'SF Pro Display', -apple-system, system-ui, sans-serif"
FONT_MONO = "'SF Mono', 'Cascadia Code', 'JetBrains Mono', 'Consolas', monospace"


def global_stylesheet() -> str:
    """Full application stylesheet."""
    return f"""
        * {{
            font-family: {FONT_FAMILY};
        }}

        QMainWindow {{
            background: {BG_DARK};
            color: {TEXT_PRIMARY};
        }}

        /* ── Menu bar ── */
        QMenuBar {{
            background: {BG_DARKEST};
            color: {TEXT_DIM};
            border-bottom: 1px solid {BORDER_SUBTLE};
            padding: 2px 0;
            font-size: 12px;
        }}
        QMenuBar::item {{
            padding: 4px 10px;
            background: transparent;
        }}
        QMenuBar::item:selected {{
            background: {BG_INPUT};
            color: {TEXT_PRIMARY};
            border-radius: 4px;
        }}
        QMenu {{
            background: {BG_MID};
            color: {TEXT_SECONDARY};
            border: 1px solid {BORDER_INPUT};
            border-radius: 6px;
            padding: 4px;
        }}
        QMenu::item {{
            padding: 6px 24px 6px 12px;
            border-radius: 4px;
        }}
        QMenu::item:selected {{
            background: {BG_INPUT};
            color: {TEXT_PRIMARY};
        }}
        QMenu::separator {{
            height: 1px;
            background: {BORDER_LIGHT};
            margin: 4px 8px;
        }}

        /* ── Toolbar ── */
        QToolBar {{
            background: {BG_MID};
            border: none;
            border-bottom: 1px solid {BORDER_SUBTLE};
            spacing: 6px;
            padding: 6px 12px;
        }}

        /* ── Buttons ── */
        QPushButton {{
            background: {BG_INPUT};
            color: {TEXT_SECONDARY};
            border: 1px solid {BORDER_INPUT};
            border-radius: 6px;
            padding: 7px 16px;
            font-size: 12px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background: {BG_CARD};
            border-color: {BORDER_HOVER};
            color: {TEXT_PRIMARY};
        }}
        QPushButton:pressed {{
            background: {BG_MID};
        }}
        QPushButton:disabled {{
            background: {BG_MID};
            color: {TEXT_LABEL};
            border-color: {BORDER_SUBTLE};
        }}
        QPushButton#syncBtn {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {PURPLE}, stop:1 {PURPLE_DARK});
            color: #ffffff;
            border: none;
            padding: 7px 28px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }}
        QPushButton#syncBtn:hover {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #7d6ef0, stop:1 {PURPLE});
        }}
        QPushButton#syncBtn:disabled {{
            background: {BG_INPUT};
            color: {TEXT_LABEL};
        }}

        /* ── Table ── */
        QTableWidget {{
            background: {BG_CARD};
            alternate-background-color: {BG_MID};
            color: {TEXT_PRIMARY};
            gridline-color: {BORDER_SUBTLE};
            border: 1px solid {BORDER_SUBTLE};
            border-radius: 10px;
            font-size: 12px;
            selection-background-color: {PURPLE_BG_HOVER};
            selection-color: {TEXT_PRIMARY};
        }}
        QTableWidget::item {{
            padding: 4px 8px;
            border-bottom: 1px solid {BORDER_SUBTLE};
        }}
        QHeaderView::section {{
            background: {BG_MID};
            color: {TEXT_LABEL};
            border: none;
            border-bottom: 1px solid {BORDER_SUBTLE};
            border-right: 1px solid {BORDER_SUBTLE};
            padding: 8px 8px;
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
        }}
        QHeaderView::section:last {{
            border-right: none;
        }}

        /* ── Scroll bars ── */
        QScrollBar:vertical {{
            background: {BG_CARD};
            width: 8px;
            border-radius: 4px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {BG_INPUT};
            border-radius: 4px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {TEXT_LABEL};
        }}
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        QScrollBar:horizontal {{
            background: {BG_CARD};
            height: 8px;
            border-radius: 4px;
        }}
        QScrollBar::handle:horizontal {{
            background: {BG_INPUT};
            border-radius: 4px;
            min-width: 30px;
        }}

        /* ── Combo box ── */
        QComboBox {{
            background: {BG_INPUT};
            color: {TEXT_SECONDARY};
            border: 1px solid {BORDER_INPUT};
            border-radius: 6px;
            padding: 5px 28px 5px 10px;
            font-size: 11px;
            min-width: 80px;
        }}
        QComboBox:hover {{
            border-color: {BORDER_HOVER};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid {TEXT_DIM};
            margin-right: 8px;
        }}
        QComboBox QAbstractItemView {{
            background: {BG_MID};
            color: {TEXT_SECONDARY};
            border: 1px solid {BORDER_INPUT};
            selection-background-color: {BG_INPUT};
            selection-color: {TEXT_PRIMARY};
            border-radius: 6px;
            padding: 4px;
        }}

        /* ── Spin box ── */
        QSpinBox {{
            background: {BG_INPUT};
            color: {TEXT_PRIMARY};
            border: 1px solid {BORDER_INPUT};
            border-radius: 6px;
            padding: 4px 8px;
            font-size: 12px;
            min-width: 44px;
        }}
        QSpinBox::up-button, QSpinBox::down-button {{
            width: 0;
        }}

        /* ── Progress bar ── */
        QProgressBar {{
            background: {BG_INPUT};
            border: none;
            border-radius: 3px;
            height: 6px;
            text-align: center;
            color: transparent;
        }}
        QProgressBar::chunk {{
            border-radius: 3px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {PURPLE}, stop:1 {GREEN});
        }}

        /* ── Status bar ── */
        QStatusBar {{
            background: {BG_DARKEST};
            color: {TEXT_LABEL};
            font-size: 11px;
            border-top: 1px solid {BORDER_SUBTLE};
            padding: 2px 12px;
        }}

        /* ── Labels ── */
        QLabel {{
            color: {TEXT_PRIMARY};
        }}
        QLabel#dimLabel {{
            color: {TEXT_LABEL};
            font-size: 11px;
        }}
        QLabel#statValue {{
            font-size: 22px;
            font-weight: 600;
            color: {TEXT_PRIMARY};
        }}
        QLabel#statLabel {{
            font-size: 10px;
            font-weight: 700;
            color: {TEXT_HINT};
            letter-spacing: 0.8px;
        }}
        QLabel#statValuePurple {{
            font-size: 22px;
            font-weight: 600;
            color: {PURPLE};
        }}
        QLabel#statValueGreen {{
            font-size: 22px;
            font-weight: 600;
            color: {GREEN};
        }}
        QLabel#sectionLabel {{
            font-size: 10px;
            font-weight: 700;
            color: {TEXT_LABEL};
            letter-spacing: 0.8px;
        }}

        /* ── Group box ── */
        QGroupBox {{
            background: transparent;
            border: none;
            margin: 0;
            padding: 0;
        }}

        /* ── Splitter ── */
        QSplitter::handle {{
            background: {BORDER_SUBTLE};
            height: 1px;
        }}

        /* ── Tool tip ── */
        QToolTip {{
            background: {BG_INPUT};
            color: {TEXT_PRIMARY};
            border: 1px solid {BORDER_INPUT};
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 11px;
        }}
    """
