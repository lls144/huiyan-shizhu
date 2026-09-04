"""One restrained dark theme inspired by modern desktop developer tools."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtGui import QFontDatabase


def load_ui_fonts() -> None:
    """Make Windows UI fonts available even under Qt's offscreen platform."""

    windows_dir = os.environ.get("WINDIR")
    if not windows_dir:
        return
    font_dir = Path(windows_dir) / "Fonts"
    for name in ("msyh.ttc", "msyhbd.ttc", "segoeui.ttf", "segoeuib.ttf"):
        path = font_dir / name
        if path.exists():
            QFontDatabase.addApplicationFont(str(path))

APP_STYLE = """
QWidget {
    color: #d9dce5;
    background: #0e1014;
    font-family: "Microsoft YaHei UI";
    font-size: 13px;
}
QMainWindow { background: #0e1014; }
QFrame#card {
    background: #161920;
    border: 1px solid #262b35;
    border-radius: 10px;
}
QLabel#title { font-size: 20px; font-weight: 650; color: #f3f4f7; }
QLabel#subtitle { color: #858c9b; }
QLabel#sectionTitle { font-size: 12px; font-weight: 650; color: #aeb4c0; }
QLabel#metricValue { font-family: "Consolas"; color: #f2f3f7; }
QLabel#video {
    background: #090b0e;
    border: 1px solid #262b35;
    border-radius: 10px;
    color: #626977;
}
QLabel#stateChip {
    background: #222735;
    border: 1px solid #333a49;
    border-radius: 9px;
    padding: 4px 10px;
    font-weight: 650;
}
QPushButton {
    background: #20242d;
    border: 1px solid #313744;
    border-radius: 7px;
    padding: 7px 13px;
    color: #e4e6ec;
}
QPushButton:hover { background: #292e39; border-color: #414959; }
QPushButton:pressed { background: #171a21; }
QPushButton:disabled { color: #666d79; background: #171a20; border-color: #22262e; }
QPushButton#primary { background: #6172e8; border-color: #7181ef; color: white; }
QPushButton#primary:hover { background: #7181ef; }
QListWidget {
    background: transparent;
    border: none;
    outline: none;
    color: #cfd3dd;
}
QListWidget::item { padding: 5px 4px; border-bottom: 1px solid #20242c; }
QSplitter::handle { background: transparent; width: 8px; }
QScrollBar:vertical { background: transparent; width: 8px; }
QScrollBar::handle:vertical { background: #343a46; border-radius: 4px; min-height: 24px; }
"""
