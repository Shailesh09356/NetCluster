import sys
import subprocess
import os
import random
import math
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel,
    QHBoxLayout, QGraphicsDropShadowEffect, QFrame, QDialog,
    QDialogButtonBox, QScrollArea, QShortcut, QGraphicsOpacityEffect
)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPointF, pyqtProperty
from PyQt5.QtGui import (
    QPainter, QColor, QLinearGradient, QPen, QKeySequence, QFont, QBrush,
    QRadialGradient, QPainterPath, QPixmap, QIcon
)

from netcluster.ui.theme import (
    BG_CARD, ACCENT_CYAN, SUCCESS_GREEN, TEXT_PRIMARY, TEXT_SECONDARY,
    TEXT_MUTED, BORDER_SUBTLE, get_danger_button_style, get_secondary_button_style,
    FONT_UI, get_global_app_style, RADIUS_LG
)

os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_SCALE_FACTOR"] = "1"
os.environ["QT_SCREEN_SCALE_FACTORS"] = "1"

VERSION = "1.0.0"


class Particle:
    """Individual particle with enhanced animation properties"""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.uniform(-0.8, 0.8)
        self.vy = random.uniform(-0.8, 0.8)
        self.size = random.randint(2, 6)
        self.opacity = random.uniform(0.1, 0.4)
        self.color = QColor(
            random.randint(0, 100),
            random.randint(150, 255),
            random.randint(200, 255),
            int(self.opacity * 255)
        )
        self.pulse_speed = random.uniform(0.02, 0.05)
        self.pulse_phase = random.uniform(0, 2 * math.pi)
        self.current_opacity = self.opacity


