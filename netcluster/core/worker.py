import sys
import subprocess
import threading
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QLineEdit, QTextEdit, QGroupBox, QCheckBox, QFileDialog, QFrame, QScrollArea, QSpinBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from netcluster.network.connection import LogClient
from netcluster.core.worker_backend import WorkerBackend
import socket
from PyQt5.QtGui import QPalette, QColor
import os

from netcluster.ui.theme import (
    BG_CARD, BG_INPUT, BG_TERMINAL, ACCENT_CYAN, SUCCESS_GREEN, DANGER_RED, TEXT_PRIMARY, TEXT_SECONDARY,
    TEXT_MUTED, BORDER_SUBTLE, TEXT_TERMINAL, TEXT_LOG, get_primary_button_style, get_danger_button_style,
    get_secondary_button_style, get_groupbox_style, get_terminal_style, get_checkbox_switch_style,
    get_global_app_style, FONT_UI, FONT_MONO
)

os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_SCALE_FACTOR"] = "1"
os.environ["QT_SCREEN_SCALE_FACTORS"] = "1"


class WorkerNodeWindow(QMainWindow):
    log_signal = pyqtSignal(str)
    font_signal = pyqtSignal(int)
    attack_log_signal = pyqtSignal(str)   # Thread-safe: worker executor logs -> attack_terminal
    attack_result_signal = pyqtSignal(str) # Thread-safe: attack success/fail -> attack_terminal
    connection_status_signal = pyqtSignal(str, str)  # (state, extra_text) - safe status update

    def __init__(self):
        super().__init__()
        self.setWindowTitle("NetCluster - Worker Node")
        self.setGeometry(500, 250, 720, 620)
        self.setMinimumSize(640, 520)
        self.log_client = None
        # Create backend
        self.backend = WorkerBackend("Worker")
        self.setup_ui()

        def _append_log_main(log_line):
            if '[PIN_CHANGED]' in log_line:
                self.disconnect_from_master()
                self._set_status("disconnected_pin")
            elif log_line.startswith('[SETTINGS]'):
                self.apply_settings_from_log(log_line)
            else:
                self.log_terminal.append(log_line)

        self._append_log_main = _append_log_main
        self.log_signal.connect(self._append_log_main)
        self.font_signal.connect(self._set_font_size_main)
        # Wire attack log/result signals to attack_terminal
        self.attack_log_signal.connect(self._append_attack_log)
        self.attack_result_signal.connect(self._append_attack_log)
        # Wire backend callbacks
        self.backend.on_attack_log = lambda msg: self.attack_log_signal.emit(f"⏳ {msg}")
        self.backend.on_attack_result = lambda msg: self.attack_result_signal.emit(f"✔ {msg}")
        self.backend.on_task_received = lambda tid, ttype: self.attack_log_signal.emit(
            f"📥 Task received: {ttype} [{tid[:12]}]"
        )
        def _on_task_done(tid, ok):
            icon = "✅" if ok else "❌"
            status = "completed" if ok else "failed"
            self.attack_result_signal.emit(f"{icon} Task {status}: [{tid[:12]}]")
        self.backend.on_task_completed = _on_task_done
        # Wire connection status signal to GUI update slot
        self.connection_status_signal.connect(self._apply_connection_status)

    def _set_status(self, state):
        """Update status badge - connected, disconnected, connecting, error"""
        styles = {
            "connected": f"font-size: 14px; font-weight: 600; color: {SUCCESS_GREEN}; background: rgba(16,185,129,0.15); border: 1px solid {SUCCESS_GREEN}; border-radius: 20px; padding: 8px 16px;",
            "disconnected": f"font-size: 14px; font-weight: 600; color: {DANGER_RED}; background: rgba(239,68,68,0.12); border: 1px solid {DANGER_RED}; border-radius: 20px; padding: 8px 16px;",
            "connecting": f"font-size: 14px; font-weight: 600; color: #f59e0b; background: rgba(245,158,11,0.15); border: 1px solid #f59e0b; border-radius: 20px; padding: 8px 16px;",
            "disconnected_pin": f"font-size: 14px; font-weight: 600; color: {DANGER_RED}; background: rgba(239,68,68,0.12); border: 1px solid {DANGER_RED}; border-radius: 20px; padding: 8px 16px;",
            "enter_pin": f"font-size: 14px; font-weight: 600; color: {DANGER_RED}; background: rgba(239,68,68,0.12); border: 1px solid {DANGER_RED}; border-radius: 20px; padding: 8px 16px;",
            "cancelled": f"font-size: 14px; font-weight: 600; color: {DANGER_RED}; background: rgba(239,68,68,0.12); border: 1px solid {DANGER_RED}; border-radius: 20px; padding: 8px 16px;",
            "pin_incorrect": f"font-size: 14px; font-weight: 600; color: {DANGER_RED}; background: rgba(239,68,68,0.12); border: 1px solid {DANGER_RED}; border-radius: 20px; padding: 8px 16px;",
            "pin_failed": f"font-size: 14px; font-weight: 600; color: {DANGER_RED}; background: rgba(239,68,68,0.12); border: 1px solid {DANGER_RED}; border-radius: 20px; padding: 8px 16px;",
            "connection_failed": f"font-size: 14px; font-weight: 600; color: {DANGER_RED}; background: rgba(239,68,68,0.12); border: 1px solid {DANGER_RED}; border-radius: 20px; padding: 8px 16px;",
        }
        labels = {
            "connected": "● Connected to Master",
            "disconnected": "● Not Connected",
            "connecting": "● Connecting...",
            "disconnected_pin": "● Disconnected (PIN changed)",
            "enter_pin": "● Enter PIN",
            "cancelled": "● Connection cancelled",
            "pin_incorrect": "● PIN incorrect",
            "pin_failed": "● PIN check failed",
            "connection_failed": "● Connection failed",
        }
        self.status_label.setStyleSheet(styles.get(state, styles["disconnected"]))
        self.status_label.setText(labels.get(state, labels["disconnected"]))

    def setup_ui(self):
        central = QWidget()
        self.setStyleSheet(f"background-color: {BG_CARD}; font-family: {FONT_UI};")
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Connection panel - card style
        conn_card = QFrame()
        conn_card.setStyleSheet(f"background: {BG_INPUT}; border: 1px solid {BORDER_SUBTLE}; border-radius: 12px; padding: 16px;")
        conn_layout = QVBoxLayout(conn_card)
        conn_layout.setSpacing(12)

        # Top row: inputs and buttons
        top_row = QHBoxLayout()
        top_row.setSpacing(12)
        name_label = QLabel("Worker Name")
        name_label.setStyleSheet(f"font-size: 13px; font-weight: 500; color: {TEXT_SECONDARY};")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter worker name")
        self.name_input.setMinimumWidth(120)
        self.name_input.setMaximumWidth(180)
        self.name_input.setStyleSheet(f"background: {BG_TERMINAL}; color: {TEXT_PRIMARY}; border: 1px solid {BORDER_SUBTLE}; border-radius: 8px; padding: 8px 12px; font-family: {FONT_UI};")
        pin_label = QLabel("Master PIN")
        pin_label.setStyleSheet(f"font-size: 13px; font-weight: 500; color: {TEXT_SECONDARY};")
        self.pin_input = QLineEdit()
        self.pin_input.setPlaceholderText("Enter PIN")
        self.pin_input.setMinimumWidth(80)
        self.pin_input.setMaximumWidth(120)
        self.pin_input.setEchoMode(QLineEdit.Password)
        self.pin_input.setStyleSheet(f"background: {BG_TERMINAL}; color: {TEXT_PRIMARY}; border: 1px solid {BORDER_SUBTLE}; border-radius: 8px; padding: 8px 12px; font-family: {FONT_MONO};")
        
        cpu_label = QLabel("Ray CPUs")
        cpu_label.setStyleSheet(f"font-size: 13px; font-weight: 500; color: {TEXT_SECONDARY};")
        self.cpu_input = QSpinBox()
        self.cpu_input.setMinimum(0)
        self.cpu_input.setMaximum(256)
        self.cpu_input.setValue(0)
        self.cpu_input.setSpecialValueText("Auto")
        self.cpu_input.setStyleSheet(f"background: {BG_TERMINAL}; color: {TEXT_PRIMARY}; border: 1px solid {BORDER_SUBTLE}; border-radius: 8px; padding: 8px; font-family: {FONT_UI};")
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setStyleSheet(get_primary_button_style())
        self.connect_btn.setToolTip("Connect to Master Node")
        self.connect_btn.clicked.connect(self.connect_to_master)
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setStyleSheet(get_danger_button_style())
        self.disconnect_btn.setToolTip("Disconnect from Master Node")
        self.disconnect_btn.clicked.connect(self.disconnect_from_master)
        top_row.addWidget(name_label)
        top_row.addWidget(self.name_input)
        top_row.addWidget(pin_label)
        top_row.addWidget(self.pin_input)
        top_row.addWidget(cpu_label)
        top_row.addWidget(self.cpu_input)
        top_row.addWidget(self.connect_btn)
        top_row.addWidget(self.disconnect_btn)
        top_row.addStretch()
        back_btn = QPushButton("Back")
        back_btn.setStyleSheet(get_secondary_button_style())
        back_btn.setToolTip("Return to launcher")
        back_btn.clicked.connect(self.go_back)
        top_row.addWidget(back_btn)
        exit_btn = QPushButton("Exit")
        exit_btn.setStyleSheet(get_danger_button_style() + " QPushButton { padding: 8px 16px; }")
        exit_btn.setToolTip("Close application")
        exit_btn.clicked.connect(self.close)
        top_row.addWidget(exit_btn)
        conn_layout.addLayout(top_row)

        # Status row: pill badge + auto-reconnect switch + save
        status_row = QHBoxLayout()
        self.status_label = QLabel("● Not Connected")
        self._set_status("disconnected")
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        self.reconnect_toggle = QCheckBox("Auto-reconnect")
        self.reconnect_toggle.setStyleSheet(get_checkbox_switch_style())
        self.reconnect_toggle.setToolTip("Automatically reconnect if disconnected")
        status_row.addWidget(self.reconnect_toggle)
        save_btn = QPushButton("Save Logs")
        save_btn.setStyleSheet(get_secondary_button_style())
        save_btn.setToolTip("Save all logs to a file")
        save_btn.clicked.connect(self.save_logs)
        status_row.addWidget(save_btn)
        conn_layout.addLayout(status_row)

        main_layout.addWidget(conn_card)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background: {BORDER_SUBTLE}; max-height: 1px;")
        main_layout.addWidget(sep)

        # Attack Results terminal
        attack_group = QGroupBox("Attack Results")
        attack_group.setStyleSheet(get_groupbox_style(TEXT_TERMINAL, SUCCESS_GREEN))
        attack_layout = QVBoxLayout(attack_group)
        self.attack_terminal = QTextEdit()
        self.attack_terminal.setReadOnly(True)
        self.attack_terminal.setStyleSheet(get_terminal_style(TEXT_TERMINAL, 13))
        attack_layout.addWidget(self.attack_terminal)
        main_layout.addWidget(attack_group, stretch=2)

        # Master Node Logs terminal
        log_group = QGroupBox("Master Node Logs / Settings")
        log_group.setStyleSheet(get_groupbox_style(TEXT_LOG, "#f59e0b"))
        log_layout = QVBoxLayout(log_group)
        self.log_terminal = QTextEdit()
        self.log_terminal.setReadOnly(True)
        self.log_terminal.setStyleSheet(get_terminal_style(TEXT_LOG, 13))
        log_layout.addWidget(self.log_terminal)
        main_layout.addWidget(log_group, stretch=1)
        # Status bar
        status_bar = QFrame()
        status_bar.setFixedHeight(26)
        status_bar.setStyleSheet(f"background: {BG_INPUT}; border-top: 1px solid {BORDER_SUBTLE};")
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(16, 4, 16, 4)
        self.worker_status_text = QLabel("Ready")
        self.worker_status_text.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED};")
        status_layout.addWidget(self.worker_status_text)
        status_layout.addStretch()
        version_label = QLabel("NetCluster Worker v1.0")
        version_label.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED};")
        status_layout.addWidget(version_label)
        main_layout.addWidget(status_bar)
        self.setCentralWidget(central)

    def go_back(self):
        subprocess.Popen([sys.executable, "-m", "netcluster.ui.app"])
        self.close()

    def _append_attack_log(self, msg: str):
        """Append a message to the Attack Results terminal (GUI thread)."""
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        if hasattr(self, 'attack_terminal'):
            self.attack_terminal.append(f"<span style='color:#6ee7b7;'>[{ts}]</span> {msg}")

    def _apply_connection_status(self, state: str, extra_text: str):
        """Slot: update connection status from any thread (GUI thread only)."""
        self._set_status(state)
        if extra_text and hasattr(self, 'worker_status_text'):
            self.worker_status_text.setText(extra_text)

    def connect_to_master(self):
        """Show IP dialog then do ALL blocking I/O in a background thread."""
        pin = self.pin_input.text().strip()
        worker_name = self.name_input.text().strip() or "Worker"
        if not pin:
            self._set_status("enter_pin")
            return
        self._set_status("connecting")
        from PyQt5.QtWidgets import QInputDialog
        ip, ok = QInputDialog.getText(self, "Master IP", "Enter Master IP (default: 127.0.0.1):", text="127.0.0.1")
        if not ok or not ip.strip():
            self._set_status("cancelled")
            return
        ip = ip.strip()
        cpus = self.cpu_input.value()
        # All blocking I/O runs in background so GUI stays responsive
        threading.Thread(
            target=self._do_connect,
            args=(ip, pin, worker_name, cpus),
            daemon=True
        ).start()

    def _do_connect(self, ip: str, pin: str, worker_name: str, cpus: int):
        """Background thread: PIN check -> log client -> backend TCP connect."""
        # Step 1: PIN check
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((ip, 50051))
            s.sendall(pin.encode('utf-8'))
            resp = s.recv(16)
            s.close()
            if resp.strip() != b'OK':
                self.connection_status_signal.emit("pin_incorrect", "PIN incorrect")
                return
        except Exception as e:
            self.connection_status_signal.emit("pin_failed", f"PIN check failed: {e}")
            return

        # Step 2: Log client (port 50050, log streaming)
        if self.log_client:
            self.log_client.stop()
        self.log_client = LogClient(ip, port=50050, on_log=self.append_log, worker_name=worker_name)
        if not self.log_client.start_client():
            self.connection_status_signal.emit("connection_failed", "Log client failed")
            return

        # Step 3: Backend TCP connect to NetworkServer (port 50053)
        self.backend.worker_name = worker_name
        self.backend.worker_id = worker_name
        connected = self.backend.connect_to_master(ip, 50053, cpus)

        if connected:
            self.connection_status_signal.emit("connected", f"Connected to {ip}")
            self.attack_log_signal.emit(f"\U0001f4e1 Connected to master at {ip}")
        else:
            self.connection_status_signal.emit("connection_failed", "Task channel failed")

    def disconnect_from_master(self):
        if self.log_client:
            self.log_client.stop()
            self.log_client = None
        if hasattr(self, 'backend'):
            self.backend.disconnect()
            import subprocess
            subprocess.run(["ray", "stop", "--force"], capture_output=True)
        self._set_status("disconnected")
        if hasattr(self, 'worker_status_text'):
            self.worker_status_text.setText("Disconnected")

    def append_log(self, log_line):
        if '[PIN_CHANGED]' in log_line:
            self.disconnect_from_master()
            self._set_status("disconnected_pin")
        else:
            self.log_signal.emit(log_line)

    def apply_settings_from_log(self, log_line):
        if 'theme=' in log_line:
            theme = log_line.split('theme=')[1].strip()
            self.set_dark_mode(theme.startswith('dark'))
        if 'brightness=' in log_line:
            try:
                val = int(log_line.split('brightness=')[1].strip())
                self.set_brightness(val)
            except Exception:
                pass
        if 'font_size=' in log_line:
            try:
                val = int(log_line.split('font_size=')[1].strip())
                self.set_font_size(val)
            except Exception:
                pass

    def set_dark_mode(self, enabled):
        palette = QPalette()
        if enabled:
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
        else:
            palette = QApplication.style().standardPalette()
        self.setPalette(palette)

    def set_brightness(self, value):
        self.setWindowOpacity(value / 100)

    def set_font_size(self, value):
        self.font_signal.emit(value)

    def _set_font_size_main(self, value):
        self.attack_terminal.setStyleSheet(get_terminal_style(TEXT_TERMINAL, value))
        self.log_terminal.setStyleSheet(get_terminal_style(TEXT_LOG, value))

    def save_logs(self):
        fname, _ = QFileDialog.getSaveFileName(self, "Save Logs", "worker_logs.txt", "Text Files (*.txt);;All Files (*)")
        if fname:
            with open(fname, 'w', encoding='utf-8') as f:
                f.write("--- Attack Results ---\n")
                f.write(self.attack_terminal.toPlainText())
                f.write("\n--- Master Node Logs / Settings ---\n")
                f.write(self.log_terminal.toPlainText())

    def closeEvent(self, event):
        if self.log_client:
            self.log_client.stop()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(get_global_app_style())
    win = WorkerNodeWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
