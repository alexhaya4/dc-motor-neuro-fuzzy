"""
Modern DC Motor Control GUI - Version 2.0
Complete implementation with all improvements integrated
"""

import sys
import time
import math
import numpy as np
from collections import deque
from queue import Queue, Empty
from threading import Lock
from typing import Optional, Dict, Any

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QGroupBox, QTabWidget,
                             QGridLayout, QTextEdit, QMessageBox, QComboBox,
                             QRadioButton, QButtonGroup, QCheckBox, QFileDialog,
                             QSpinBox, QDoubleSpinBox, QScrollArea, QFrame)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QFont

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Import our improved modules
from config import get_config, is_raspberry_pi
from logger_utils import get_logger
from modern_theme import ModernTheme
from animated_widgets import (AnimatedCard, CircularGauge, StatusIndicator,
                              PulseButton, SmoothSlider, AnimatedProgressBar)
from conventional_controllers import PIController, PIDController
from fuzzy_controller import FuzzyController
from neural_tuned_fuzzy_controller import NeuralTunedFuzzyController
from constants import (
    SETTLING_TIME_TOLERANCE_PERCENT,
    STEADY_STATE_SAMPLES,
    STEADY_STATE_START_TIME_SEC,
    SPEED_SENSOR_SMOOTHING_SAMPLES,
    SPEED_MEASUREMENT_DURATION_SEC,
    SENSOR_POLL_INTERVAL_SEC,
    CONTROL_LOOP_INTERVAL_SEC,
    PLOT_MAX_POINTS,
    MAX_LOG_FILE_READ_BYTES,
    OVERSHOOT_PENALTY_MULTIPLIER,
    OVERSHOOT_MAX_PENALTY,
    SETTLING_TIME_PENALTY_MULTIPLIER,
    SETTLING_TIME_MAX_PENALTY,
    STEADY_STATE_ERROR_PENALTY_MULTIPLIER,
    STEADY_STATE_ERROR_MAX_PENALTY,
    MAX_PERFORMANCE_SCORE,
    WATCHDOG_TIMEOUT_SEC,
    WATCHDOG_CHECK_INTERVAL_SEC,
    SPEED_SENSOR_SLEEP_MICROSEC
)

from motor_hardware import MotorHardware
from control_runtime import ThreadSafeSpeedSensor, ThreadSafeController
from performance_metrics import PerformanceMetrics

logger = get_logger(__name__)


class RealTimePlotWidget(FigureCanvas):
    """Real-time plotting with matplotlib"""

    def __init__(self, parent=None, width=8, height=4):
        self.fig = Figure(figsize=(width, height), dpi=100)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)

        # Data buffers (use constant for max points)
        self.time_data = deque(maxlen=PLOT_MAX_POINTS)
        self.target_data = deque(maxlen=PLOT_MAX_POINTS)
        self.actual_data = deque(maxlen=PLOT_MAX_POINTS)
        self.error_data = deque(maxlen=PLOT_MAX_POINTS)

        # For blitting optimization
        self.line_target = None
        self.line_actual = None
        self.background = None

        self.start_time = time.monotonic()

        self.configured_window = get_config().gui.max_time_window_sec
        # Initialize plot
        self.setup_plot()

    def setup_plot(self):
        """Setup plot appearance"""
        self.ax.set_xlabel('Time (s)', fontsize=10)
        self.ax.set_ylabel('Speed (%)', fontsize=10)
        self.ax.set_title('Speed vs Time', fontsize=12, fontweight='bold')
        self.ax.grid(True, alpha=0.3, linestyle='--')
        self.ax.set_ylim(0, 110)

    def update_data(self, target: float, actual: float):
        current_time = time.monotonic() - self.start_time
        self.time_data.append(current_time)
        self.target_data.append(target)
        self.actual_data.append(actual)
        self.error_data.append(target - actual)
        if self.line_target is None:
            self.line_target, = self.ax.plot([], [], 'b--', label='Target')
            self.line_actual, = self.ax.plot([], [], 'g-', label='Actual')
            self.ax.legend(loc='upper right', fontsize=9)
        self.line_target.set_data(list(self.time_data), list(self.target_data))
        self.line_actual.set_data(list(self.time_data), list(self.actual_data))
        self.ax.set_xlim(max(0, current_time - self.configured_window), max(self.configured_window, current_time))
        self.draw_idle()

    def clear_data(self):
        """Clear all data"""
        self.time_data.clear()
        self.target_data.clear()
        self.actual_data.clear()
        self.error_data.clear()
        self.start_time = time.monotonic()

        # Reset blitting cache
        self.line_target = None
        self.line_actual = None
        self.background = None

        self.ax.clear()
        self.setup_plot()
        self.draw()