class AnimatedBackground(QWidget):
    """Enhanced animated background with pulsing particles and waves"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.particles = []
        self.wave_offset = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(30)  # 30ms for smoother animation
        self.init_particles()
        
        # Gradient animation
        self.gradient_shift = 0
        self.gradient_timer = QTimer()
        self.gradient_timer.timeout.connect(self.update_gradient)
        self.gradient_timer.start(100)

    def init_particles(self):
        w, h = 960, 720
        for _ in range(40):  # More particles
            self.particles.append(Particle(
                random.randint(0, w),
                random.randint(0, h)
            ))

    def update_animation(self):
        w, h = max(1, self.width()), max(1, self.height())
        for p in self.particles:
            # Update position
            p.x = (p.x + p.vx) % w
            p.y = (p.y + p.vy) % h
            
            # Pulse opacity
            p.pulse_phase += p.pulse_speed
            pulse_factor = (math.sin(p.pulse_phase) + 1) / 2
            p.current_opacity = p.opacity * (0.7 + 0.3 * pulse_factor)
        
        self.wave_offset = (self.wave_offset + 0.02) % (2 * math.pi)
        self.update()

    def update_gradient(self):
        self.gradient_shift = (self.gradient_shift + 0.01) % 1
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        # Animated base gradient
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        
        # Shifting colors for subtle animation
        shift = self.gradient_shift
        gradient.setColorAt(0, QColor(13, 17, 23))
        gradient.setColorAt(0.3, QColor(13, 27, int(42 + 10 * shift)))
        gradient.setColorAt(0.7, QColor(15, 23, int(42 + 10 * (1 - shift))))
        gradient.setColorAt(1, QColor(17, 24, 39))
        painter.fillRect(self.rect(), gradient)

        # Animated radial glow
        glow_x = self.width() * (0.7 + 0.1 * math.sin(self.wave_offset))
        glow_y = self.height() * (0.3 + 0.1 * math.cos(self.wave_offset * 1.3))
        radial = QRadialGradient(glow_x, glow_y, self.width() * 0.5)
        radial.setColorAt(0, QColor(0, 212, 255, 15))
        radial.setColorAt(0.5, QColor(0, 212, 255, 8))
        radial.setColorAt(1, QColor(0, 212, 255, 0))
        painter.fillRect(self.rect(), radial)

        # Draw animated particles with pulsing effect
        for p in self.particles:
            painter.setOpacity(p.current_opacity)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(p.color))
            
            # Size pulse
            pulse_size = p.size * (0.8 + 0.4 * math.sin(p.pulse_phase))
            painter.drawEllipse(QPointF(p.x, p.y), pulse_size, pulse_size)

        # Animated grid lines with wave effect
        painter.setOpacity(0.06)
        pen = QPen(QColor(255, 255, 255, 100), 1)
        pen.setStyle(Qt.DotLine)
        painter.setPen(pen)
        
        # Horizontal lines with wave - FIXED: convert to int
        for y in range(0, self.height(), 40):
            wave = 10 * math.sin(self.wave_offset + y * 0.02)
            painter.drawLine(0, int(y + wave), self.width(), int(y + wave))

        # Vertical lines with wave - FIXED: convert to int
        for x in range(0, self.width(), 40):
            wave = 10 * math.cos(self.wave_offset + x * 0.02)
            painter.drawLine(int(x + wave), 0, int(x + wave), self.height())


class AnimatedNodeButton(QPushButton):
    """Enhanced animated button with multiple animation effects"""
    def __init__(self, text, accent_color, icon_emoji, parent=None):
        super().__init__(text, parent)
        self.accent = accent_color
        self.icon_emoji = icon_emoji
        self._hover_scale = 1.0
        self._glow_intensity = 0
        self.pulse_phase = 0
        
        self.setMinimumSize(320, 80)
        self.setMaximumWidth(450)
        self.setCursor(Qt.PointingHandCursor)
        
        # Hover animations
        self.hover_animation = QPropertyAnimation(self, b"hover_scale")
        self.hover_animation.setDuration(200)
        self.hover_animation.setEasingCurve(QEasingCurve.OutCubic)
        
        self.glow_animation = QPropertyAnimation(self, b"glow_intensity")
        self.glow_animation.setDuration(300)
        self.glow_animation.setEasingCurve(QEasingCurve.OutCubic)
        
        # Pulse timer for idle animation
        self.pulse_timer = QTimer()
        self.pulse_timer.timeout.connect(self.update_pulse)
        self.pulse_timer.start(50)
        
        # Shadow effect
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(20)
        self.shadow.setColor(QColor(0, 212, 255, 0))
        self.shadow.setOffset(0, 4)
        self.setGraphicsEffect(self.shadow)
        
        self.setup_style()

    def setup_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: white;
                border: 2px solid {self.accent};
                border-radius: 16px;
                padding: 0px;
                font-size: 18px;
                font-weight: 600;
                font-family: {FONT_UI};
                text-align: center;
            }}
        """)

    def get_hover_scale(self):
        return self._hover_scale

    def set_hover_scale(self, value):
        self._hover_scale = value
        self.update()

    def get_glow_intensity(self):
        return self._glow_intensity

    def set_glow_intensity(self, value):
        self._glow_intensity = value
        self.shadow.setColor(QColor(0, 212, 255, int(100 * value)))
        self.shadow.setBlurRadius(20 + int(20 * value))
        self.update()

    hover_scale = pyqtProperty(float, get_hover_scale, set_hover_scale)
    glow_intensity = pyqtProperty(float, get_glow_intensity, set_glow_intensity)

    def update_pulse(self):
        self.pulse_phase = (self.pulse_phase + 0.1) % (2 * math.pi)
        if not self.underMouse():
            self.set_glow_intensity(0.2 + 0.1 * math.sin(self.pulse_phase))
            self.update()

    def enterEvent(self, event):
        self.hover_animation.setStartValue(self._hover_scale)
        self.hover_animation.setEndValue(1.05)
        self.hover_animation.start()
        
        self.glow_animation.setStartValue(self._glow_intensity)
        self.glow_animation.setEndValue(1.0)
        self.glow_animation.start()
        
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hover_animation.setStartValue(self._hover_scale)
        self.hover_animation.setEndValue(1.0)
        self.hover_animation.start()
        
        self.glow_animation.setStartValue(self._glow_intensity)
        self.glow_animation.setEndValue(0.3)
        self.glow_animation.start()
        
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Create button path
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 16, 16)
        
        # Animated gradient background
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(self.accent).lighter(120))
        gradient.setColorAt(1, QColor(self.accent).darker(120))
        
        # Apply hover scale transform
        painter.save()
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(self._hover_scale, self._hover_scale)
        painter.translate(-self.width() / 2, -self.height() / 2)
        
        # Fill button
        painter.fillPath(path, gradient)
        
        # Draw glowing border
        pen = QPen(QColor(255, 255, 255, int(100 * self._glow_intensity)), 2)
        painter.setPen(pen)
        painter.drawPath(path)
        
        painter.restore()
        
        # Draw text with icon
        painter.save()
        painter.setPen(Qt.white)
        
        # Draw emoji icon
        font = QFont("Segoe UI Emoji", 24)
        painter.setFont(font)
        painter.drawText(40, 0, self.width(), self.height(), Qt.AlignLeft | Qt.AlignVCenter, self.icon_emoji)
        
        # Draw button text
        font = QFont(FONT_UI, 18, QFont.Bold)
        painter.setFont(font)
        painter.drawText(0, 0, self.width(), self.height(), Qt.AlignCenter, self.text())
        
        painter.restore()


