"""
NetCluster UI Theme - Enterprise cybersecurity dashboard design system
Dark futuristic theme with electric blue/cyan accents and neon green success states
"""

# ─── Color System ─────────────────────────────────────────────────────────
# Background & surfaces
BG_DARK = "#0d1117"           # Deep charcoal
BG_NAVY = "#0d1b2a"           # Dark navy
BG_CARD = "#161b22"           # Card background
BG_CARD_HOVER = "#1c2128"     # Card hover
BG_INPUT = "#21262d"          # Input fields
BG_TERMINAL = "#0d1117"       # Log/terminal bg

# Primary accent - electric blue/cyan
ACCENT_CYAN = "#00d4ff"
ACCENT_BLUE = "#3b82f6"
ACCENT_BLUE_DARK = "#2563eb"

# Secondary - neon green (success, connected, active)
SUCCESS_GREEN = "#10b981"
SUCCESS_NEON = "#22c55e"
SUCCESS_DIM = "rgba(16, 185, 129, 0.15)"

# Warning / Danger - red-orange
DANGER_RED = "#ef4444"
DANGER_ORANGE = "#f97316"
WARNING_AMBER = "#f59e0b"

# Text
TEXT_PRIMARY = "#f1f5f9"
TEXT_SECONDARY = "#94a3b8"
TEXT_MUTED = "#64748b"
TEXT_TERMINAL = "#00ff88"     # Neon green for attack results
TEXT_LOG = "#fbbf24"          # Amber for logs

# Borders
BORDER_SUBTLE = "#30363d"
BORDER_ACCENT = "#00d4ff"
BORDER_SUCCESS = "#10b981"

# ─── Typography ──────────────────────────────────────────────────────────
# Fallback: Inter/Poppins → Segoe UI, JetBrains Mono → Consolas
FONT_UI = "Segoe UI, 'SF Pro Display', -apple-system, sans-serif"
FONT_MONO = "'JetBrains Mono', 'Fira Code', Consolas, 'Courier New', monospace"
FONT_SIZE_SM = "12px"
FONT_SIZE_MD = "14px"
FONT_SIZE_LG = "16px"
FONT_SIZE_XL = "20px"
FONT_SIZE_2XL = "24px"
FONT_SIZE_3XL = "32px"

# ─── Spacing (8px grid) ───────────────────────────────────────────────────
SPACE_8 = "8px"
SPACE_16 = "16px"
SPACE_24 = "24px"
SPACE_32 = "32px"

# ─── Border Radius ───────────────────────────────────────────────────────
RADIUS_SM = "6px"
RADIUS_MD = "10px"
RADIUS_LG = "12px"
RADIUS_XL = "16px"

# ─── Shared Stylesheets ──────────────────────────────────────────────────

def get_primary_button_style(hex_color=ACCENT_CYAN, hover_color="#00b4e6"):
    """Gradient button with hover glow"""
    return f"""
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {hex_color}, stop:1 {ACCENT_BLUE_DARK});
            color: white;
            border: none;
            border-radius: {RADIUS_MD};
            padding: 12px 24px;
            font-size: {FONT_SIZE_MD};
            font-weight: 600;
            font-family: {FONT_UI};
        }}
        QPushButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {hover_color}, stop:1 {ACCENT_BLUE});
        }}
        QPushButton:pressed {{
            padding: 13px 23px 11px 25px;
        }}
        QPushButton:disabled {{
            background: {BG_INPUT};
            color: {TEXT_MUTED};
        }}
    """

def get_success_button_style():
    return get_primary_button_style(SUCCESS_GREEN, SUCCESS_NEON)

def get_danger_button_style():
    return f"""
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {DANGER_RED}, stop:1 {DANGER_ORANGE});
            color: white;
            border: none;
            border-radius: {RADIUS_MD};
            padding: 12px 24px;
            font-size: {FONT_SIZE_MD};
            font-weight: 600;
            font-family: {FONT_UI};
        }}
        QPushButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #dc2626, stop:1 {DANGER_RED});
        }}
        QPushButton:disabled {{
            background: {BG_INPUT};
            color: {TEXT_MUTED};
        }}
    """

def get_secondary_button_style():
    return f"""
        QPushButton {{
            background: {BG_INPUT};
            color: {TEXT_PRIMARY};
            border: 1px solid {BORDER_SUBTLE};
            border-radius: {RADIUS_MD};
            padding: 10px 20px;
            font-size: {FONT_SIZE_MD};
            font-weight: 500;
            font-family: {FONT_UI};
        }}
        QPushButton:hover {{
            background: {BG_CARD_HOVER};
            border-color: {ACCENT_CYAN};
        }}
        QPushButton:disabled {{
            color: {TEXT_MUTED};
        }}
    """

def get_card_style(border_color=BORDER_SUBTLE):
    return f"""
        background: {BG_CARD};
        border: 1px solid {border_color};
        border-radius: {RADIUS_LG};
        padding: {SPACE_16};
    """

