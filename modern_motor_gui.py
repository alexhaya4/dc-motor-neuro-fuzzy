"""
Modern DC Motor Control GUI - Version 2.0
Complete implementation with all improvements integrated
"""

import sys
import time
import random  # Import at module level, not in hot loop
import numpy as np
from collections import deque
from queue import Queue, Empty
from threading import Lock
from typing import Optional, Dict, Any

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QGroupBox, QTabWidget,
                             QGridLayout, QTextEdit, QMessageBox, QComboBox,
                             QRadioButton, QButtonGroup, QCheckBox, QFileDialog,
                             QSpinBox, QDoubleSpinBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QFont

import matplotlib
matplotlib.use('Qt5Agg')
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
from anfis_controller import ANFISController
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

# Conditional GPIO import
if is_raspberry_pi():
    import RPi.GPIO as GPIO
else:
    # Mock GPIO for development
    class MockGPIO:
        BCM = 0
        OUT = 0
        IN = 1
        HIGH = 1
        LOW = 0

        @staticmethod
        def setmode(mode): pass
        @staticmethod
        def setup(pin, mode): pass
        @staticmethod
        def output(pin, state): pass
        @staticmethod
        def input(pin): return 0
        @staticmethod
        def setwarnings(flag): pass

        class PWM:
            def __init__(self, pin, freq): pass
            def start(self, duty): pass
            def ChangeDutyCycle(self, duty): pass
            def stop(self): pass

    GPIO = MockGPIO()


logger = get_logger(__name__)