class FloatingCard(QFrame):
    """Animated floating card for content"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.float_offset = 0
        self.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(30, 41, 59, 0.9),
                    stop:1 rgba(15, 23, 42, 0.9));
                border: 1px solid {BORDER_SUBTLE};
                border-radius: {RADIUS_LG};
            }}
        """)
        
        # Float animation
        self.float_timer = QTimer()
        self.float_timer.timeout.connect(self.update_float)
        self.float_timer.start(50)
        
        # Shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 8)
        self.setGraphicsEffect(shadow)

    def update_float(self):
        self.float_offset = (self.float_offset + 0.02) % (2 * math.pi)
        # FIXED: Use move with proper coordinate handling
        current_pos = self.pos()
        self.move(current_pos.x(), current_pos.y() + int(2 * math.sin(self.float_offset)))


class TypewriterLabel(QLabel):
    """Label with typewriter animation effect"""
    def __init__(self, text, delay=50, parent=None):
        super().__init__(parent)
        self.full_text = text
        self.current_text = ""
        self.index = 0
        self.delay = delay
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_text)
        self.timer.start(delay)
        
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 42px; font-weight: 700;")

    def update_text(self):
        if self.index < len(self.full_text):
            self.current_text += self.full_text[self.index]
            self.setText(self.current_text)
            self.index += 1
        else:
            self.timer.stop()


