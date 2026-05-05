import ray
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QHBoxLayout, QGroupBox
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QColor
from netcluster.ui.theme import get_table_style, TEXT_PRIMARY, SUCCESS_GREEN, DANGER_RED, ACCENT_CYAN, get_primary_button_style

class RayStatusPage(QWidget):
    def __init__(self, master_backend):
        super().__init__()
        self.master_backend = master_backend
        self.setup_ui()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_status)
        self.timer.start(2000)
        
        # Initial call
        self.update_status()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(16)
        
        # Header Info
        header_layout = QHBoxLayout()
        self.status_lbl = QLabel("Ray Cluster Status: Checking...")
        self.status_lbl.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {TEXT_PRIMARY};")
        header_layout.addWidget(self.status_lbl)
        
        refresh_btn = QPushButton("Refresh Status")
        refresh_btn.setStyleSheet(get_primary_button_style())
        refresh_btn.clicked.connect(self.update_status)
        header_layout.addWidget(refresh_btn)
        layout.addLayout(header_layout)
        
        # Resources Box
        res_group = QGroupBox("Target Cluster Resources")
        res_group.setStyleSheet(f"color: {ACCENT_CYAN}; font-weight: bold; font-size: 14px;")
        res_layout = QVBoxLayout()
        self.res_lbl = QLabel("Loading...")
        self.res_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 13px;")
        res_layout.addWidget(self.res_lbl)
        res_group.setLayout(res_layout)
        layout.addWidget(res_group)
        
        # Node Table
        self.node_table = QTableWidget()
        self.node_table.setColumnCount(4)
        self.node_table.setHorizontalHeaderLabels(["Node IP", "Status", "Total CPUs", "Total Memory"])
        self.node_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.node_table.setStyleSheet(get_table_style())
        layout.addWidget(self.node_table)
        
        self.setLayout(layout)
        
    def update_status(self):
        try:
            if not ray.is_initialized():
                self.status_lbl.setText("Ray Cluster Status: Disconnected")
                self.status_lbl.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {DANGER_RED};")
                return
            
            self.status_lbl.setText("Ray Cluster Status: ONLINE")
            self.status_lbl.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {SUCCESS_GREEN};")
            
            res = ray.cluster_resources()
            res_str = f"CPUs: {res.get('CPU', 0)} | Memory: {round(res.get('memory', 0)/(1024**3), 2)} GB"
            self.res_lbl.setText(res_str)
            
            nodes = ray.nodes()
            self.node_table.setRowCount(len(nodes))
            for i, node in enumerate(nodes):
                ip = node.get("NodeManagerAddress", "Unknown")
                alive = node.get("Alive", False)
                
                res = node.get("Resources", {})
                cpus = str(res.get("CPU", "0"))
                mem = f"{round(res.get('memory', 0)/(1024**3), 2)} GB"
                
                self.node_table.setItem(i, 0, QTableWidgetItem(ip))
                status_item = QTableWidgetItem("Alive" if alive else "Dead")
                if alive:
                    # Using hex code for Success Green since QColor needs valid color formats.
                    status_item.setForeground(QColor("#10B981")) 
                else:
                    status_item.setForeground(QColor("#EF4444"))
                self.node_table.setItem(i, 1, status_item)
                self.node_table.setItem(i, 2, QTableWidgetItem(cpus))
                self.node_table.setItem(i, 3, QTableWidgetItem(mem))
                
        except Exception as e:
            self.status_lbl.setText(f"Ray Cluster Status: Error ({e})")
            self.status_lbl.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {DANGER_RED};")
