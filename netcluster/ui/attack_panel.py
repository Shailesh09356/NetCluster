"""
Brute Force Attack Panel
UI for configuring and monitoring distributed brute force attacks
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSpinBox, 
    QPushButton, QTextEdit, QGroupBox, QFormLayout, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget, 
    QCheckBox, QFileDialog, QRadioButton, QButtonGroup
)
from PyQt5.QtCore import pyqtSignal, QTimer, Qt, QObject
from PyQt5.QtGui import QColor
from netcluster.ui.theme import (
    BG_CARD, BG_INPUT, TEXT_PRIMARY, TEXT_SECONDARY, ACCENT_CYAN,
    SUCCESS_GREEN, DANGER_RED, get_primary_button_style, get_success_button_style,
    get_danger_button_style, get_secondary_button_style, get_groupbox_style,
    get_input_style, get_terminal_style, get_table_style, FONT_UI, FONT_MONO
)
import time


class AttackPanel(QObject):
    """Controller for configuring and monitoring brute force attacks"""
    
    attack_started = pyqtSignal(str)
    attack_updated = pyqtSignal(dict)
    
    def __init__(self, master_backend, parent=None):
        super().__init__(parent)
        self.master_backend = master_backend
        self.master_window = parent  # Reference to MasterNodeWindow
        self.active_attacks = {}
        self._logged_successes = set()  # Track already-logged success attack IDs
        
        # Create separate widgets for config and monitoring
        self.config_widget = self.create_config_widget()
        self.monitor_widget = self.create_monitor_tab()
        
        self.setup_connections()
        
        # Update timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_stats)
        self.update_timer.start(1000)
    
    def _forward_to_attack_terminal(self, msg: str):
        """Forward a message to the master window's Attack Results terminal"""
        if self.master_window and hasattr(self.master_window, 'log_attack'):
            self.master_window.log_attack(msg)
        
    def create_config_widget(self):
        """Creates the tabbed configuration UI"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(16)
        
        # Create tabs for different configurations
        self.tabs = QTabWidget()
        
        # Tab 1: Quick Attack
        quick_tab = self.create_quick_attack_tab()
        self.tabs.addTab(quick_tab, "Quick Attack")
        
        # Tab 2: Hash Cracking
        hash_tab = self.create_hash_cracking_tab()
        self.tabs.addTab(hash_tab, "Hash Cracking")
        
        # Tab 3: File Password
        file_tab = self.create_file_attack_tab()
        self.tabs.addTab(file_tab, "File Password")
        
        layout.addWidget(self.tabs)
        widget.setLayout(layout)
        return widget
    
    def create_monitor_tab(self):
        """Create the attacks monitoring tab"""
        widget = QWidget()
        monitor_layout = QVBoxLayout()
        
        # Attacks table
        self.attacks_table = QTableWidget()
        self.attacks_table.setColumnCount(7)
        self.attacks_table.setHorizontalHeaderLabels([
            "Attack ID", "Type", "Target", "Status", 
            "Attempts", "Speed", "Progress"
        ])
        self.attacks_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.attacks_table.setStyleSheet(get_table_style())
        monitor_layout.addWidget(self.attacks_table)
        
        # Real-time stats
        stats_layout = QHBoxLayout()
        self.total_attempts = QLabel("Total Attempts: 0")
        self.total_attempts.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 13px;")
        self.avg_speed = QLabel("Avg Speed: 0/s")
        self.avg_speed.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 13px;")
        self.active_workers = QLabel("Active Workers: 0")
        self.active_workers.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 13px;")
        stats_layout.addWidget(self.total_attempts)
        stats_layout.addWidget(self.avg_speed)
        stats_layout.addWidget(self.active_workers)
        monitor_layout.addLayout(stats_layout)
        
        # Log output
        log_label = QLabel("Attack Log:")
        log_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 13px; font-weight: 600;")
        monitor_layout.addWidget(log_label)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet(get_terminal_style(TEXT_PRIMARY, 12))
        monitor_layout.addWidget(self.log_output, stretch=1)
        
        widget.setLayout(monitor_layout)
        return widget
        
    def create_quick_attack_tab(self):
        """Create quick attack configuration tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(16)
        
        # Attack type selection
        type_group = QGroupBox("Attack Type")
        type_group.setStyleSheet(get_groupbox_style(ACCENT_CYAN))
        type_layout = QFormLayout()
        
        self.attack_type = QComboBox()
        self.attack_type.addItems([
            "SSH Brute Force",
            "FTP Brute Force", 
            "HTTP Basic Auth",
            "HTTP Form Login",
            "MySQL Database"
        ])
        self.attack_type.setStyleSheet(get_input_style())
        type_layout.addRow("Type:", self.attack_type)
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        
        # Target configuration
        target_group = QGroupBox("Target")
        target_group.setStyleSheet(get_groupbox_style(ACCENT_CYAN))
        target_layout = QFormLayout()
        
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("e.g., 192.168.1.100 or example.com")
        self.target_input.setStyleSheet(get_input_style())
        target_layout.addRow("Target:", self.target_input)
        
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(22)
        self.port_input.setStyleSheet(get_input_style())
        target_layout.addRow("Port:", self.port_input)
        
        target_group.setLayout(target_layout)
        layout.addWidget(target_group)
        
        # Credentials
        cred_group = QGroupBox("Credentials")
        cred_group.setStyleSheet(get_groupbox_style(ACCENT_CYAN))
        cred_layout = QFormLayout()
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username (leave empty for list)")
        self.username_input.setStyleSheet(get_input_style())
        cred_layout.addRow("Username:", self.username_input)
        
        # Wordlist selection
        wordlist_layout = QHBoxLayout()
        self.wordlist_path = QLineEdit()
        self.wordlist_path.setPlaceholderText("Path to password wordlist")
        self.wordlist_path.setStyleSheet(get_input_style())
        self.browse_wordlist = QPushButton("Browse...")
        self.browse_wordlist.setStyleSheet(get_secondary_button_style())
        self.browse_wordlist.clicked.connect(self.browse_wordlist_file)
        wordlist_layout.addWidget(self.wordlist_path)
        wordlist_layout.addWidget(self.browse_wordlist)
        cred_layout.addRow("Wordlist:", wordlist_layout)
        
        cred_group.setLayout(cred_layout)
        layout.addWidget(cred_group)
        
        # Options
        options_group = QGroupBox("Options")
        options_group.setStyleSheet(get_groupbox_style(ACCENT_CYAN))
        options_layout = QVBoxLayout()
        
        self.use_generation = QCheckBox("Use generation instead of wordlist (brute force)")
        self.use_generation.setStyleSheet(f"color: {TEXT_PRIMARY};")
        options_layout.addWidget(self.use_generation)
        
        # Generation options (initially hidden)
        self.gen_options = QWidget()
        gen_layout = QHBoxLayout()
        gen_layout.addWidget(QLabel("Min Length:"))
        self.min_length = QSpinBox()
        self.min_length.setRange(1, 10)
        self.min_length.setValue(4)
        self.min_length.setStyleSheet(get_input_style())
        gen_layout.addWidget(self.min_length)
        
        gen_layout.addWidget(QLabel("Max Length:"))
        self.max_length = QSpinBox()
        self.max_length.setRange(1, 10)
        self.max_length.setValue(6)
        self.max_length.setStyleSheet(get_input_style())
        gen_layout.addWidget(self.max_length)
        
        gen_layout.addWidget(QLabel("Charset:"))
        self.charset = QComboBox()
        self.charset.addItems([
            "Lowercase (a-z)",
            "Uppercase (A-Z)",
            "Letters (a-zA-Z)",
            "Alphanumeric (a-z0-9)",
            "Full ASCII"
        ])
        self.charset.setStyleSheet(get_input_style())
        gen_layout.addWidget(self.charset)
        
        self.gen_options.setLayout(gen_layout)
        self.gen_options.setVisible(False)
        options_layout.addWidget(self.gen_options)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Control buttons
        button_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start Attack")
        self.start_btn.setStyleSheet(get_success_button_style())
        self.stop_btn = QPushButton("Stop All")
        self.stop_btn.setStyleSheet(get_danger_button_style())
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        layout.addLayout(button_layout)
        
        layout.addStretch()
        widget.setLayout(layout)
        
        # Connect signals
        self.use_generation.toggled.connect(self.gen_options.setVisible)
        self.start_btn.clicked.connect(self.start_attack)
        self.stop_btn.clicked.connect(self.stop_attacks)
        
        return widget
    
    def create_hash_cracking_tab(self):
        """Create hash cracking tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(16)
        
        # Hash input
        hash_group = QGroupBox("Hash to Crack")
        hash_group.setStyleSheet(get_groupbox_style(ACCENT_CYAN))
        hash_layout = QFormLayout()
        
        self.hash_input = QLineEdit()
        self.hash_input.setPlaceholderText("e.g., 5f4dcc3b5aa765d61d8327deb882cf99")
        self.hash_input.setStyleSheet(get_input_style())
        hash_layout.addRow("Hash:", self.hash_input)
        
        self.hash_type = QComboBox()
        self.hash_type.addItems(["MD5", "SHA1", "SHA256", "SHA512"])
        self.hash_type.setStyleSheet(get_input_style())
        hash_layout.addRow("Hash Type:", self.hash_type)
        
        hash_group.setLayout(hash_layout)
        layout.addWidget(hash_group)
        
        # Attack mode
        mode_group = QGroupBox("Attack Mode")
        mode_group.setStyleSheet(get_groupbox_style(ACCENT_CYAN))
        mode_layout = QVBoxLayout()
        
        self.dict_attack = QRadioButton("Dictionary Attack")
        self.dict_attack.setChecked(True)
        self.brute_attack = QRadioButton("Brute Force")
        
        for r in [self.dict_attack, self.brute_attack]:
            r.setStyleSheet(f"color: {TEXT_PRIMARY};")
        
        mode_layout.addWidget(self.dict_attack)
        mode_layout.addWidget(self.brute_attack)
        
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # Wordlist (for dictionary attack)
        wordlist_group = QGroupBox("Wordlist")
        wordlist_group.setStyleSheet(get_groupbox_style(ACCENT_CYAN))
        wordlist_layout = QHBoxLayout()
        self.hash_wordlist = QLineEdit()
        self.hash_wordlist.setStyleSheet(get_input_style())
        self.browse_hash_wordlist = QPushButton("Browse...")
        self.browse_hash_wordlist.setStyleSheet(get_secondary_button_style())
        self.browse_hash_wordlist.clicked.connect(self.browse_hash_wordlist_file)
        wordlist_layout.addWidget(self.hash_wordlist)
        wordlist_layout.addWidget(self.browse_hash_wordlist)
        wordlist_group.setLayout(wordlist_layout)
        layout.addWidget(wordlist_group)
        
        # Brute force options
        self.hash_brute_options = QWidget()
        brute_layout = QHBoxLayout()
        brute_layout.addWidget(QLabel("Min Length:"))
        self.hash_min = QSpinBox()
        self.hash_min.setRange(1, 10)
        self.hash_min.setValue(4)
        self.hash_min.setStyleSheet(get_input_style())
        brute_layout.addWidget(self.hash_min)
        
        brute_layout.addWidget(QLabel("Max Length:"))
        self.hash_max = QSpinBox()
        self.hash_max.setRange(1, 10)
        self.hash_max.setValue(6)
        self.hash_max.setStyleSheet(get_input_style())
        brute_layout.addWidget(self.hash_max)
        
        brute_layout.addWidget(QLabel("Charset:"))
        self.hash_charset = QComboBox()
        self.hash_charset.addItems([
            "Lowercase (a-z)",
            "Alphanumeric (a-z0-9)",
            "Full ASCII"
        ])
        self.hash_charset.setStyleSheet(get_input_style())
        brute_layout.addWidget(self.hash_charset)
        
        self.hash_brute_options.setLayout(brute_layout)
        self.hash_brute_options.setVisible(False)
        layout.addWidget(self.hash_brute_options)
        
        # Connect signals
        self.dict_attack.toggled.connect(lambda: self.hash_brute_options.setVisible(not self.dict_attack.isChecked()))
        
        # Start button
        self.start_hash_btn = QPushButton("Start Hash Cracking")
        self.start_hash_btn.setStyleSheet(get_success_button_style())
        self.start_hash_btn.clicked.connect(self.start_hash_attack)
        layout.addWidget(self.start_hash_btn)
        
        layout.addStretch()
        widget.setLayout(layout)
        
        return widget
    
    def create_file_attack_tab(self):
        """Create file password cracking tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(16)
        
        # File selection
        file_group = QGroupBox("Protected File")
        file_group.setStyleSheet(get_groupbox_style(ACCENT_CYAN))
        file_layout = QHBoxLayout()
        
        self.file_path = QLineEdit()
        self.file_path.setPlaceholderText("Path to protected file (ZIP/PDF)")
        self.file_path.setStyleSheet(get_input_style())
        self.browse_file = QPushButton("Browse...")
        self.browse_file.setStyleSheet(get_secondary_button_style())
        self.browse_file.clicked.connect(self.browse_file_dialog)
        file_layout.addWidget(self.file_path)
        file_layout.addWidget(self.browse_file)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # File type
        type_group = QGroupBox("File Type")
        type_group.setStyleSheet(get_groupbox_style(ACCENT_CYAN))
        type_layout = QFormLayout()
        self.file_type = QComboBox()
        self.file_type.addItems(["ZIP Archive", "PDF Document"])
        self.file_type.setStyleSheet(get_input_style())
        type_layout.addRow("Type:", self.file_type)
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        
        # Attack mode
        mode_group = QGroupBox("Attack Mode")
        mode_group.setStyleSheet(get_groupbox_style(ACCENT_CYAN))
        mode_layout = QVBoxLayout()
        
        self.file_dict = QRadioButton("Dictionary Attack")
        self.file_dict.setChecked(True)
        self.file_brute = QRadioButton("Brute Force")
        
        for r in [self.file_dict, self.file_brute]:
            r.setStyleSheet(f"color: {TEXT_PRIMARY};")
        
        mode_layout.addWidget(self.file_dict)
        mode_layout.addWidget(self.file_brute)
        
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # Wordlist
        wordlist_group = QGroupBox("Wordlist")
        wordlist_group.setStyleSheet(get_groupbox_style(ACCENT_CYAN))
        wordlist_layout = QHBoxLayout()
        self.file_wordlist = QLineEdit()
        self.file_wordlist.setStyleSheet(get_input_style())
        self.browse_file_wordlist = QPushButton("Browse...")
        self.browse_file_wordlist.setStyleSheet(get_secondary_button_style())
        self.browse_file_wordlist.clicked.connect(self.browse_file_wordlist_file)
        wordlist_layout.addWidget(self.file_wordlist)
        wordlist_layout.addWidget(self.browse_file_wordlist)
        wordlist_group.setLayout(wordlist_layout)
        layout.addWidget(wordlist_group)
        
        # Start button
        self.start_file_btn = QPushButton("Start Cracking")
        self.start_file_btn.setStyleSheet(get_success_button_style())
        self.start_file_btn.clicked.connect(self.start_file_attack)
        layout.addWidget(self.start_file_btn)
        
        layout.addStretch()
        widget.setLayout(layout)
        
        return widget
    
    def setup_connections(self):
        """Setup signal connections"""
        self.attack_started.connect(self.on_attack_started)
        self.attack_updated.connect(self.on_attack_updated)
    
    def browse_wordlist_file(self):
        """Open file dialog for wordlist selection"""
        file_path, _ = QFileDialog.getOpenFileName(
            None, "Select Wordlist File", "", "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            self.wordlist_path.setText(file_path)
    
    def browse_hash_wordlist_file(self):
        """Open file dialog for hash wordlist"""
        file_path, _ = QFileDialog.getOpenFileName(
            None, "Select Wordlist File", "", "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            self.hash_wordlist.setText(file_path)
    
    def browse_file_dialog(self):
        """Open file dialog for protected file"""
        file_path, _ = QFileDialog.getOpenFileName(
            None, "Select Protected File", "", "All Files (*)"
        )
        if file_path:
            self.file_path.setText(file_path)
    
    def browse_file_wordlist_file(self):
        """Open file dialog for file wordlist"""
        file_path, _ = QFileDialog.getOpenFileName(
            None, "Select Wordlist File", "", "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            self.file_wordlist.setText(file_path)
    
    def start_attack(self):
        """Start brute force attack"""
        # Check if workers available
        workers = self.master_backend.get_available_workers()
        if len(workers) == 0:
            self.log_output.append("❌ No workers available")
            return
        
        # Build attack configuration
        attack_type_map = {
            "SSH Brute Force": "ssh",
            "FTP Brute Force": "ftp",
            "HTTP Basic Auth": "http_basic",
            "HTTP Form Login": "http_form",
            "MySQL Database": "mysql"
        }
        
        attack_type = attack_type_map.get(self.attack_type.currentText(), "ssh")
        
        config = {
            'type': attack_type,
            'target': self.target_input.text(),
            'port': self.port_input.value(),
            'username': self.username_input.text() or None,
            'password_list': self.wordlist_path.text() if self.wordlist_path.text() else None,
            'use_wordlist': not self.use_generation.isChecked(),
            'protocol_config': {
                'timeout': 5
            }
        }
        
        if self.use_generation.isChecked():
            config.update({
                'min_length': self.min_length.value(),
                'max_length': self.max_length.value(),
                'charset': self.get_charset_from_combo(self.charset)
            })
        
        # Send to backend
        attack_id = self.master_backend.create_attack(config)
        
        if attack_id:
            self.active_attacks[attack_id] = {
                'start_time': time.time(),
                'config': config,
                'attempts': 0
            }
            
            self.attack_started.emit(attack_id)
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            
            self.log_output.append(f"🚀 Started attack {attack_id}")
            self.log_output.append(f"   Target: {config['target']}:{config['port']}")
            self.log_output.append(f"   Type: {attack_type}")
            self.log_output.append(f"   Workers: {len(workers)}")
            self._forward_to_attack_terminal(f"🚀 Attack started: {attack_type} → {config['target']}:{config['port']}")
            self._forward_to_attack_terminal(f"   Workers assigned: {len(workers)} | ID: {attack_id[:16]}")
            # Auto-redirect to Dashboard
            if self.master_window and hasattr(self.master_window, 'show_section'):
                self.master_window.show_section(1)
    
    def get_charset_from_combo(self, combo):
        """Get charset string from combo box selection"""
        charsets = {
            0: 'abcdefghijklmnopqrstuvwxyz',
            1: 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
            2: 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ',
            3: 'abcdefghijklmnopqrstuvwxyz0123456789',
            4: 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()'
        }
        return charsets.get(combo.currentIndex(), 'abcdefghijklmnopqrstuvwxyz')
    
    def start_hash_attack(self):
        """Start hash cracking attack"""
        if not self.hash_input.text():
            self.log_output.append("❌ Please enter a hash value")
            return
        
        config = {
            'type': 'hash',
            'target': self.hash_input.text(),  # Hash value is the target
            'hash_type': self.hash_type.currentText().lower(),
            'use_wordlist': self.dict_attack.isChecked(),
            'protocol_config': {
                'hash_type': self.hash_type.currentText().lower()
            }
        }
        
        if self.dict_attack.isChecked():
            config['password_list'] = self.hash_wordlist.text()
        else:
            config.update({
                'min_length': self.hash_min.value(),
                'max_length': self.hash_max.value(),
                'charset': self.get_charset_from_combo(self.hash_charset),
                'use_wordlist': False
            })
        
        attack_id = self.master_backend.create_attack(config)
        if attack_id:
            self.active_attacks[attack_id] = {
                'start_time': time.time(),
                'config': config
            }
            self.log_output.append(f"🚀 Started hash cracking: {config['target'][:20]}...")
            self._forward_to_attack_terminal(f"🚀 Hash cracking started: {config['target'][:20]}...")
            # Auto-redirect to Dashboard
            if self.master_window and hasattr(self.master_window, 'show_section'):
                self.master_window.show_section(1)
    
    def start_file_attack(self):
        """Start file password cracking"""
        if not self.file_path.text():
            self.log_output.append("❌ Please select a file")
            return
        
        # Determine attack type: 'zip' or 'pdf' (pdf not yet supported, warn user)
        raw_type = self.file_type.currentText().lower().split()[0]  # 'zip' or 'pdf'
        if raw_type == 'pdf':
            self.log_output.append("❌ PDF cracking not yet supported")
            return
        
        file_path_val = self.file_path.text()
        use_dict = self.file_dict.isChecked()
        
        if use_dict:
            if not self.file_wordlist.text():
                self.log_output.append("❌ Please select a wordlist file")
                return
            config = {
                'type': raw_type,
                'target': file_path_val,
                'use_wordlist': True,
                'password_list': self.file_wordlist.text(),
                'protocol_config': {}
            }
        else:
            config = {
                'type': raw_type,
                'target': file_path_val,
                'use_wordlist': False,
                'password_list': None,
                'min_length': 4,
                'max_length': 8,
                'charset': 'abcdefghijklmnopqrstuvwxyz0123456789',
                'protocol_config': {}
            }
        
        attack_id = self.master_backend.create_attack(config)
        if attack_id:
            self.active_attacks[attack_id] = {
                'start_time': time.time(),
                'config': config
            }
            self.log_output.append(f"🚀 Started cracking {raw_type.upper()} file: {file_path_val}")
            self._forward_to_attack_terminal(f"🚀 File cracking started: {raw_type.upper()} | {file_path_val}")
            # Auto-redirect to Dashboard
            if self.master_window and hasattr(self.master_window, 'show_section'):
                self.master_window.show_section(1)
        else:
            self.log_output.append("❌ Failed to create attack (no workers available?)")
    
    def stop_attacks(self):
        """Stop all active attacks"""
        for attack_id in list(self.active_attacks.keys()):
            self.master_backend.stop_attack(attack_id)
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.log_output.append("⛔ All attacks stopped")
        self._forward_to_attack_terminal("⛔ All attacks stopped")
        self._logged_successes.clear()
    
    def update_stats(self):
        """Update real-time statistics"""
        if not self.active_attacks:
            return
        
        # Get status for all attacks
        total_attempts = 0
        total_speed = 0
        active_count = 0
        
        # Clear and update table
        self.attacks_table.setRowCount(len(self.active_attacks))
        
        for row, (attack_id, attack_info) in enumerate(self.active_attacks.items()):
            status = self.master_backend.get_attack_status(attack_id)
            
            if status:
                total_attempts += status.get('attempts', 0)
                total_speed += status.get('speed', 0)
                
                if status.get('status') == 'running':
                    active_count += 1
                
                # Update table
                self.attacks_table.setItem(row, 0, QTableWidgetItem(attack_id[:16]))
                self.attacks_table.setItem(row, 1, QTableWidgetItem(status.get('type', '')))
                self.attacks_table.setItem(row, 2, QTableWidgetItem(status.get('target', '')))
                
                status_item = QTableWidgetItem(status.get('status', ''))
                if status.get('found_password'):
                    status_item.setText("SUCCESS!")
                    status_item.setForeground(QColor(SUCCESS_GREEN))
                elif status.get('status') == 'executing':
                    status_item.setText("executing...")
                    status_item.setForeground(QColor("#f59e0b"))  # Yellow/amber
                elif status.get('status') == 'running':
                    status_item.setForeground(QColor(ACCENT_CYAN))
                elif status.get('status') == 'failed':
                    status_item.setForeground(QColor(DANGER_RED))
                self.attacks_table.setItem(row, 3, status_item)
                
                self.attacks_table.setItem(row, 4, QTableWidgetItem(str(status.get('attempts', 0))))
                
                # Show speed or elapsed time when speed is 0
                speed = status.get('speed', 0)
                elapsed = status.get('elapsed', 0)
                if speed > 0:
                    speed_text = f"{speed:.1f}/s"
                elif elapsed > 0:
                    speed_text = f"{elapsed:.0f}s elapsed"
                else:
                    speed_text = "starting..."
                self.attacks_table.setItem(row, 5, QTableWidgetItem(speed_text))
                
                progress = status.get('progress', 0)
                progress_item = QTableWidgetItem(f"{progress:.1f}%")
                self.attacks_table.setItem(row, 6, progress_item)
                
                # Log success (once per attack)
                if status.get('found_password') and attack_id not in self._logged_successes:
                    self._logged_successes.add(attack_id)
                    self.log_output.append(f"✅ SUCCESS! Password found: {status.get('found_password')}")
                    self._forward_to_attack_terminal(f"✅ SUCCESS! Password found: {status.get('found_password')}")
                    if status.get('found_username'):
                        self.log_output.append(f"   Username: {status.get('found_username')}")
                        self._forward_to_attack_terminal(f"   Username: {status.get('found_username')}")
                
                # Forward running status updates periodically
                if status.get('status') == 'running' and status.get('attempts', 0) > 0:
                    attempts = status.get('attempts', 0)
                    speed = status.get('speed', 0)
                    progress = status.get('progress', 0)
                    # Only update the terminal every ~10 seconds worth of stats
                    prev_attempts = attack_info.get('_last_logged_attempts', 0)
                    if attempts - prev_attempts >= max(50, int(speed * 10)):
                        attack_info['_last_logged_attempts'] = attempts
                        self._forward_to_attack_terminal(
                            f"[{attack_id[:12]}] Attempts: {attempts} | Speed: {speed:.1f}/s | Progress: {progress:.1f}%"
                        )
        
        # Update stats labels
        self.total_attempts.setText(f"Total Attempts: {total_attempts}")
        if active_count > 0:
            self.avg_speed.setText(f"Avg Speed: {total_speed/active_count:.1f}/s")
        self.active_workers.setText(f"Active Workers: {active_count}")
    
    def on_attack_started(self, attack_id):
        """Handle attack started"""
        pass
    
    def on_attack_updated(self, update):
        """Handle attack update"""
        if update.get('type') == 'log':
            self.log_output.append(update.get('message', ''))
        elif update.get('type') == 'success':
            self.log_output.append(f"✅ SUCCESS! Password found: {update.get('password')}")