class PerformanceMetrics:
    """Calculate and track controller performance metrics"""

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset all metrics"""
        self.start_time = time.time()
        self.target_reached_time = None
        self.max_value = 0
        self.min_value = 100
        self.steady_state_samples = []

    def update(self, target: float, actual: float):
        """Update metrics with new data point"""
        self.max_value = max(self.max_value, actual)
        self.min_value = min(self.min_value, actual)

        # Check if reached target (within tolerance)
        if self.target_reached_time is None:
            tolerance = target * (SETTLING_TIME_TOLERANCE_PERCENT / 100.0)
            if abs(actual - target) <= tolerance:
                self.target_reached_time = time.time()

        # Collect steady-state samples (after defined time)
        if time.time() - self.start_time > STEADY_STATE_START_TIME_SEC:
            self.steady_state_samples.append(actual - target)
            if len(self.steady_state_samples) > STEADY_STATE_SAMPLES:
                self.steady_state_samples.pop(0)

    def calculate(self, target: float) -> Dict[str, float]:
        """Calculate final metrics"""
        overshoot = max(0, (self.max_value - target) / target * 100) if target > 0 else 0

        settling_time = self.target_reached_time - self.start_time if self.target_reached_time else 0

        ss_error = np.mean(np.abs(self.steady_state_samples)) if self.steady_state_samples else 0

        # Calculate score using constants
        score = MAX_PERFORMANCE_SCORE
        score -= min(overshoot * OVERSHOOT_PENALTY_MULTIPLIER, OVERSHOOT_MAX_PENALTY)
        score -= min(settling_time * SETTLING_TIME_PENALTY_MULTIPLIER, SETTLING_TIME_MAX_PENALTY)
        score -= min(ss_error * STEADY_STATE_ERROR_PENALTY_MULTIPLIER, STEADY_STATE_ERROR_MAX_PENALTY)
        score = max(0, score)

        return {
            'overshoot': overshoot,
            'settling_time': settling_time,
            'ss_error': ss_error,
            'score': score
        }


class ThreadSafeSpeedSensor(QThread):
    """Thread-safe speed sensor with proper synchronization"""

    speed_updated = pyqtSignal(float)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.running = True
        self.lock = Lock()

        # Smoothing buffer
        self.rpm_history = deque(maxlen=SPEED_SENSOR_SMOOTHING_SAMPLES)

        logger.info("Speed sensor thread initialized")

    def run(self):
        """Main sensor loop"""
        while self.running:
            try:
                raw_rpm = self.measure_speed()

                with self.lock:
                    self.rpm_history.append(raw_rpm)
                    smoothed_rpm = sum(self.rpm_history) / len(self.rpm_history)

                self.speed_updated.emit(smoothed_rpm)
                time.sleep(SENSOR_POLL_INTERVAL_SEC)

            except (ValueError, TypeError, IOError) as e:
                logger.error(f"Speed sensor error: {e}")
                time.sleep(0.5)

    def measure_speed(self, duration: float = SPEED_MEASUREMENT_DURATION_SEC) -> float:
        """Measure speed by counting IR sensor pulses"""
        if not is_raspberry_pi():
            # Simulate speed for development (random imported at module level)
            return random.uniform(40, 60)

        pulse_count = 0
        last_state = GPIO.input(self.config.gpio.ir_sensor_pin)
        start_time = time.time()
        end_time = start_time + duration

        while time.time() < end_time:
            current_state = GPIO.input(self.config.gpio.ir_sensor_pin)
            if current_state == 0 and last_state == 1:
                pulse_count += 1
            last_state = current_state
            time.sleep(SPEED_SENSOR_SLEEP_MICROSEC)

        # Calculate RPM
        pulses_per_rev = self.config.motor.pulses_per_revolution
        rpm = (pulse_count / pulses_per_rev) * (60.0 / duration)

        # Convert to 0-100 scale
        max_rpm = self.config.motor.max_rpm
        speed_percent = min(100, (rpm / max_rpm) * 100)

        return speed_percent

    def stop(self):
        """Stop the sensor thread"""
        self.running = False
        logger.info("Speed sensor thread stopped")


class ThreadSafeController(QThread):
    """Thread-safe controller with Queue-based communication and watchdog"""

    pwm_updated = pyqtSignal(float)
    metrics_updated = pyqtSignal(dict)

    def __init__(self, controller, config, motor_pwm=None):
        super().__init__()
        self.controller = controller
        self.config = config
        self.motor_pwm = motor_pwm  # Store PWM instance instead of global
        self.running = True

        # Thread-safe communication
        self.command_queue = Queue()
        self.state_lock = Lock()

        # State
        self.target_speed = 0.0
        self.current_speed = 0.0
        self.motor_enabled = False

        # Performance tracking
        self.metrics = PerformanceMetrics()

        # Watchdog timer for safety
        self.last_update_time = time.time()
        self.watchdog_timeout = WATCHDOG_TIMEOUT_SEC

        logger.info(f"Controller thread initialized: {controller.__class__.__name__}")

    def run(self):
        """Main control loop with watchdog"""
        while self.running:
            try:
                # Get commands from queue (non-blocking)
                try:
                    cmd = self.command_queue.get(timeout=0.01)
                    self._process_command(cmd)
                except Empty:
                    pass

                # Check watchdog timer
                if self.motor_enabled:
                    elapsed = time.time() - self.last_update_time
                    if elapsed > self.watchdog_timeout:
                        logger.warning(f"Watchdog timeout! No update in {elapsed:.2f}s. Stopping motor.")
                        self.motor_enabled = False
                        if self.motor_pwm and is_raspberry_pi():
                            self.motor_pwm.ChangeDutyCycle(0)

                # Compute control output
                if self.motor_enabled:
                    with self.state_lock:
                        target = self.target_speed
                        current = self.current_speed

                    # Compute PWM
                    pwm = self.controller.compute_output(target, current)

                    # Apply to motor
                    if self.motor_pwm and is_raspberry_pi():
                        self.motor_pwm.ChangeDutyCycle(pwm)

                    # Update metrics
                    self.metrics.update(target, current)

                    # Emit signals
                    self.pwm_updated.emit(pwm)

                    # Reset watchdog
                    self.last_update_time = time.time()

                time.sleep(CONTROL_LOOP_INTERVAL_SEC)

            except (ValueError, TypeError, RuntimeError) as e:
                logger.error(f"Controller error: {e}")
                time.sleep(0.1)

    def _process_command(self, cmd: Dict[str, Any]):
        """Process command from queue"""
        cmd_type = cmd.get('type')

        if cmd_type == 'set_target':
            with self.state_lock:
                self.target_speed = cmd['value']
            logger.debug(f"Target speed set to {cmd['value']}")

        elif cmd_type == 'set_current':
            with self.state_lock:
                self.current_speed = cmd['value']

        elif cmd_type == 'enable_motor':
            self.motor_enabled = True
            self.metrics.reset()
            logger.info("Motor enabled")

        elif cmd_type == 'disable_motor':
            self.motor_enabled = False
            if self.motor_pwm and is_raspberry_pi():
                self.motor_pwm.ChangeDutyCycle(0)
            logger.info("Motor disabled")

        elif cmd_type == 'reset':
            self.controller.reset()
            self.metrics.reset()
            logger.info("Controller reset")

        elif cmd_type == 'get_metrics':
            metrics = self.metrics.calculate(self.target_speed)
            self.metrics_updated.emit(metrics)

    def set_target_speed(self, speed: float):
        """Thread-safe method to set target speed"""
        self.command_queue.put({'type': 'set_target', 'value': speed})

    def update_current_speed(self, speed: float):
        """Thread-safe method to update current speed"""
        self.command_queue.put({'type': 'set_current', 'value': speed})

    def enable_motor(self):
        """Thread-safe method to enable motor"""
        self.command_queue.put({'type': 'enable_motor'})

    def disable_motor(self):
        """Thread-safe method to disable motor"""
        self.command_queue.put({'type': 'disable_motor'})

    def reset_controller(self):
        """Thread-safe method to reset controller"""
        self.command_queue.put({'type': 'reset'})

    def request_metrics(self):
        """Request performance metrics calculation"""
        self.command_queue.put({'type': 'get_metrics'})

    def stop(self):
        """Stop the controller thread"""
        self.running = False
        self.disable_motor()
        logger.info("Controller thread stopped")


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

        self.start_time = time.time()

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
        """Update plot with new data using optimized blitting"""
        current_time = time.time() - self.start_time

        self.time_data.append(current_time)
        self.target_data.append(target)
        self.actual_data.append(actual)
        self.error_data.append(target - actual)

        if len(self.time_data) > 1:
            # Use blitting for better performance (only update lines, not entire figure)
            if self.line_target is None or self.line_actual is None:
                # Initial setup
                self.ax.clear()
                self.setup_plot()

                self.line_target, = self.ax.plot(self.time_data, self.target_data, 'b--',
                                                  linewidth=2, label='Target', alpha=0.8, animated=True)
                self.line_actual, = self.ax.plot(self.time_data, self.actual_data, 'g-',
                                                  linewidth=2, label='Actual', animated=True)

                self.ax.legend(loc='upper right', fontsize=9)
                self.draw()
                self.background = self.copy_from_bbox(self.ax.bbox)
            else:
                # Fast update using blitting
                self.restore_region(self.background)

                # Update line data
                self.line_target.set_data(list(self.time_data), list(self.target_data))
                self.line_actual.set_data(list(self.time_data), list(self.actual_data))

                # Redraw only the lines
                self.ax.draw_artist(self.line_target)
                self.ax.draw_artist(self.line_actual)

                self.blit(self.ax.bbox)
        else:
            # Not enough data yet
            self.draw()

    def clear_data(self):
        """Clear all data"""
        self.time_data.clear()
        self.target_data.clear()
        self.actual_data.clear()
        self.error_data.clear()
        self.start_time = time.time()

        # Reset blitting cache
        self.line_target = None
        self.line_actual = None
        self.background = None

        self.ax.clear()
        self.setup_plot()
        self.draw()


class ModernMotorControlGUI(QMainWindow):
    """Modern DC Motor Control GUI with all improvements"""

    def __init__(self):
        super().__init__()

        self.config = get_config()
        self.config.setup_logging()

        logger.info("=" * 60)
        logger.info("DC Motor Control System v2.0 - Starting")
        logger.info("=" * 60)

        # Motor PWM instance (not global)
        self.motor_pwm = None

        # Initialize hardware (if on Raspberry Pi)
        self.init_hardware()

        # Initialize controllers
        self.controllers = {
            'PI': PIController(),
            'PID': PIDController(),
            'Fuzzy': FuzzyController(),
            'ANFIS': ANFISController()
        }
        self.current_controller_name = 'ANFIS'
        self.current_controller = self.controllers['ANFIS']

        # Threads
        self.speed_sensor = None
        self.controller_thread = None

        # UI Setup
        self.setWindowTitle("DC Motor Control System v2.0 - Professional Edition")
        self.setMinimumSize(1400, 900)

        self.setup_ui()
        self.apply_theme('modern_light')

        # Start threads
        self.start_threads()

        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(100)  # 10Hz

        logger.info("GUI initialized successfully")

    def init_hardware(self):
        """Initialize hardware (GPIO, PWM)"""
        if not is_raspberry_pi():
            logger.warning("Not running on Raspberry Pi - using simulation mode")
            return

        logger.info("Initializing GPIO hardware...")

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

        # Setup pins
        GPIO.setup(self.config.gpio.motor_in1, GPIO.OUT)
        GPIO.setup(self.config.gpio.motor_in2, GPIO.OUT)
        GPIO.setup(self.config.gpio.motor_ena, GPIO.OUT)
        GPIO.setup(self.config.gpio.ir_sensor_pin, GPIO.IN)

        # Create PWM (instance variable, not global)
        self.motor_pwm = GPIO.PWM(self.config.gpio.motor_ena, self.config.motor.pwm_frequency)
        self.motor_pwm.start(0)

        # Set direction (forward)
        GPIO.output(self.config.gpio.motor_in1, GPIO.HIGH)
        GPIO.output(self.config.gpio.motor_in2, GPIO.LOW)

        logger.info("GPIO initialized successfully")

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
        title = QLabel("⚙️ DC Motor Control System v2.0")
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
        self.controller_label = QLabel("Controller: ANFIS")
        self.controller_label.setObjectName("subheading")
        layout.addWidget(self.controller_label)

        # ANFIS status (if applicable)
        self.anfis_status_label = QLabel("")
        self.anfis_status_label.setObjectName("caption")
        layout.addWidget(self.anfis_status_label)

        layout.addStretch()

        return card

    def create_gauge_card(self):
        """Create speed gauge card"""
        card = AnimatedCard("Current Speed")
        layout = QVBoxLayout()
        card.layout().addLayout(layout)

        self.speed_gauge = CircularGauge()
        self.speed_gauge.setRange(0, 100)
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

        tabs.addTab(self.create_control_tab(), "🎮 Control")
        tabs.addTab(self.create_plot_tab(), "📊 Real-Time Plot")
        tabs.addTab(self.create_tuning_tab(), "⚙️ Tuning")
        tabs.addTab(self.create_performance_tab(), "📈 Performance")
        tabs.addTab(self.create_settings_tab(), "⚙️ Settings")
        tabs.addTab(self.create_logs_tab(), "📝 Logs")

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

        self.start_button = PulseButton("▶ Start Motor")
        self.start_button.setObjectName("success")
        self.start_button.clicked.connect(self.start_motor)
        buttons_layout.addWidget(self.start_button)

        self.stop_button = PulseButton("⏹ Stop Motor")
        self.stop_button.setObjectName("error")
        self.stop_button.clicked.connect(self.stop_motor)
        buttons_layout.addWidget(self.stop_button)

        self.reset_button = PulseButton("↻ Reset")
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
            ("PI Controller", "Simple, fast response"),
            ("PID Controller", "Handles disturbances"),
            ("Fuzzy Controller", "Non-linear, robust"),
            ("ANFIS Controller ⭐", "Adaptive neural-fuzzy (BEST)")
        ]

        for i, (name, desc) in enumerate(controllers):
            radio = QRadioButton(name)
            if i == 3:  # ANFIS selected by default
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
        self.score_label = QLabel("Overall Score: -")

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
        """Start sensor and controller threads"""
        # Start speed sensor
        self.speed_sensor = ThreadSafeSpeedSensor(self.config)
        self.speed_sensor.speed_updated.connect(self.on_speed_updated)
        self.speed_sensor.start()

        # Start controller with motor_pwm instance
        self.controller_thread = ThreadSafeController(
            self.current_controller,
            self.config,
            motor_pwm=self.motor_pwm
        )
        self.controller_thread.pwm_updated.connect(self.on_pwm_updated)
        self.controller_thread.metrics_updated.connect(self.on_metrics_updated)
        self.controller_thread.start()

        logger.info("Threads started")

    def apply_theme(self, theme_name: str):
        """Apply theme to application"""
        theme_map = {
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
        controller_names = ['PI', 'PID', 'Fuzzy', 'ANFIS']
        self.current_controller_name = controller_names[index]
        self.current_controller = self.controllers[self.current_controller_name]

        # Update controller thread
        if self.controller_thread:
            self.controller_thread.controller = self.current_controller

        # Update UI
        self.controller_label.setText(f"Controller: {self.current_controller_name}")

        # Update ANFIS status
        if self.current_controller_name == 'ANFIS':
            status = self.current_controller.get_scaling_factors()
            mode = "Neural Networks Active" if status['using_neural_networks'] else "Fuzzy-Only Mode"
            self.anfis_status_label.setText(f"└─ {mode}")
        else:
            self.anfis_status_label.setText("")

        logger.info(f"Controller changed to {self.current_controller_name}")

    def on_speed_updated(self, speed: float):
        """Handle speed sensor update"""
        if self.controller_thread:
            self.controller_thread.update_current_speed(speed)

    def on_pwm_updated(self, pwm: float):
        """Handle PWM update from controller"""
        pass  # Handled in update_display

    def on_metrics_updated(self, metrics: Dict[str, float]):
        """Handle metrics update"""
        self.overshoot_label.setText(f"Overshoot: {metrics['overshoot']:.2f}%")
        self.settling_label.setText(f"Settling Time: {metrics['settling_time']:.2f}s")
        self.ss_error_label.setText(f"Steady-State Error: {metrics['ss_error']:.2f}%")
        self.score_label.setText(f"Overall Score: {metrics['score']:.1f}/100")

    def update_display(self):
        """Update display with current values (thread-safe)"""
        if not self.controller_thread:
            return

        # Get current values
        target = self.target_slider.value()

        # Thread-safe: copy all values inside lock to avoid TOCTOU
        with self.controller_thread.state_lock:
            current = self.controller_thread.current_speed
            motor_enabled = self.controller_thread.motor_enabled

        # Update target if changed
        self.controller_thread.set_target_speed(target)

        # Update gauge
        self.speed_gauge.setValue(current, animated=True)

        # Update labels
        self.target_label.setText(f"Target: {target:.1f}%")
        self.actual_label.setText(f"Actual: {current:.1f}%")

        error = target - current
        self.error_label.setText(f"Error: {error:+.1f}%")

        # Update PWM (mock for now)
        pwm = 50 + error * 0.5
        pwm = max(0, min(100, pwm))
        self.pwm_label.setText(f"PWM: {pwm:.1f}%")
        self.pwm_bar.setValueAnimated(int(pwm))

        # Update plot
        self.plot_widget.update_data(target, current)

        # Update status indicators
        self.sensor_status.setStatus("ok" if motor_enabled else "inactive")
        self.controller_status.setStatus("ok" if motor_enabled else "inactive")

    def start_motor(self):
        """Start motor"""
        if self.controller_thread:
            self.controller_thread.enable_motor()

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
            self.controller_thread.controller = self.current_controller

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

        # Stop threads
        if self.speed_sensor:
            self.speed_sensor.stop()
            self.speed_sensor.wait()

        if self.controller_thread:
            self.controller_thread.stop()
            self.controller_thread.wait()

        # Cleanup GPIO
        if self.motor_pwm and is_raspberry_pi():
            self.motor_pwm.stop()
            GPIO.cleanup()

        logger.info("Shutdown complete")

        event.accept()


def main():
    """Main entry point"""
    app = QApplication(sys.argv)

    # Set application font
    app.setFont(ModernTheme.get_font())

    # Create and show window
    window = ModernMotorControlGUI()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
