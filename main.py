#!/usr/bin/env python3
"""
asynk - Multi-Track Audio/Video Synchronization Tool

Launch the desktop application.
"""

import sys
import logging
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from asynk.ui.main_window import MainWindow


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    app = QApplication(sys.argv)
    app.setApplicationName("asynk")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("asynk")

    # Default font matching the design system
    font = QFont("Segoe UI", 10)
    font.setStyleHint(QFont.SansSerif)
    font.setHintingPreference(QFont.PreferFullHinting)
    app.setFont(font)

    # Force dark window frame on Windows
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "windows:darkmode=2")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