def get_groupbox_style(title_color=ACCENT_CYAN, border_color=BORDER_SUBTLE):
    return f"""
        QGroupBox {{
            font-size: {FONT_SIZE_LG};
            font-weight: 600;
            color: {title_color};
            background: {BG_CARD};
            border: 1px solid {border_color};
            border-radius: {RADIUS_LG};
            margin-top: 16px;
            padding: 16px 16px 8px 16px;
            font-family: {FONT_UI};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 12px;
            padding: 0 8px;
            background: {BG_CARD};
            color: {title_color};
        }}
    """

def get_input_style():
    return f"""
        QLineEdit, QSpinBox, QComboBox {{
            background: {BG_INPUT};
            color: {TEXT_PRIMARY};
            border: 1px solid {BORDER_SUBTLE};
            border-radius: {RADIUS_SM};
            padding: 8px 12px;
            font-size: {FONT_SIZE_MD};
            font-family: {FONT_UI};
            selection-background-color: {ACCENT_BLUE};
        }}
        QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
            border-color: {ACCENT_CYAN};
        }}
        QComboBox::drop-down {{
            border: none;
            background: transparent;
        }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid {TEXT_SECONDARY};
            margin-right: 8px;
        }}
    """

def get_terminal_style(fg_color=TEXT_TERMINAL, font_size=13):
    return f"""
        background-color: {BG_TERMINAL};
        color: {fg_color};
        font-family: {FONT_MONO};
        font-size: {font_size}px;
        border-radius: {RADIUS_MD};
        padding: 12px;
        border: 1px solid {BORDER_SUBTLE};
    """

def get_nav_button_style(active=False):
    if active:
        return f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {ACCENT_CYAN}, stop:1 {ACCENT_BLUE_DARK});
                color: white;
                border: none;
                border-radius: {RADIUS_MD};
                padding: 10px 20px;
                font-size: {FONT_SIZE_MD};
                font-weight: 600;
                font-family: {FONT_UI};
            }}
        """
    return f"""
        QPushButton {{
            background: {BG_INPUT};
            color: {TEXT_SECONDARY};
            border: 1px solid {BORDER_SUBTLE};
            border-radius: {RADIUS_MD};
            padding: 10px 20px;
            font-size: {FONT_SIZE_MD};
            font-weight: 500;
            font-family: {FONT_UI};
        }}
        QPushButton:hover {{
            background: {BG_CARD_HOVER};
            color: {TEXT_PRIMARY};
            border-color: {ACCENT_CYAN};
        }}
        QPushButton:checked {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {ACCENT_CYAN}, stop:1 {ACCENT_BLUE_DARK});
            color: white;
            border: none;
        }}
    """

def get_table_style():
    return f"""
        QTableWidget {{
            background-color: {BG_TERMINAL};
            color: {TEXT_PRIMARY};
            gridline-color: {BORDER_SUBTLE};
            border: 1px solid {BORDER_SUBTLE};
            border-radius: {RADIUS_MD};
            font-family: {FONT_UI};
        }}
        QTableWidget::item {{
            padding: 10px;
            border-bottom: 1px solid {BORDER_SUBTLE};
        }}
        QTableWidget::item:selected {{
            background-color: {ACCENT_BLUE};
            color: white;
        }}
        QHeaderView::section {{
            background-color: {BG_CARD};
            color: {ACCENT_CYAN};
            padding: 12px;
            border: none;
            border-bottom: 2px solid {ACCENT_CYAN};
            font-weight: 600;
        }}
    """

def get_slider_style():
    return f"""
        QSlider::groove:horizontal {{
            border: none;
            height: 6px;
            background: {BG_INPUT};
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background: {ACCENT_CYAN};
            width: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }}
        QSlider::handle:horizontal:hover {{
            background: {ACCENT_BLUE};
        }}
        QSlider::sub-page:horizontal {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {ACCENT_CYAN}, stop:1 {ACCENT_BLUE});
            border-radius: 3px;
        }}
    """

def get_radio_style():
    return f"""
        QRadioButton {{
            color: {TEXT_PRIMARY};
            font-size: {FONT_SIZE_MD};
            font-family: {FONT_UI};
            spacing: 8px;
        }}
        QRadioButton::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 9px;
            border: 2px solid {BORDER_SUBTLE};
            background: {BG_INPUT};
        }}
        QRadioButton::indicator:checked {{
            border-color: {ACCENT_CYAN};
            background: {ACCENT_CYAN};
        }}
    """

def get_global_app_style():
    """Global application styles (tooltips, etc.)"""
    return f"""
        QToolTip {{
            background: {BG_CARD};
            color: {TEXT_PRIMARY};
            border: 1px solid {BORDER_SUBTLE};
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 12px;
        }}
    """


def get_checkbox_switch_style():
    return f"""
        QCheckBox {{
            color: {TEXT_PRIMARY};
            font-size: {FONT_SIZE_MD};
            font-family: {FONT_UI};
            spacing: 10px;
        }}
        QCheckBox::indicator {{
            width: 44px;
            height: 24px;
            border-radius: 12px;
            border: 2px solid {BORDER_SUBTLE};
            background: {BG_INPUT};
        }}
        QCheckBox::indicator:checked {{
            border-color: {SUCCESS_GREEN};
            background: {SUCCESS_GREEN};
        }}
    """