class AboutDialog(QDialog):
    """Enhanced About dialog with animation"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About NetCluster")
        self.setFixedSize(450, 300)
        self.setStyleSheet(f"""
            QDialog {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {BG_CARD},
                    stop:1 #1e293b);
                border: 2px solid {ACCENT_CYAN};
                border-radius: 16px;
            }}
            QDialogButtonBox QPushButton {{
                min-width: 100px;
                padding: 8px 16px;
                border-radius: 8px;
            }}
        """)
        
        # Fade in animation
        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)
        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_anim.setDuration(300)
        self.fade_anim.setStartValue(0)
        self.fade_anim.setEndValue(1)
        self.fade_anim.start()
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Animated title
        title = QLabel("NetCluster")
        title.setStyleSheet(f"font-size: 28px; font-weight: 700; color: {ACCENT_CYAN};")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Version with glow
        version = QLabel(f"Version {VERSION}")
        version.setStyleSheet(f"font-size: 14px; color: {SUCCESS_GREEN}; font-weight: 600;")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)
        
        # Description
        desc = QLabel(
            "Distributed Network Security Platform\n\n"
            "Enterprise-grade master-worker architecture for "
            "advanced network security operations and testing."
        )
        desc.setStyleSheet(f"font-size: 13px; color: {TEXT_SECONDARY}; line-height: 1.6;")
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        layout.addStretch()
        
        btn = QDialogButtonBox(QDialogButtonBox.Ok)
        btn.accepted.connect(self.close_animation)
        btn.setStyleSheet(get_secondary_button_style())
        layout.addWidget(btn)

    def close_animation(self):
        self.fade_anim.setDirection(QPropertyAnimation.Backward)
        self.fade_anim.finished.connect(self.accept)
        self.fade_anim.start()


class LauncherWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NetCluster - Distributed Network Security Platform")
        self.setGeometry(200, 100, 1000, 750)
        self.setMinimumSize(800, 600)
        self._is_maximized = False
        self._normal_geometry = None
        self.setup_ui()

    def setup_ui(self):
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Enhanced title bar with glass effect
        title_bar = QFrame()
        title_bar.setFixedHeight(45)
        title_bar.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(30, 41, 59, 0.95),
                    stop:1 rgba(15, 23, 42, 0.95));
                border-bottom: 2px solid {ACCENT_CYAN};
            }}
        """)
        title_bar.setObjectName("TitleBar")
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(20, 0, 15, 0)
        
        # Logo with animation
        logo_label = QLabel("◉")
        logo_label.setStyleSheet(f"font-size: 22px; color: {ACCENT_CYAN};")
        title_bar_layout.addWidget(logo_label)
        
        title_label = QLabel("NetCluster")
        title_label.setStyleSheet(f"font-size: 15px; font-weight: 600; color: {TEXT_PRIMARY}; letter-spacing: 1px;")
        title_bar_layout.addWidget(title_label)
        
        version_badge = QLabel(f"v{VERSION}")
        version_badge.setStyleSheet(f"""
            font-size: 11px; 
            color: {TEXT_MUTED}; 
            background: rgba(0,212,255,0.1); 
            padding: 3px 10px; 
            border-radius: 12px;
            border: 1px solid {ACCENT_CYAN};
        """)
        title_bar_layout.addWidget(version_badge)
        
        title_bar_layout.addStretch()
        
        # Window controls with hover animations
        about_btn = QPushButton("About")
        about_btn.setStyleSheet(get_secondary_button_style() + " QPushButton { padding: 6px 16px; font-size: 12px; border-radius: 6px; }")
        about_btn.setCursor(Qt.PointingHandCursor)
        about_btn.clicked.connect(self._show_about)
        title_bar_layout.addWidget(about_btn)
        
        for btn_text, btn_action in [("─", self.showMinimized), ("□", self._toggle_maximize), ("✕", self.close)]:
            btn = QPushButton(btn_text)
            btn.setFixedSize(38, 30)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #94a3b8;
                    border: none;
                    border-radius: 6px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background: rgba(0,212,255,0.1);
                    color: #00d4ff;
                }
                QPushButton:pressed {
                    background: rgba(0,212,255,0.2);
                }
            """)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(btn_action)
            title_bar_layout.addWidget(btn)
        
        main_layout.addWidget(title_bar)

        # Content area with animated background
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Animated background
        self.background = AnimatedBackground(content_container)
        self.background.lower()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setAlignment(Qt.AlignCenter)
        scroll_layout.setContentsMargins(60, 50, 60, 60)
        scroll_layout.setSpacing(25)

        # Animated logo with typewriter effect
        logo_container = QWidget()
        logo_layout = QVBoxLayout(logo_container)
        logo_layout.setSpacing(10)
        
        # Animated title
        self.title_label = TypewriterLabel("NetCluster")
        logo_layout.addWidget(self.title_label)
        
        # Animated subtitle
        subtitle = QLabel("Distributed Network Security Platform")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(f"""
            font-size: 16px; 
            color: {ACCENT_CYAN}; 
            font-weight: 400;
            letter-spacing: 2px;
            text-transform: uppercase;
        """)
        
        # Add underline animation
        underline = QFrame()
        underline.setFixedHeight(2)
        underline.setStyleSheet(f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 transparent, stop:0.5 {ACCENT_CYAN}, stop:1 transparent);")
        
        logo_layout.addWidget(subtitle)
        logo_layout.addWidget(underline)
        logo_layout.setAlignment(underline, Qt.AlignCenter)
        
        scroll_layout.addWidget(logo_container)

        # Animated prompt
        prompt_container = QWidget()
        prompt_layout = QVBoxLayout(prompt_container)
        prompt_layout.setSpacing(5)
        
        prompt = QLabel("Select Node Type to Launch")
        prompt.setAlignment(Qt.AlignCenter)
        prompt.setStyleSheet(f"font-size: 15px; color: {TEXT_SECONDARY}; padding: 10px;")
        prompt_layout.addWidget(prompt)
        
        # Animated dots
        dots_layout = QHBoxLayout()
        for _ in range(3):
            dot = QLabel("●")
            dot.setStyleSheet(f"font-size: 8px; color: {ACCENT_CYAN};")
            dots_layout.addWidget(dot)
        dots_layout.setAlignment(Qt.AlignCenter)
        prompt_layout.addLayout(dots_layout)
        
        scroll_layout.addWidget(prompt_container)

        # Animated buttons
        self.master_btn = AnimatedNodeButton("MASTER NODE", ACCENT_CYAN, "⚡")
        self.master_btn.setToolTip("Launch Master Node - Central Controller")
        self.master_btn.clicked.connect(self.launch_master)
        scroll_layout.addWidget(self.master_btn, alignment=Qt.AlignCenter)

        self.worker_btn = AnimatedNodeButton("WORKER NODE", SUCCESS_GREEN, "🌐")
        self.worker_btn.setToolTip("Launch Worker Node - Distributed Processing")
        self.worker_btn.clicked.connect(self.launch_worker)
        scroll_layout.addWidget(self.worker_btn, alignment=Qt.AlignCenter)

        # Footer with animation
        footer = QLabel("⚡ Secure • Fast • Distributed ⚡")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet(f"""
            font-size: 13px; 
            color: {TEXT_MUTED}; 
            padding: 20px;
            border-top: 1px solid {BORDER_SUBTLE};
        """)
        scroll_layout.addWidget(footer)

        scroll.setWidget(scroll_widget)
        content_layout.addWidget(scroll)
        main_layout.addWidget(content_container, 1)

        # Window dragging
        self.old_pos = None
        QShortcut(QKeySequence("Escape"), self, self.close)

        def _title_press(e):
            if e.button() == Qt.LeftButton:
                self.old_pos = e.globalPos()

        def _title_move(e):
            if self.old_pos and not self._is_maximized:
                self.move(self.pos() + e.globalPos() - self.old_pos)
                self.old_pos = e.globalPos()

        def _title_release(e):
            self.old_pos = None

        title_bar.mousePressEvent = _title_press
        title_bar.mouseMoveEvent = _title_move
        title_bar.mouseReleaseEvent = _title_release

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.background.setGeometry(0, 0, self.centralWidget().width(), self.centralWidget().height())

    def _show_about(self):
        AboutDialog(self).exec_()

    def _toggle_maximize(self):
        if self._is_maximized:
            self.showNormal()
            if self._normal_geometry:
                self.setGeometry(self._normal_geometry)
            self._is_maximized = False
        else:
            self._normal_geometry = self.geometry()
            self.showMaximized()
            self._is_maximized = True

    def launch_master(self):
        """Launch Master Node with exit animation"""
        self.fade_out_and_launch("netcluster.core.master")

    def launch_worker(self):
        """Launch Worker Node with exit animation"""
        self.fade_out_and_launch("netcluster.core.worker")

    def fade_out_and_launch(self, module_name):
        """Fade out window and launch target module"""
        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)
        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_anim.setDuration(300)
        self.fade_anim.setStartValue(1)
        self.fade_anim.setEndValue(0)
        self.fade_anim.finished.connect(lambda: self.launch_module(module_name))
        self.fade_anim.start()

    def launch_module(self, module_name):
        """Launch the target module and close launcher"""
        try:
            subprocess.Popen([sys.executable, "-m", module_name])
            self.close()
        except Exception as e:
            print(f"Error launching {module_name}: {e}")
            self.close()


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(get_global_app_style())
    app.setApplicationName("NetCluster")
    app.setApplicationVersion(VERSION)
    app.setOrganizationName("NetCluster Security")
    
    win = LauncherWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
