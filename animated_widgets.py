"""
Animated Widgets with Smooth Transitions
Beautiful, fluid animations for modern GUI
"""

from PyQt5.QtWidgets import (QWidget, QLabel, QFrame, QVBoxLayout, QHBoxLayout,
                              QProgressBar, QPushButton, QGraphicsOpacityEffect)
from PyQt5.QtCore import (QPropertyAnimation, QEasingCurve, QParallelAnimationGroup,
                          QSequentialAnimationGroup, Qt, pyqtProperty, QTimer, QRect)
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QLinearGradient
from typing import Optional
import math


class AnimatedCard(QFrame):
    """Card widget with smooth hover effects and elevation"""

    def __init__(self, title: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("card")
        self._elevation = 2

        # Setup layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        if title:
            title_label = QLabel(title)
            title_label.setObjectName("subheading")
            layout.addWidget(title_label)

        # Opacity effect for fade animations
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self.opacity_effect)

        # Animation for hover
        self.hover_animation = QPropertyAnimation(self, b"elevation")
        self.hover_animation.setDuration(200)
        self.hover_animation.setEasingCurve(QEasingCurve.OutCubic)

    @pyqtProperty(int)
    def elevation(self):
        return self._elevation

    @elevation.setter
    def elevation(self, value):
        self._elevation = value
        self.update()

    def enterEvent(self, event):
        """Animate on mouse enter"""
        self.hover_animation.stop()
        self.hover_animation.setStartValue(self._elevation)
        self.hover_animation.setEndValue(8)
        self.hover_animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Animate on mouse leave"""
        self.hover_animation.stop()
        self.hover_animation.setStartValue(self._elevation)
        self.hover_animation.setEndValue(2)
        self.hover_animation.start()
        super().leaveEvent(event)

    def fade_in(self, duration: int = 300):
        """Fade in animation"""
        animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        animation.setDuration(duration)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.InOutCubic)
        animation.start()
        self._fade_animation = animation  # Keep reference

    def fade_out(self, duration: int = 300):
        """Fade out animation"""
        animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        animation.setDuration(duration)
        animation.setStartValue(1.0)
        animation.setEndValue(0.0)
        animation.setEasingCurve(QEasingCurve.InOutCubic)
        animation.start()
        self._fade_animation = animation


class AnimatedProgressBar(QProgressBar):
    """Progress bar with smooth value transitions"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._target_value = 0
        self._animation = QPropertyAnimation(self, b"value")
        self._animation.setDuration(500)
        self._animation.setEasingCurve(QEasingCurve.InOutCubic)

    def setValueAnimated(self, value: int):
        """Set value with smooth animation"""
        self._animation.stop()
        self._animation.setStartValue(self.value())
        self._animation.setEndValue(value)
        self._animation.start()


