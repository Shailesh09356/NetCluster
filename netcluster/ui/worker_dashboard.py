"""
Workers Dashboard - Live execution logs for connected workers
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QFrame, QScrollArea,
    QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from netcluster.ui.theme import (
    BG_CARD, BG_INPUT, BG_TERMINAL, ACCENT_CYAN, SUCCESS_GREEN, DANGER_RED,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, BORDER_SUBTLE, TEXT_TERMINAL,
    get_groupbox_style, get_terminal_style, FONT_UI, FONT_MONO
)


class WorkerLogCard(QFrame):
    """Card widget displaying a single worker's logs"""
    
    def __init__(self, worker_name: str, worker_ip: str, parent=None):
        super().__init__(parent)
        self.worker_name = worker_name
        self.worker_ip = worker_ip
        self.is_connected = True
        self.task_count = 0
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the card UI"""
        self.setStyleSheet(f"""
            QFrame {{
                background: {BG_CARD};
                border: 2px solid {BORDER_SUBTLE};
                border-radius: 12px;
                padding: 0px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header row
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)
        
        # Worker name
        name_label = QLabel(self.worker_name)
        name_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 600;
            color: {TEXT_PRIMARY};
            font-family: {FONT_UI};
        """)
        header_layout.addWidget(name_label)
        
        header_layout.addStretch()
        
        # Status indicator
        self.status_indicator = QLabel("●")
        self.status_indicator.setStyleSheet(f"""
            font-size: 14px;
            color: {SUCCESS_GREEN};
        """)
        self.status_indicator.setToolTip("Connected")
        header_layout.addWidget(self.status_indicator)
        
        layout.addLayout(header_layout)
        
        # Info row
        info_layout = QHBoxLayout()
        info_layout.setSpacing(16)
        
        ip_label = QLabel(f"IP: <span style='color:{TEXT_SECONDARY}; font-family:{FONT_MONO};'>{self.worker_ip}</span>")
        ip_label.setStyleSheet(f"font-size: 12px; color: {TEXT_SECONDARY};")
        info_layout.addWidget(ip_label)
        
        self.task_count_label = QLabel(f"Tasks: <span style='color:{ACCENT_CYAN};'>0</span>")
        self.task_count_label.setStyleSheet(f"font-size: 12px; color: {TEXT_SECONDARY};")
        info_layout.addWidget(self.task_count_label)
        
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
        # Terminal area
        self.log_terminal = QTextEdit()
        self.log_terminal.setReadOnly(True)
        self.log_terminal.setStyleSheet(get_terminal_style(TEXT_TERMINAL, 11))
        self.log_terminal.setMinimumHeight(200)
        self.log_terminal.setMaximumHeight(300)
        layout.addWidget(self.log_terminal)
    
    def append_log(self, message: str):
        """Append log message to terminal"""
        self.log_terminal.append(message)
        # Auto-scroll to bottom
        scrollbar = self.log_terminal.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def set_connected(self, connected: bool):
        """Update connection status"""
        self.is_connected = connected
        if connected:
            self.status_indicator.setStyleSheet(f"""
                font-size: 14px;
                color: {SUCCESS_GREEN};
            """)
            self.status_indicator.setToolTip("Connected")
        else:
            self.status_indicator.setStyleSheet(f"""
                font-size: 14px;
                color: {DANGER_RED};
            """)
            self.status_indicator.setToolTip("Disconnected")
    
    def set_task_count(self, count: int):
        """Update task count"""
        self.task_count = count
        self.task_count_label.setText(f"Tasks: <span style='color:{ACCENT_CYAN};'>{count}</span>")


class WorkersDashboardPage(QWidget):
    """Workers Dashboard page with live worker logs"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker_cards: dict = {}  # worker_name -> WorkerLogCard
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the dashboard page UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Title
        title = QLabel("Workers Dashboard - Live Execution Logs")
        title.setStyleSheet(f"""
            font-size: 20px;
            font-weight: 700;
            color: {ACCENT_CYAN};
            font-family: {FONT_UI};
        """)
        layout.addWidget(title)
        
        # Scroll area for worker cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Container widget for grid
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(container)
        self.grid_layout.setSpacing(16)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll.setWidget(container)
        layout.addWidget(scroll)
        
        # Store reference to container for adding cards
        self.container = container
    
    def add_worker_card(self, worker_name: str, worker_ip: str):
        """Add a new worker card"""
        if worker_name in self.worker_cards:
            # Worker already exists, just update status
            self.worker_cards[worker_name].set_connected(True)
            return
        
        card = WorkerLogCard(worker_name, worker_ip)
        self.worker_cards[worker_name] = card
        
        # Add to grid (2 columns)
        row = len(self.worker_cards) // 2
        col = len(self.worker_cards) % 2
        self.grid_layout.addWidget(card, row, col)
        
        # Add welcome message
        card.append_log(f"[{worker_name}] Connected from {worker_ip}")
    
    def remove_worker_card(self, worker_name: str):
        """Remove worker card (mark as disconnected)"""
        if worker_name in self.worker_cards:
            self.worker_cards[worker_name].set_connected(False)
            self.worker_cards[worker_name].append_log(f"[{worker_name}] Disconnected")
    
    def append_worker_log(self, worker_name: str, message: str):
        """Append log message to worker card"""
        if worker_name in self.worker_cards:
            self.worker_cards[worker_name].append_log(message)
    
    def update_worker_task_count(self, worker_name: str, task_count: int):
        """Update task count for worker"""
        if worker_name in self.worker_cards:
            self.worker_cards[worker_name].set_task_count(task_count)
    
    def get_all_worker_names(self):
        """Get all worker names"""
        return list(self.worker_cards.keys())