class ModernMotorControlGUI(QMainWindow):
    """Modern DC Motor Control GUI with all improvements"""

    def __init__(self, offline=False):
        super().__init__()

        self.offline = offline
        self.config = get_config()
        self.config.setup_logging()

        logger.info("=" * 60)
        logger.info("DC Motor Control - Starting")
        logger.info("=" * 60)

        # Motor PWM instance (not global)
        self.motor_pwm = None


        # Initialize controllers
        self.controllers = {
            'PI': PIController(),
            'PID': PIDController(),
            'Fuzzy': FuzzyController(),
            'Neural-Tuned Fuzzy': NeuralTunedFuzzyController()
        }
        self.current_controller_name = 'Neural-Tuned Fuzzy'
        self.current_controller = self.controllers['Neural-Tuned Fuzzy']

        # Threads
        self.speed_sensor = None
        self.controller_thread = None

        # UI Setup
        self.setWindowTitle("DC Motor Control")
        self.setMinimumSize(min(960, self.config.gui.window_width), min(640, self.config.gui.window_height))
        self.resize(self.config.gui.window_width, self.config.gui.window_height)

        self.setup_ui()
        self.apply_theme(self.config.gui.theme)
        self.on_controller_changed(3)

        # Hardware is opened only after controller and UI initialization succeeds.
        try:
            self.init_hardware()
            self.start_threads()
        except Exception:
            if self.controller_thread is not None:
                self.controller_thread.stop()
                self.controller_thread.wait()
            if self.speed_sensor is not None:
                self.speed_sensor.stop()
                self.speed_sensor.wait()
            if self.motor_pwm is not None:
                self.motor_pwm.stop()
            raise
        if self.offline:
            self.start_button.setEnabled(False)
            self.motor_status.setText("Motor: DISCONNECTED (offline)")
            self.actual_label.setText("Actual: unavailable")
            self.pwm_label.setText("PWM: unavailable")
            self.error_label.setText("Error: unavailable")

        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(self.config.gui.plot_update_interval_ms)

        logger.info("GUI initialized successfully")

    def init_hardware(self):
        """Open real hardware unless the user selected offline inspection."""
        if not self.offline:
            self.motor_pwm = MotorHardware(self.config)

    def setup_ui(self):
        """Setup the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # Top bar
        top_bar = self.create_top_bar()
        main_layout.addWidget(top_bar)

        # Dashboard
        dashboard = self.create_dashboard()
        main_layout.addWidget(dashboard)

        # Tabs
        tabs = self.create_tabs()
        main_layout.addWidget(tabs, stretch=1)

        # Status bar
        self.statusBar().showMessage("Ready")

    def create_top_bar(self):
        """Create top bar with title and controls"""
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)

        # Title
        title = QLabel("DC Motor Control")
        title.setObjectName("heading")
        layout.addWidget(title)

        layout.addStretch()

        # Theme selector
        theme_label = QLabel("Theme:")
        layout.addWidget(theme_label)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(['Modern Light', 'Modern Dark', 'Classic'])
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
        layout.addWidget(self.theme_combo)

        return bar

    def create_dashboard(self):
        """Create main dashboard"""
        dashboard = QWidget()
        layout = QHBoxLayout(dashboard)
        layout.setSpacing(16)

        # Status Card
        status_card = self.create_status_card()
        layout.addWidget(status_card)

        # Speed Gauge Card
        gauge_card = self.create_gauge_card()
        layout.addWidget(gauge_card)

        # Metrics Card
        metrics_card = self.create_metrics_card()
        layout.addWidget(metrics_card)

        dashboard.setFixedHeight(320)
        return dashboard

    def create_status_card(self):
        """Create system status card"""
        card = AnimatedCard("System Status")
        layout = QVBoxLayout()
        card.layout().addLayout(layout)

        # Status indicators
        self.motor_status = StatusIndicator("Motor")
        self.sensor_status = StatusIndicator("Sensor")
        self.controller_status = StatusIndicator("Controller")

        layout.addWidget(self.motor_status)
        layout.addWidget(self.sensor_status)
        layout.addWidget(self.controller_status)

        layout.addSpacing(16)

        # Current controller
        self.controller_label = QLabel("Controller: Neural-Tuned Fuzzy")
        self.controller_label.setObjectName("subheading")
        layout.addWidget(self.controller_label)

        # Neural-Tuned Fuzzy status (if applicable)
        self.neural_tuned_status_label = QLabel("")
        self.neural_tuned_status_label.setObjectName("caption")
        layout.addWidget(self.neural_tuned_status_label)

        layout.addStretch()

        return card

    def create_gauge_card(self):
        """Create speed gauge card"""
        card = AnimatedCard("Current Speed")
        layout = QVBoxLayout()
        card.layout().addLayout(layout)

        self.speed_gauge = CircularGauge()
        self.speed_gauge.setRange(0, 100)
        self.speed_gauge.setAvailable(False)
        self.speed_gauge.setUnit("%")
        layout.addWidget(self.speed_gauge, alignment=Qt.AlignCenter)

        return card

    def create_metrics_card(self):
        """Create performance metrics card"""
        card = AnimatedCard("Real-Time Metrics")
        layout = QVBoxLayout()
        card.layout().addLayout(layout)

        # Metrics labels
        self.target_label = QLabel("Target: 0.0%")
        self.actual_label = QLabel("Actual: 0.0%")
        self.error_label = QLabel("Error: 0.0%")
        self.pwm_label = QLabel("PWM: 0.0%")

        for label in [self.target_label, self.actual_label, self.error_label, self.pwm_label]:
            layout.addWidget(label)

        layout.addSpacing(12)

        # PWM progress bar
        pwm_bar_label = QLabel("PWM Output:")
        layout.addWidget(pwm_bar_label)

        self.pwm_bar = AnimatedProgressBar()
        self.pwm_bar.setRange(0, 100)
        layout.addWidget(self.pwm_bar)

        layout.addStretch()

        return card

    def create_tabs(self):
        """Create tabbed interface"""
        tabs = QTabWidget()

        for content, title in [(self.create_control_tab(), 'Control'),
                               (self.create_plot_tab(), 'Real-Time Plot'),
                               (self.create_tuning_tab(), 'Tuning'),
                               (self.create_performance_tab(), 'Performance'),
                               (self.create_settings_tab(), 'Settings'),
                               (self.create_logs_tab(), 'Logs')]:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            scroll.setWidget(content)
            tabs.addTab(scroll, title)

        return tabs

    def create_control_tab(self):
        """Create control tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)

        # Target speed control
        target_card = AnimatedCard("Target Speed Control")
        target_layout = QVBoxLayout()
        target_card.layout().addLayout(target_layout)

        self.target_slider = SmoothSlider(0, 100, "Target Speed", "%")
        target_layout.addWidget(self.target_slider)

        layout.addWidget(target_card)

        # Motor control buttons
        buttons_card = AnimatedCard("Motor Control")
        buttons_layout = QHBoxLayout()
        buttons_card.layout().addLayout(buttons_layout)

        self.start_button = PulseButton("Start Motor")
        self.start_button.setObjectName("success")
        self.start_button.clicked.connect(self.start_motor)
        buttons_layout.addWidget(self.start_button)

        self.stop_button = PulseButton("Stop Motor")
        self.stop_button.setObjectName("error")
        self.stop_button.clicked.connect(self.stop_motor)
        buttons_layout.addWidget(self.stop_button)

        self.reset_button = PulseButton("Reset")
        self.reset_button.setObjectName("secondary")
        self.reset_button.clicked.connect(self.reset_controller)
        buttons_layout.addWidget(self.reset_button)

        layout.addWidget(buttons_card)

        # Controller selection
        controller_card = AnimatedCard("Controller Selection")
        controller_layout = QVBoxLayout()
        controller_card.layout().addLayout(controller_layout)

        self.controller_group = QButtonGroup()

        controllers = [
            ("PI Controller", "Proportional and integral feedback"),
            ("PID Controller", "Proportional, integral and filtered derivative"),
            ("Fuzzy Controller", "Mamdani fuzzy inference"),
            ("Neural-Tuned Fuzzy Controller", "Learned scaling when verified models are available")
        ]

        for i, (name, desc) in enumerate(controllers):
            radio = QRadioButton(name)
            if i == 3:  # Neural-Tuned Fuzzy selected by default
                radio.setChecked(True)
            self.controller_group.addButton(radio, i)
            radio.toggled.connect(lambda checked, idx=i: self.on_controller_changed(idx) if checked else None)
            controller_layout.addWidget(radio)

            desc_label = QLabel(f"  └─ {desc}")
            desc_label.setObjectName("caption")
            controller_layout.addWidget(desc_label)

        layout.addWidget(controller_card)

        layout.addStretch()

        return tab

    def create_plot_tab(self):
        """Create real-time plot tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Plot widget
        self.plot_widget = RealTimePlotWidget(tab, width=10, height=6)
        layout.addWidget(self.plot_widget)

        # Plot controls
        controls_layout = QHBoxLayout()

        clear_plot_btn = PulseButton("Clear Plot")
        clear_plot_btn.clicked.connect(self.plot_widget.clear_data)
        controls_layout.addWidget(clear_plot_btn)

        controls_layout.addStretch()

        layout.addLayout(controls_layout)

        return tab

    def create_tuning_tab(self):
        """Create tuning tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)

        # PI/PID Tuning
        pid_card = AnimatedCard("PID Parameters")
        pid_layout = QGridLayout()
        pid_card.layout().addLayout(pid_layout)

        # Kp
        pid_layout.addWidget(QLabel("Kp (Proportional):"), 0, 0)
        self.kp_spin = QDoubleSpinBox()
        self.kp_spin.setRange(0, 10)
        self.kp_spin.setSingleStep(0.1)
        self.kp_spin.setValue(self.config.controller.pid_kp)
        pid_layout.addWidget(self.kp_spin, 0, 1)

        # Ki
        pid_layout.addWidget(QLabel("Ki (Integral):"), 1, 0)
        self.ki_spin = QDoubleSpinBox()
        self.ki_spin.setRange(0, 5)
        self.ki_spin.setSingleStep(0.01)
        self.ki_spin.setValue(self.config.controller.pid_ki)
        pid_layout.addWidget(self.ki_spin, 1, 1)

        # Kd
        pid_layout.addWidget(QLabel("Kd (Derivative):"), 2, 0)
        self.kd_spin = QDoubleSpinBox()
        self.kd_spin.setRange(0, 1)
        self.kd_spin.setSingleStep(0.01)
        self.kd_spin.setValue(self.config.controller.pid_kd)
        pid_layout.addWidget(self.kd_spin, 2, 1)

        apply_btn = PulseButton("Apply Parameters")
        apply_btn.clicked.connect(self.apply_pid_parameters)
        pid_layout.addWidget(apply_btn, 3, 0, 1, 2)

        layout.addWidget(pid_card)

        layout.addStretch()

        return tab

    def create_performance_tab(self):
        """Create performance metrics tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        metrics_card = AnimatedCard("Performance Metrics")
        metrics_layout = QGridLayout()
        metrics_card.layout().addLayout(metrics_layout)

        self.overshoot_label = QLabel("Overshoot: -")
        self.settling_label = QLabel("Settling Time: -")
        self.ss_error_label = QLabel("Steady-State Error: -")
        self.score_label = QLabel("Composite score: not defined")

        metrics_layout.addWidget(QLabel("Metric"), 0, 0)
        metrics_layout.addWidget(QLabel("Value"), 0, 1)
        metrics_layout.addWidget(self.overshoot_label, 1, 0, 1, 2)
        metrics_layout.addWidget(self.settling_label, 2, 0, 1, 2)
        metrics_layout.addWidget(self.ss_error_label, 3, 0, 1, 2)
        metrics_layout.addWidget(self.score_label, 4, 0, 1, 2)

        calc_btn = PulseButton("Calculate Metrics")
        calc_btn.clicked.connect(self.calculate_metrics)
        metrics_layout.addWidget(calc_btn, 5, 0, 1, 2)

        layout.addWidget(metrics_card)
        layout.addStretch()

        return tab

    def create_settings_tab(self):
        """Create settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        settings_card = AnimatedCard("System Settings")
        settings_layout = QGridLayout()
        settings_card.layout().addLayout(settings_layout)

        # Max RPM
        settings_layout.addWidget(QLabel("Max RPM:"), 0, 0)
        max_rpm_spin = QSpinBox()
        max_rpm_spin.setRange(10, 10000)
        max_rpm_spin.setValue(self.config.motor.max_rpm)
        settings_layout.addWidget(max_rpm_spin, 0, 1)

        # Log level
        settings_layout.addWidget(QLabel("Log Level:"), 1, 0)
        log_combo = QComboBox()
        log_combo.addItems(['DEBUG', 'INFO', 'WARNING', 'ERROR'])
        log_combo.setCurrentText(self.config.logging.level)
        settings_layout.addWidget(log_combo, 1, 1)

        layout.addWidget(settings_card)
        layout.addStretch()

        return tab

    def create_logs_tab(self):
        """Create logs display tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self.log_text)

        # Load logs button
        load_btn = PulseButton("Load Latest Logs")
        load_btn.clicked.connect(self.load_logs)
        layout.addWidget(load_btn)

        return tab

    def start_threads(self):
        if self.offline:
            return
        self.controller_thread = ThreadSafeController(self.current_controller, self.config, self.motor_pwm)
        self.controller_thread.pwm_updated.connect(self.on_pwm_updated)
        self.controller_thread.metrics_updated.connect(self.on_metrics_updated)
        self.controller_thread.faulted.connect(self.on_control_fault)
        self.speed_sensor = ThreadSafeSpeedSensor(self.config, self.motor_pwm)
        self.speed_sensor.speed_updated.connect(self.on_speed_updated)
        self.speed_sensor.faulted.connect(self.on_control_fault)
        self.controller_thread.start()
        self.speed_sensor.start()

    def on_control_fault(self, reason):
        self.stop_motor()
        self.motor_status.setText("Motor: STOPPED - " + reason)
        if self.controller_thread and not math.isfinite(self.controller_thread.current_pwm):
            self.pwm_label.setText('PWM: unavailable')
        logger.error(reason)

    def apply_theme(self, theme_name: str):
        """Apply theme to application"""
        theme_map = {
            'modern': 'modern_light',
            'modern_light': 'modern_light',
            'modern_dark': 'modern_dark',
            'dark': 'modern_dark',
            'Modern Light': 'modern_light',
            'Modern Dark': 'modern_dark',
            'Classic': 'classic'
        }
        theme = theme_map.get(theme_name, 'modern_light')

        QApplication.instance().setStyleSheet(ModernTheme.get_stylesheet(theme))
        QApplication.instance().setPalette(ModernTheme.get_palette(theme))

        logger.info(f"Theme changed to {theme_name}")

    def on_theme_changed(self, theme_name: str):
        """Handle theme change"""
        self.apply_theme(theme_name)

    def on_controller_changed(self, index: int):
        """Handle controller change"""
        controller_names = ['PI', 'PID', 'Fuzzy', 'Neural-Tuned Fuzzy']
        self.current_controller_name = controller_names[index]
        self.current_controller = self.controllers[self.current_controller_name]

        # Update controller thread
        if self.controller_thread:
            self.controller_thread.set_controller(self.current_controller)

        # Update UI
        self.controller_label.setText(f"Controller: {self.current_controller_name}")

        # Update Neural-Tuned Fuzzy status
        if self.current_controller_name == 'Neural-Tuned Fuzzy':
            status = self.current_controller.get_scaling_factors()
            mode = "Neural Networks Active" if status['using_neural_networks'] else "Fuzzy-Only Mode"
            self.neural_tuned_status_label.setText(f"└─ {mode}")
        else:
            self.neural_tuned_status_label.setText("")

        logger.info(f"Controller changed to {self.current_controller_name}")

    def on_speed_updated(self, speed: float, sampled_at: float):
        """Handle speed sensor update"""
        if self.controller_thread:
            self.controller_thread.update_current_speed(speed, sampled_at)

    def on_pwm_updated(self, pwm: float):
        """Handle PWM update from controller"""
        self.pwm_label.setText(f"PWM: {pwm:.1f}%" if math.isfinite(pwm) else 'PWM: unavailable')
        self.pwm_bar.setValueAnimated(int(pwm) if math.isfinite(pwm) else 0)

    def on_metrics_updated(self, metrics):
        def show(value, unit):
            return f"{value:.2f}{unit}" if value is not None else "Unavailable"
        self.overshoot_label.setText("Overshoot: " + show(metrics['overshoot'], "%"))
        self.settling_label.setText("Settling Time: " + show(metrics['settling_time'], "s"))
        self.ss_error_label.setText("Steady-State Error: " + show(metrics['ss_error'], "%"))
        self.score_label.setText("Composite score: not defined")

    def update_display(self):
        """Update display with current values (thread-safe)"""
        if not self.controller_thread:
            return

        # Get current values
        target = self.target_slider.value()

        # Copy a coherent snapshot of measured feedback and commanded output.
        with self.controller_thread.state_lock:
            current = self.controller_thread.current_speed
            motor_enabled = self.controller_thread.motor_enabled
            pwm = self.controller_thread.current_pwm
            sampled_at = self.controller_thread.last_update_time

        # Update target if changed
        self.controller_thread.set_target_speed(target)

        if sampled_at is None or time.monotonic() - sampled_at > WATCHDOG_TIMEOUT_SEC:
            self.speed_gauge.setAvailable(False)
            self.actual_label.setText('Actual: unavailable')
            self.error_label.setText('Error: unavailable')
            self.sensor_status.setStatus('inactive')
            return
        self.speed_gauge.setAvailable(True)
        # Update gauge
        self.speed_gauge.setValue(current, animated=True)

        # Update labels
        self.target_label.setText(f"Target: {target:.1f}%")
        self.actual_label.setText(f"Actual: {current:.1f}%")

        error = target - current
        self.error_label.setText(f"Error: {error:+.1f}%")

        # Display the value actually written by the controller worker.
        self.pwm_label.setText(f"PWM: {pwm:.1f}%" if math.isfinite(pwm) else 'PWM: unavailable')
        self.pwm_bar.setValueAnimated(int(pwm) if math.isfinite(pwm) else 0)

        # Update plot
        if sampled_at != getattr(self, '_plotted_sample', None):
            self.plot_widget.update_data(target, current)
            self._plotted_sample = sampled_at

        # Update status indicators
        self.sensor_status.setStatus("ok" if motor_enabled else "inactive")
        self.controller_status.setStatus("ok" if motor_enabled else "inactive")

    def start_motor(self):
        """Start motor"""
        if not self.controller_thread or not self.controller_thread.enable_motor():
            return

        self.start_button.start_pulse()
        self.motor_status.setStatus("ok")
        self.motor_status.setText("Motor: RUNNING")

        logger.info("Motor started")

    def stop_motor(self):
        """Stop motor"""
        if self.controller_thread:
            self.controller_thread.disable_motor()

        self.start_button.stop_pulse()
        self.motor_status.setStatus("inactive")
        self.motor_status.setText("Motor: STOPPED")

        logger.info("Motor stopped")

    def reset_controller(self):
        """Reset controller"""
        if self.controller_thread:
            self.controller_thread.reset_controller()

        self.plot_widget.clear_data()

        logger.info("Controller reset")

    def apply_pid_parameters(self):
        """Apply PID parameters"""
        kp = self.kp_spin.value()
        ki = self.ki_spin.value()
        kd = self.kd_spin.value()

        # Update PID controller
        self.controllers['PID'] = PIDController(kp=kp, ki=ki, kd=kd)

        # If currently using PID, update thread
        if self.current_controller_name == 'PID':
            self.current_controller = self.controllers['PID']
            if self.controller_thread:
                self.controller_thread.set_controller(self.current_controller)

        logger.info(f"PID parameters updated: Kp={kp}, Ki={ki}, Kd={kd}")

        QMessageBox.information(self, "Success", "PID parameters applied successfully!")

    def calculate_metrics(self):
        """Calculate and display performance metrics"""
        if self.controller_thread:
            self.controller_thread.request_metrics()

    def load_logs(self):
        """Load logs from file with size limit for safety"""
        log_file = self.config.paths.logs_dir / "motor_control.log"

        if log_file.exists():
            try:
                # Check file size to prevent memory exhaustion
                file_size = log_file.stat().st_size

                if file_size > MAX_LOG_FILE_READ_BYTES:
                    # Read only the last N bytes
                    with open(log_file, 'rb') as f:
                        f.seek(-MAX_LOG_FILE_READ_BYTES, 2)  # Seek from end
                        logs = f.read().decode('utf-8', errors='ignore')
                        # Find first complete line
                        first_newline = logs.find('\n')
                        if first_newline != -1:
                            logs = logs[first_newline + 1:]
                        self.log_text.setPlainText(
                            f"[Showing last {MAX_LOG_FILE_READ_BYTES} bytes of {file_size} total]\n\n" + logs
                        )
                else:
                    # File is small enough, read all
                    with open(log_file, 'r', encoding='utf-8') as f:
                        logs = f.read()
                        self.log_text.setPlainText(logs)

                # Scroll to bottom
                cursor = self.log_text.textCursor()
                cursor.movePosition(cursor.End)
                self.log_text.setTextCursor(cursor)

            except (OSError, IOError, UnicodeDecodeError) as e:
                self.log_text.setPlainText(f"Error reading log file: {e}")
        else:
            self.log_text.setPlainText("No log file found.")

    def closeEvent(self, event):
        """Clean up on close"""
        logger.info("Shutting down...")

        self.update_timer.stop()
        # Disable output before waiting for sensor shutdown.
        if self.controller_thread:
            self.controller_thread.stop()
        if self.speed_sensor:
            self.speed_sensor.stop()
            self.speed_sensor.wait()

        if self.controller_thread:
            self.controller_thread.stop()
            self.controller_thread.wait()

        # Cleanup GPIO
        if self.motor_pwm:
            try:
                self.motor_pwm.stop()
            except Exception:
                logger.critical('GPIO cleanup failed; disconnect motor power', exc_info=True)
                QMessageBox.critical(self, 'Motor shutdown error', 'GPIO cleanup failed. Disconnect motor power before leaving the rig.')

        logger.info("Application shutdown complete")

        event.accept()


def main():
    """Main entry point"""
    import argparse
    parser = argparse.ArgumentParser(description="DC motor control with measured hardware feedback")
    parser.add_argument('--offline', action='store_true', help='Inspect the GUI without motor I/O or generated sensor readings')
    args = parser.parse_args()
    app = QApplication([sys.argv[0]])

    # Set application font
    app.setFont(ModernTheme.get_font())

    # Create and show window
    try:
        window = ModernMotorControlGUI(offline=args.offline)
    except (RuntimeError, ImportError, OSError) as exc:
        print(f"Startup failed: {exc}", file=sys.stderr)
        sys.exit(1)
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