class CircularGauge(QWidget):
    """Circular gauge for displaying speed/RPM with animations"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._value = 0
        self._target_value = 0
        self._min_value = 0
        self._max_value = 100
        self._unit = "RPM"
        self._primary_color = QColor("#2196F3")
        self._background_color = QColor("#E0E0E0")

        self.setMinimumSize(200, 200)

        # Animation for smooth value changes
        self._animation = QPropertyAnimation(self, b"value")
        self._animation.setDuration(500)
        self._animation.setEasingCurve(QEasingCurve.InOutCubic)

    @pyqtProperty(float)
    def value(self):
        return self._value

    @value.setter
    def value(self, val):
        self._value = val
        self.update()

    def setValue(self, value: float, animated: bool = True):
        """Set gauge value with optional animation"""
        value = max(self._min_value, min(self._max_value, value))
        self._target_value = value

        if animated:
            self._animation.stop()
            self._animation.setStartValue(self._value)
            self._animation.setEndValue(value)
            self._animation.start()
        else:
            self._value = value
            self.update()

    def setRange(self, min_val: float, max_val: float):
        """Set gauge range"""
        self._min_value = min_val
        self._max_value = max_val

    def setUnit(self, unit: str):
        """Set display unit"""
        self._unit = unit

    def paintEvent(self, event):
        """Custom painting for circular gauge"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Calculate dimensions
        width = self.width()
        height = self.height()
        size = min(width, height)
        center_x = width / 2
        center_y = height / 2
        radius = (size - 40) / 2

        # Draw background arc
        painter.setPen(QPen(self._background_color, 15, Qt.SolidLine, Qt.RoundCap))
        start_angle = 135 * 16  # Start at bottom-left
        span_angle = 270 * 16   # 270 degrees arc
        rect = QRect(int(center_x - radius), int(center_y - radius),
                     int(radius * 2), int(radius * 2))
        painter.drawArc(rect, start_angle, span_angle)

        # Draw value arc
        value_ratio = (self._value - self._min_value) / (self._max_value - self._min_value)
        value_span = int(value_ratio * 270 * 16)

        # Gradient for value arc
        gradient = QLinearGradient(center_x - radius, center_y,
                                   center_x + radius, center_y)
        gradient.setColorAt(0, self._primary_color)
        gradient.setColorAt(1, self._primary_color.lighter(120))

        painter.setPen(QPen(gradient, 15, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(rect, start_angle, value_span)

        # Draw value text
        font = QFont("Segoe UI", 36, QFont.Bold)
        painter.setFont(font)
        painter.setPen(QColor("#212121"))
        painter.drawText(rect, Qt.AlignCenter,
                        f"{int(self._value)}")

        # Draw unit text
        font = QFont("Segoe UI", 12)
        painter.setFont(font)
        painter.setPen(QColor("#757575"))
        unit_rect = QRect(int(center_x - radius), int(center_y + 20),
                          int(radius * 2), 30)
        painter.drawText(unit_rect, Qt.AlignCenter, self._unit)


class PulseButton(QPushButton):
    """Button with pulse animation effect"""

    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self._pulse_active = False
        self._scale = 1.0

        # Scale animation
        self.scale_animation = QPropertyAnimation(self, b"scale")
        self.scale_animation.setDuration(150)
        self.scale_animation.setEasingCurve(QEasingCurve.OutCubic)

    @pyqtProperty(float)
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, value):
        self._scale = value
        self.update()

    def enterEvent(self, event):
        """Animate on hover"""
        self.scale_animation.stop()
        self.scale_animation.setStartValue(self._scale)
        self.scale_animation.setEndValue(1.05)
        self.scale_animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Animate on leave"""
        self.scale_animation.stop()
        self.scale_animation.setStartValue(self._scale)
        self.scale_animation.setEndValue(1.0)
        self.scale_animation.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """Animate on press"""
        self.scale_animation.stop()
        self.scale_animation.setStartValue(self._scale)
        self.scale_animation.setEndValue(0.95)
        self.scale_animation.setDuration(100)
        self.scale_animation.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Animate on release"""
        self.scale_animation.stop()
        self.scale_animation.setStartValue(self._scale)
        self.scale_animation.setEndValue(1.05 if self.underMouse() else 1.0)
        self.scale_animation.setDuration(150)
        self.scale_animation.start()
        super().mouseReleaseEvent(event)

    def start_pulse(self):
        """Start continuous pulse animation"""
        self._pulse_active = True
        self._pulse_loop()

    def stop_pulse(self):
        """Stop pulse animation"""
        self._pulse_active = False
        self.scale_animation.stop()
        self._scale = 1.0
        self.update()

    def _pulse_loop(self):
        """Internal pulse loop"""
        if not self._pulse_active:
            return

        # Pulse in
        pulse_in = QPropertyAnimation(self, b"scale")
        pulse_in.setDuration(800)
        pulse_in.setStartValue(1.0)
        pulse_in.setEndValue(1.1)
        pulse_in.setEasingCurve(QEasingCurve.InOutCubic)

        # Pulse out
        pulse_out = QPropertyAnimation(self, b"scale")
        pulse_out.setDuration(800)
        pulse_out.setStartValue(1.1)
        pulse_out.setEndValue(1.0)
        pulse_out.setEasingCurve(QEasingCurve.InOutCubic)

        # Sequential animation
        sequence = QSequentialAnimationGroup(self)
        sequence.addAnimation(pulse_in)
        sequence.addAnimation(pulse_out)
        sequence.finished.connect(self._pulse_loop)
        sequence.start()

        self._pulse_sequence = sequence  # Keep reference


class StatusIndicator(QWidget):
    """Animated status indicator (dot with label)"""

    def __init__(self, label: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._status = "inactive"  # inactive, ok, warning, error
        self._colors = {
            'inactive': QColor("#BDBDBD"),
            'ok': QColor("#4CAF50"),
            'warning': QColor("#FF9800"),
            'error': QColor("#F44336")
        }

        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Status dot
        self.dot = QLabel()
        self.dot.setFixedSize(12, 12)
        layout.addWidget(self.dot)

        # Label
        self.label = QLabel(label)
        layout.addWidget(self.label)

        layout.addStretch()

        self._update_dot()

        # Blink animation for warnings/errors
        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self._blink)
        self._blink_state = True

    def setStatus(self, status: str):
        """Set status (inactive, ok, warning, error)"""
        self._status = status
        self._update_dot()

        # Start blinking for warnings/errors
        if status in ['warning', 'error']:
            self.blink_timer.start(500)
        else:
            self.blink_timer.stop()
            self._blink_state = True
            self._update_dot()

    def setText(self, text: str):
        """Update label text"""
        self.label.setText(text)

    def _update_dot(self):
        """Update dot appearance"""
        color = self._colors.get(self._status, self._colors['inactive'])
        alpha = 255 if self._blink_state else 100

        self.dot.setStyleSheet(f"""
            QLabel {{
                background-color: rgba({color.red()}, {color.green()},
                                      {color.blue()}, {alpha});
                border-radius: 6px;
            }}
        """)

    def _blink(self):
        """Toggle blink state"""
        self._blink_state = not self._blink_state
        self._update_dot()


class SmoothSlider(QWidget):
    """Slider with smooth value display and animations"""

    def __init__(self, min_val: int = 0, max_val: int = 100,
                 label: str = "", unit: str = "",
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        from PyQt5.QtWidgets import QSlider

        self._value = min_val
        self._min = min_val
        self._max = max_val
        self._unit = unit

        # Layout
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Label row
        label_row = QHBoxLayout()
        self.label = QLabel(label)
        self.value_label = QLabel(f"{min_val} {unit}")
        self.value_label.setAlignment(Qt.AlignRight)
        label_row.addWidget(self.label)
        label_row.addWidget(self.value_label)
        layout.addLayout(label_row)

        # Slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(min_val)
        self.slider.setMaximum(max_val)
        self.slider.setValue(min_val)
        self.slider.valueChanged.connect(self._on_value_changed)
        layout.addWidget(self.slider)

        # Animation for value display
        self._animation = QPropertyAnimation(self, b"displayValue")
        self._animation.setDuration(150)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)

    @pyqtProperty(float)
    def displayValue(self):
        return self._value

    @displayValue.setter
    def displayValue(self, value):
        self._value = value
        self.value_label.setText(f"{value:.1f} {self._unit}")

    def _on_value_changed(self, value):
        """Handle slider value change with animation"""
        self._animation.stop()
        self._animation.setStartValue(self._value)
        self._animation.setEndValue(float(value))
        self._animation.start()

    def value(self):
        """Get current value"""
        return self.slider.value()

    def setValue(self, value: int):
        """Set value"""
        self.slider.setValue(value)
