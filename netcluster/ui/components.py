"""
NetCluster UI Components - Reusable enterprise-grade widgets
"""
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QFrame, QVBoxLayout,
    QSizeGrip, QScrollArea, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor

from netcluster.ui.theme import (
    BG_INPUT, BORDER_SUBTLE, ACCENT_CYAN, DANGER_RED, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    get_danger_button_style, get_secondary_button_style, FONT_UI
)


class TitleBar(QWidget):
    """Enterprise-style title bar with window controls"""
    close_clicked = pyqtSignal()
    minimize_clicked = pyqtSignal()
    maximize_clicked = pyqtSignal()

    def __init__(self, title="NetCluster", show_minimize=True, show_maximize=True, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setStyleSheet(f"""
            TitleBar {{
                background: {BG_INPUT};
                border-bottom: 1px solid {BORDER_SUBTLE};
            }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 8, 0)
        layout.setSpacing(8)
        # Title
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {TEXT_PRIMARY};")
        layout.addWidget(self.title_label)
        layout.addStretch()
        # Window controls
        if show_minimize:
            min_btn = QPushButton("─")
            min_btn.setFixedSize(36, 28)
            min_btn.setStyleSheet(get_secondary_button_style() + " QPushButton { padding: 0; font-size: 14px; }")
            min_btn.setCursor(Qt.PointingHandCursor)
            min_btn.clicked.connect(self.minimize_clicked.emit)
            min_btn.setToolTip("Minimize")
            layout.addWidget(min_btn)
        if show_maximize:
            max_btn = QPushButton("□")
            max_btn.setFixedSize(36, 28)
            max_btn.setStyleSheet(get_secondary_button_style() + " QPushButton { padding: 0; font-size: 12px; }")
            max_btn.setCursor(Qt.PointingHandCursor)
            max_btn.clicked.connect(self.maximize_clicked.emit)
            max_btn.setToolTip("Maximize")
            layout.addWidget(max_btn)
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(36, 28)
        close_btn.setStyleSheet(get_danger_button_style() + " QPushButton { padding: 0; font-size: 14px; min-width: 36px; }")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.close_clicked.emit)
        close_btn.setToolTip("Close")
        layout.addWidget(close_btn)

    def set_title(self, title: str):
        self.title_label.setText(title)


class StatusBar(QWidget):
    """Enterprise-style status bar at bottom of window"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(28)
        self.setStyleSheet(f"""
            StatusBar {{
                background: {BG_INPUT};
                border-top: 1px solid {BORDER_SUBTLE};
            }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 4, 16, 4)
        layout.setSpacing(16)
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet(f"font-size: 12px; color: {TEXT_SECONDARY};")
        layout.addWidget(self.status_label)
        layout.addStretch()
        self.version_label = QLabel("v1.0")
        self.version_label.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED};")
        layout.addWidget(self.version_label)

    def set_status(self, text: str):
        self.status_label.setText(text)

    def set_version(self, text: str):
        self.version_label.setText(text)


class CollapsibleGroupBox(QFrame):
    """GroupBox that can collapse/expand its content"""
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setObjectName("CollapsibleGroupBox")
        self._collapsed = False
        self._content = None
        self.setStyleSheet(f"""
            #CollapsibleGroupBox {{
                background: {BG_INPUT};
                border: 1px solid {BORDER_SUBTLE};
                border-radius: 10px;
                padding: 0;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.header = QPushButton(f"▼ {title}")
        self.header.setCheckable(True)
        self.header.setChecked(True)
        self.header.setStyleSheet(f"""
            QPushButton {{
                text-align: left;
                padding: 12px 16px;
                font-size: 14px;
                font-weight: 600;
                color: {ACCENT_CYAN};
                background: transparent;
                border: none;
            }}
            QPushButton:hover {{
                background: rgba(0,212,255,0.08);
            }}
        """)
        self.header.clicked.connect(self._toggle)
        layout.addWidget(self.header)
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(16, 0, 16, 16)
        layout.addWidget(self.content_widget)

    def _toggle(self):
        self._collapsed = not self._collapsed
        self.content_widget.setVisible(not self._collapsed)
        title = self.header.text().lstrip("▼▶ ")
        self.header.setText(("▶ " if self._collapsed else "▼ ") + title)

    def set_title(self, title: str):
        prefix = "▶ " if self._collapsed else "▼ "
        self.header.setText(prefix + title)

    def add_content(self, widget):
        self.content_layout.addWidget(widget)
