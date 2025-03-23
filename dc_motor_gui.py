import sys
import time
import threading
import numpy as np
import os
import RPi.GPIO as GPIO
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QSlider, QLabel, QPushButton, QGroupBox,
                             QTabWidget, QLineEdit, QGridLayout, QTextEdit, QMessageBox,
                             QProgressBar, QShortcut, QCheckBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QTextCursor
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from neural_fuzzy_controller import NeuralFuzzyController
from conventional_controllers import PIController, PIDController
from data_collection import DataCollector
from nn_models import NeuralNetworkTrainer

# Suppress GPIO warnings
GPIO.setwarnings(False)

# GPIO Pin definitions
MOTOR_PIN1 = 17  # Connect to IN1 of L298N
MOTOR_PIN2 = 18  # Connect to IN2 of L298N
MOTOR_PWM_PIN = 12  # Connect to ENA of L298N

# IR sensor pin definitions and dual sensor settings
IR_SENSOR_PIN = 23  # Connect to output pin of first IR sensor
IR_SENSOR_PIN2 = 24  # Connect to output pin of second IR sensor (if available)
USE_DUAL_SENSORS = False  # Set to True if using two sensors

# Setup GPIO pins
GPIO.setmode(GPIO.BCM)
GPIO.setup(MOTOR_PIN1, GPIO.OUT)
GPIO.setup(MOTOR_PIN2, GPIO.OUT)
GPIO.setup(MOTOR_PWM_PIN, GPIO.OUT)
GPIO.setup(IR_SENSOR_PIN, GPIO.IN)
if USE_DUAL_SENSORS:
    GPIO.setup(IR_SENSOR_PIN2, GPIO.IN)

# Create PWM object
motor_pwm = GPIO.PWM(MOTOR_PWM_PIN, 100)  # 100 Hz frequency
motor_pwm.start(0)  # Start with 0% duty cycle

# Motor direction (forward only)
GPIO.output(MOTOR_PIN1, GPIO.HIGH)
GPIO.output(MOTOR_PIN2, GPIO.LOW)

# Make sure motor is stopped at startup
motor_pwm.ChangeDutyCycle(0)

# Speed measurement worker thread
class SpeedSensorThread(QThread):
    speed_updated = pyqtSignal(float)  # RPM signal
    
    def __init__(self):
        super().__init__()
        self.running = True
        self.pulses_per_revolution = 1  # Adjust based on your setup
        # For smoothing: a simple moving average filter
        self.rpm_history = [0] * 5  # Store last 5 readings for smoothing
        self.rpm_index = 0  # Index for circular buffer
    
    def run(self):
        while self.running:
            raw_rpm = self.measure_speed()
            self.rpm_history[self.rpm_index] = raw_rpm
            self.rpm_index = (self.rpm_index + 1) % len(self.rpm_history)
            smoothed_rpm = sum(self.rpm_history) / len(self.rpm_history)
            self.speed_updated.emit(smoothed_rpm)
            time.sleep(0.1)
    
    def measure_speed(self, duration=0.5):
        """Measure speed by counting pulses for the specified duration."""
        pulse_count = 0
        pulse_count2 = 0  # For second sensor (if enabled)
        last_state = GPIO.input(IR_SENSOR_PIN)
        last_state2 = GPIO.input(IR_SENSOR_PIN2) if USE_DUAL_SENSORS else 0
        valid_transitions = 0
        min_pulse_width = 0.001  # 1ms minimum pulse width (to filter noise)
        last_transition_time = time.time()
        start_time = time.time()
        end_time = start_time + duration
        
        while time.time() < end_time:
            current_time = time.time()
            # First sensor processing
            current_state = GPIO.input(IR_SENSOR_PIN)
            if current_state == 0 and last_state == 1:
                transition_delta = current_time - last_transition_time
                if transition_delta > min_pulse_width:
                    pulse_count += 1
                    valid_transitions += 1
                last_transition_time = current_time
            last_state = current_state
            # Second sensor processing if enabled
            if USE_DUAL_SENSORS:
                current_state2 = GPIO.input(IR_SENSOR_PIN2)
                if current_state2 == 0 and last_state2 == 1:
                    transition_delta = current_time - last_transition_time
                    if transition_delta > min_pulse_width:
                        pulse_count2 += 1
                    last_state2 = current_state2
            time.sleep(0.0001)
            if not self.running:
                break
        
        if self.running:
            duration_actual = time.time() - start_time
            if duration_actual > 0 and valid_transitions > 0:
                if USE_DUAL_SENSORS:
                    avg_pulses = (pulse_count + pulse_count2) / 2
                    rpm = (avg_pulses / self.pulses_per_revolution) / duration_actual * 60
                else:
                    rpm = (pulse_count / self.pulses_per_revolution) / duration_actual * 60
                max_reasonable_rpm = 3000  # Set based on motor specifications
                if rpm > max_reasonable_rpm:
                    rpm = 0
                return rpm
            return 0
        return 0
    
    def stop(self):
        self.running = False
        self.wait()

# Controller worker thread
class ControllerThread(QThread):
    controller_updated = pyqtSignal(float, float, float, float, float)  # PWM, e_scale, de_scale, o_scale, error
    
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.running = True
        self.target_speed = 0  # Normalized 0-100
        self.current_speed = 0  # Normalized 0-100
        self.max_rpm = 100  # Adjust based on your motor
        self.motor_enabled = False  # Controls motor state
    
    def run(self):
        while self.running:
            error = self.target_speed - self.current_speed
            pwm = self.controller.compute_output(self.target_speed, self.current_speed)
            if self.motor_enabled:
                motor_pwm.ChangeDutyCycle(pwm)
            if hasattr(self.controller, 'error_scale'):
                e_scale = self.controller.error_scale
                de_scale = self.controller.delta_error_scale
                o_scale = self.controller.output_scale
            else:
                e_scale = de_scale = o_scale = 1.0
            self.controller_updated.emit(pwm, e_scale, de_scale, o_scale, error)
            time.sleep(0.1)
    
    def update_speeds(self, target, current_rpm):
        self.target_speed = target
        self.current_speed = min(100, max(0, (current_rpm / self.max_rpm) * 100))
    
    def stop(self):
        self.running = False
        motor_pwm.ChangeDutyCycle(0)
        self.wait()

# Enhanced SpeedPlotCanvas for research-quality plots
class SpeedPlotCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        self.axes.set_title('Step Response', fontsize=12, fontweight='bold')
        self.axes.set_xlabel('Time (s)', fontsize=10)
        self.axes.set_ylabel('Amplitude', fontsize=10)
        self.axes.grid(True, linestyle='--', alpha=0.7)
        
        # Data storage for different controllers
        self.controller_data = {
            "ANFIS": {"time": np.array([]), "speed": np.array([]), "target": np.array([]), "color": 'red'},
            "PI": {"time": np.array([]), "speed": np.array([]), "target": np.array([]), "color": 'blue'},
            "PID": {"time": np.array([]), "speed": np.array([]), "target": np.array([]), "color": 'green'}
        }
        
        # Tracking current controller
        self.current_controller = "ANFIS"
        
        # For smoothing
        self.smooth_window = 7  # Increased for smoother curves
        
        # Start times for each controller session
        self.start_times = {"ANFIS": time.time(), "PI": time.time(), "PID": time.time()}
        
        # Plot configuration
        self.show_grid = True
        self.normalize_amplitude = True  # Normalize amplitude to 0-1 range
        self.max_time_window = 30  # Maximum time window to display (seconds)
        
        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)
        
        self.fig.tight_layout()
    
    def set_current_controller(self, controller_type):
        """Set the current controller and reset its data"""
        self.current_controller = controller_type
        self.start_times[controller_type] = time.time()
        self.controller_data[controller_type]["time"] = np.array([])
        self.controller_data[controller_type]["speed"] = np.array([])
        self.controller_data[controller_type]["target"] = np.array([])
    
    def update_plot(self, current_rpm, target_rpm):
        """Update plot with new data point"""
        controller = self.current_controller
        data = self.controller_data[controller]
        current_time = time.time() - self.start_times[controller]
        data["time"] = np.append(data["time"], current_time)
        data["speed"] = np.append(data["speed"], current_rpm)
        data["target"] = np.append(data["target"], target_rpm)
        if len(data["time"]) > 0 and data["time"][-1] > self.max_time_window:
            cutoff_idx = np.where(data["time"] > data["time"][-1] - self.max_time_window)[0][0]
            data["time"] = data["time"][cutoff_idx:]
            data["speed"] = data["speed"][cutoff_idx:]
            data["target"] = data["target"][cutoff_idx:]
        self._draw_plot()
    
    def _smooth_data(self, data):
        """Apply smoothing to data"""
        if len(data) >= self.smooth_window:
            window = np.ones(self.smooth_window) / self.smooth_window
            smooth_data = np.convolve(data, window, mode='valid')
            padding = len(data) - len(smooth_data)
            return np.concatenate((data[:padding], smooth_data))
        return data
    
    def _normalize_data(self, speed_data, target_data):
        """Normalize data to 0-1 range if needed"""
        if not self.normalize_amplitude or len(speed_data) == 0:
            return speed_data, target_data
        max_val = max(np.max(target_data) if len(target_data) > 0 else 0, 
                      np.max(speed_data) if len(speed_data) > 0 else 0)
        if max_val > 0:
            return speed_data / max_val, target_data / max_val
        return speed_data, target_data
    
    def _draw_plot(self):
        """Redraw the plot with all active controller data"""
        self.axes.clear()
        self.axes.set_title('Step Response', fontsize=12, fontweight='bold')
        self.axes.set_xlabel('Time (s)', fontsize=10)
        if self.normalize_amplitude:
            self.axes.set_ylabel('Normalized Amplitude', fontsize=10)
            self.axes.set_ylim(0, 1.2)
        else:
            self.axes.set_ylabel('Speed (RPM)', fontsize=10)
        if self.show_grid:
            self.axes.grid(True, linestyle='--', alpha=0.7)
        legend_handles = []
        for controller, data in self.controller_data.items():
            if len(data["time"]) > 0:
                time_data = data["time"]
                speed_data = self._smooth_data(data["speed"])
                target_data = data["target"]
                if self.normalize_amplitude:
                    speed_data, target_data = self._normalize_data(speed_data, target_data)
                speed_line, = self.axes.plot(
                    time_data, speed_data, '-', 
                    linewidth=2, 
                    color=data["color"], 
                    label=f'{controller} Response'
                )
                if controller == self.current_controller:
                    target_line, = self.axes.plot(
                        time_data, target_data, '--', 
                        linewidth=1.5, 
                        color='black', 
                        label='Target'
                    )
                    legend_handles.append(target_line)
                legend_handles.append(speed_line)
        if legend_handles:
            self.axes.legend(handles=legend_handles, fontsize=9)
        for label in (self.axes.get_xticklabels() + self.axes.get_yticklabels()):
            label.set_fontsize(8)
        self.fig.tight_layout()
        self.fig.canvas.draw()
    
    def toggle_controller_visibility(self, controller, visible):
        """Toggle the visibility of a controller's data"""
        if controller in self.controller_data:
            self.controller_data[controller]["visible"] = visible
            self._draw_plot()
    
    def toggle_normalization(self, normalize):
        """Toggle amplitude normalization"""
        self.normalize_amplitude = normalize
        self._draw_plot()
    
    def toggle_grid(self, show_grid):
        """Toggle grid visibility"""
        self.show_grid = show_grid
        self._draw_plot()
    
    def reset_plot(self):
        """Reset all plot data"""
        for controller in self.controller_data:
            self.controller_data[controller]["time"] = np.array([])
            self.controller_data[controller]["speed"] = np.array([])
            self.controller_data[controller]["target"] = np.array([])
            self.start_times[controller] = time.time()
        self.axes.clear()
        self.axes.set_title('Step Response', fontsize=12, fontweight='bold')
        self.axes.set_xlabel('Time (s)', fontsize=10)
        if self.normalize_amplitude:
            self.axes.set_ylabel('Normalized Amplitude', fontsize=10)
        else:
            self.axes.set_ylabel('Speed (RPM)', fontsize=10)
        if self.show_grid:
            self.axes.grid(True, linestyle='--', alpha=0.7)
        self.fig.canvas.draw()
    
    def save_plot(self, filename="motor_response_plot.png"):
        """Save the current plot to a file"""
        self.fig.savefig(filename, dpi=300, bbox_inches='tight')
        return filename

# Main Window
class MainWindow(QMainWindow):
    training_update_signal = pyqtSignal(str, int, int, dict, str, str)
    training_status_updated = pyqtSignal(str)
    model_info_updated = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.training_update_signal.connect(self.on_training_update)
        
        # Initialize controllers
        self.neuro_fuzzy_controller = NeuralFuzzyController()
        self.pi_controller = PIController(kp=0.8, ki=0.3)
        self.pid_controller = PIDController(kp=0.8, ki=0.3, kd=0.1)
        
        self.active_controller = self.neuro_fuzzy_controller
        self.controller_type = "ANFIS"
        
        motor_pwm.ChangeDutyCycle(0)
        self.target_rpm = 0
        
        self.init_ui()
        self.update_model_info()
        self.init_threads()
        
        self.plot_timer = QTimer()
        self.plot_timer.timeout.connect(self.update_plot)
        self.plot_timer.start(500)
        
        self.max_rpm = 100
        self.current_rpm = 0
        
        self.logging_active = False
        self.log_data = []
    
    def init_ui(self):
        self.setWindowTitle('Neuro-Fuzzy DC Motor Control System')
        self.setGeometry(100, 100, 800, 600)
        
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)
        
        # === Training Tab ===
        training_tab = QWidget()
        training_layout = QVBoxLayout()
        training_tab.setLayout(training_layout)

        training_description = QLabel(
            "This tab lets you collect training data, train neural networks, and select models for the ANFIS controller."
        )
        training_description.setWordWrap(True)
        training_layout.addWidget(training_description)

        data_collection_group = QGroupBox("Step 1: Data Collection")
        data_collection_layout = QVBoxLayout()
        data_collection_group.setLayout(data_collection_layout)
        collection_desc = QLabel(
            "Collect training data by running the motor at different speeds. "
            "This data will be used to train the neural networks."
        )
        collection_desc.setWordWrap(True)
        data_collection_layout.addWidget(collection_desc)
        collection_buttons_layout = QHBoxLayout()
        self.start_collection_button = QPushButton("Start Data Collection")
        self.stop_collection_button = QPushButton("Stop Collection")
        self.start_collection_button.clicked.connect(self.start_data_collection)
        self.stop_collection_button.clicked.connect(self.stop_data_collection)
        self.stop_collection_button.setEnabled(False)
        collection_buttons_layout.addWidget(self.start_collection_button)
        collection_buttons_layout.addWidget(self.stop_collection_button)
        data_collection_layout.addLayout(collection_buttons_layout)
        self.collection_status_label = QLabel("Collection Status: Idle")
        data_collection_layout.addWidget(self.collection_status_label)
        training_layout.addWidget(data_collection_group)

        nn_training_group = QGroupBox("Step 2: Neural Network Training")
        nn_training_layout = QVBoxLayout()
        nn_training_group.setLayout(nn_training_layout)
        training_desc = QLabel(
            "Train the neural networks using the collected data. "
            "This will create three models to adapt the error, delta-error, and output scaling factors."
        )
        training_desc.setWordWrap(True)
        nn_training_layout.addWidget(training_desc)
        training_params_layout = QGridLayout()
        training_params_layout.addWidget(QLabel("Training Epochs:"), 0, 0)
        self.epochs_input = QLineEdit("50")
        self.epochs_input.setToolTip("Number of training iterations (higher values may improve results but take longer)")
        training_params_layout.addWidget(self.epochs_input, 0, 1)
        training_params_layout.addWidget(QLabel("Batch Size:"), 1, 0)
        self.batch_size_input = QLineEdit("32")
        self.batch_size_input.setToolTip("Number of samples processed before model update (32 is typically a good choice)")
        training_params_layout.addWidget(self.batch_size_input, 1, 1)
        nn_training_layout.addLayout(training_params_layout)
        self.train_nn_button = QPushButton("Train Neural Networks")
        self.train_nn_button.clicked.connect(self.train_neural_networks)
        nn_training_layout.addWidget(self.train_nn_button)
        self.training_status_label = QLabel("Training Status: Not Started")
        nn_training_layout.addWidget(self.training_status_label)
        self.training_progress = QProgressBar()
        self.training_progress.setRange(0, 100)
        self.training_progress.setValue(0)
        self.training_progress.setVisible(False)
        nn_training_layout.addWidget(self.training_progress)
        training_layout.addWidget(nn_training_group)

        model_group = QGroupBox("Step 3: Model Selection and Information")
        model_layout = QVBoxLayout()
        model_group.setLayout(model_layout)
        model_desc = QLabel(
            "Select and load trained models for the ANFIS controller. "
            "You can view information about the available models."
        )
        model_desc.setWordWrap(True)
        model_layout.addWidget(model_desc)
        models_grid = QGridLayout()
        models_grid.addWidget(QLabel("Error Scaling Model:"), 0, 0)
        self.error_model_status = QLabel("Not Found")
        models_grid.addWidget(self.error_model_status, 0, 1)
        self.error_model_checkbox = QCheckBox("Use")
        self.error_model_checkbox.setEnabled(False)
        models_grid.addWidget(self.error_model_checkbox, 0, 2)
        models_grid.addWidget(QLabel("Delta-Error Scaling Model:"), 1, 0)
        self.delta_model_status = QLabel("Not Found")
        models_grid.addWidget(self.delta_model_status, 1, 1)
        self.delta_model_checkbox = QCheckBox("Use")
        self.delta_model_checkbox.setEnabled(False)
        models_grid.addWidget(self.delta_model_checkbox, 1, 2)
        models_grid.addWidget(QLabel("Output Scaling Model:"), 2, 0)
        self.output_model_status = QLabel("Not Found")
        models_grid.addWidget(self.output_model_status, 2, 1)
        self.output_model_checkbox = QCheckBox("Use")
        self.output_model_checkbox.setEnabled(False)
        models_grid.addWidget(self.output_model_checkbox, 2, 2)
        model_layout.addLayout(models_grid)
        check_models_button = QPushButton("Check for Available Models")
        check_models_button.clicked.connect(self.check_available_models)
        model_layout.addWidget(check_models_button)
        self.load_models_button = QPushButton("Load Selected Models")
        self.load_models_button.clicked.connect(self.load_selected_models)
        self.load_models_button.setEnabled(False)
        model_layout.addWidget(self.load_models_button)
        self.model_info_text = QTextEdit()
        self.model_info_text.setReadOnly(True)
        self.model_info_text.setMinimumHeight(150)
        self.model_info_text.setText("No trained models found. Complete Steps 1 and 2 to create models.")
        model_layout.addWidget(self.model_info_text)
        training_layout.addWidget(model_group)
        tab_widget.addTab(training_tab, "Training")
        
        # === Control Tab ===
        control_tab = QWidget()
        control_layout = QVBoxLayout()
        control_tab.setLayout(control_layout)
        
        speed_group = QGroupBox("Speed Control")
        speed_layout = QVBoxLayout()
        speed_group.setLayout(speed_layout)
        slider_layout = QHBoxLayout()
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(0)
        self.speed_slider.setMaximum(100)
        self.speed_slider.setValue(0)
        self.speed_slider.setTickPosition(QSlider.TicksBelow)
        self.speed_slider.setTickInterval(10)
        self.speed_slider.valueChanged.connect(self.speed_slider_changed)
        slider_layout.addWidget(QLabel("Target Speed:"))
        slider_layout.addWidget(self.speed_slider)
        self.speed_value_label = QLabel("0 %")
        slider_layout.addWidget(self.speed_value_label)
        speed_layout.addLayout(slider_layout)
        direction_layout = QHBoxLayout()
        self.direction_label = QLabel("Motor Direction: Forward")
        self.direction_label.setStyleSheet("font-weight: bold; color: green;")
        direction_layout.addWidget(self.direction_label)
        speed_layout.addLayout(direction_layout)
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("START")
        self.start_button.setStyleSheet("background-color: green; color: white; font-weight: bold;")
        self.start_button.clicked.connect(self.start_motor)
        button_layout.addWidget(self.start_button)
        self.stop_button = QPushButton("STOP")
        self.stop_button.setStyleSheet("background-color: red; color: white; font-weight: bold;")
        self.stop_button.clicked.connect(self.stop_motor)
        button_layout.addWidget(self.stop_button)
        speed_layout.addLayout(button_layout)
        control_layout.addWidget(speed_group)
        
        controller_select_group = QGroupBox("Controller Selection")
        controller_select_layout = QHBoxLayout()
        controller_select_group.setLayout(controller_select_layout)
        self.anfis_button = QPushButton("ANFIS")
        self.pi_button = QPushButton("PI")
        self.pid_button = QPushButton("PID")
        self.anfis_button.setCheckable(True)
        self.pi_button.setCheckable(True)
        self.pid_button.setCheckable(True)
        self.anfis_button.setChecked(True)
        self.anfis_button.clicked.connect(lambda: self.change_controller("ANFIS"))
        self.pi_button.clicked.connect(lambda: self.change_controller("PI"))
        self.pid_button.clicked.connect(lambda: self.change_controller("PID"))
        controller_select_layout.addWidget(self.anfis_button)
        controller_select_layout.addWidget(self.pi_button)
        controller_select_layout.addWidget(self.pid_button)
        control_layout.addWidget(controller_select_group)
        
        tuning_group = QGroupBox("Controller Parameter Tuning")
        tuning_layout = QGridLayout()
        tuning_group.setLayout(tuning_layout)
        tuning_layout.addWidget(QLabel("PI Controller Parameters:"), 0, 0, 1, 2)
        tuning_layout.addWidget(QLabel("Kp:"), 1, 0)
        self.pi_kp_input = QLineEdit(str(self.pi_controller.kp))
        tuning_layout.addWidget(self.pi_kp_input, 1, 1)
        tuning_layout.addWidget(QLabel("Ki:"), 2, 0)
        self.pi_ki_input = QLineEdit(str(self.pi_controller.ki))
        tuning_layout.addWidget(self.pi_ki_input, 2, 1)
        tuning_layout.addWidget(QLabel("PID Controller Parameters:"), 3, 0, 1, 2)
        tuning_layout.addWidget(QLabel("Kp:"), 4, 0)
        self.pid_kp_input = QLineEdit(str(self.pid_controller.kp))
        tuning_layout.addWidget(self.pid_kp_input, 4, 1)
        tuning_layout.addWidget(QLabel("Ki:"), 5, 0)
        self.pid_ki_input = QLineEdit(str(self.pid_controller.ki))
        tuning_layout.addWidget(self.pid_ki_input, 5, 1)
        tuning_layout.addWidget(QLabel("Kd:"), 6, 0)
        self.pid_kd_input = QLineEdit(str(self.pid_controller.kd))
        tuning_layout.addWidget(self.pid_kd_input, 6, 1)
        self.apply_params_button = QPushButton("Apply Parameters")
        self.apply_params_button.clicked.connect(self.apply_controller_parameters)
        tuning_layout.addWidget(self.apply_params_button, 7, 0, 1, 2)
        control_layout.addWidget(tuning_group)
        
        display_group = QGroupBox("Speed Measurement")
        display_layout = QVBoxLayout()
        display_group.setLayout(display_layout)
        self.speed_display = QLabel("0 RPM")
        self.speed_display.setFont(QFont("Arial", 24))
        self.speed_display.setAlignment(Qt.AlignCenter)
        display_layout.addWidget(self.speed_display)
        control_layout.addWidget(display_group)
        
        controller_group = QGroupBox("Controller Information")
        controller_layout = QGridLayout()
        controller_group.setLayout(controller_layout)
        controller_layout.addWidget(QLabel("PWM Output:"), 0, 0)
        self.pwm_label = QLabel("0 %")
        controller_layout.addWidget(self.pwm_label, 0, 1)
        controller_layout.addWidget(QLabel("Error:"), 1, 0)
        self.error_label = QLabel("0")
        controller_layout.addWidget(self.error_label, 1, 1)
        controller_layout.addWidget(QLabel("Error Scale:"), 2, 0)
        self.error_scale_label = QLabel("1.0")
        controller_layout.addWidget(self.error_scale_label, 2, 1)
        controller_layout.addWidget(QLabel("Delta Error Scale:"), 3, 0)
        self.delta_error_scale_label = QLabel("1.0")
        controller_layout.addWidget(self.delta_error_scale_label, 3, 1)
        controller_layout.addWidget(QLabel("Output Scale:"), 4, 0)
        self.output_scale_label = QLabel("1.0")
        controller_layout.addWidget(self.output_scale_label, 4, 1)
        control_layout.addWidget(controller_group)
        
        tab_widget.addTab(control_tab, "Control")
        
        # === Monitoring Tab ===
        monitoring_tab = QWidget()
        monitoring_layout = QVBoxLayout()
        monitoring_tab.setLayout(monitoring_layout)
        self.speed_plot = SpeedPlotCanvas(monitoring_tab, width=5, height=4, dpi=100)
        monitoring_layout.addWidget(self.speed_plot)
        
        plot_controls_group = QGroupBox("Plot Controls")
        plot_controls_layout = QGridLayout()
        plot_controls_group.setLayout(plot_controls_layout)
        plot_controls_layout.addWidget(QLabel("Show Controllers:"), 0, 0)
        self.show_anfis_cb = QCheckBox("ANFIS")
        self.show_anfis_cb.setChecked(True)
        self.show_anfis_cb.stateChanged.connect(
            lambda state: self.speed_plot.toggle_controller_visibility("ANFIS", state == Qt.Checked)
        )
        plot_controls_layout.addWidget(self.show_anfis_cb, 0, 1)
        self.show_pi_cb = QCheckBox("PI")
        self.show_pi_cb.setChecked(True)
        self.show_pi_cb.stateChanged.connect(
            lambda state: self.speed_plot.toggle_controller_visibility("PI", state == Qt.Checked)
        )
        plot_controls_layout.addWidget(self.show_pi_cb, 0, 2)
        self.show_pid_cb = QCheckBox("PID")
        self.show_pid_cb.setChecked(True)
        self.show_pid_cb.stateChanged.connect(
            lambda state: self.speed_plot.toggle_controller_visibility("PID", state == Qt.Checked)
        )
        plot_controls_layout.addWidget(self.show_pid_cb, 0, 3)
        plot_controls_layout.addWidget(QLabel("Plot Options:"), 1, 0)
        self.normalize_cb = QCheckBox("Normalize Amplitude")
        self.normalize_cb.setChecked(True)
        self.normalize_cb.stateChanged.connect(
            lambda state: self.speed_plot.toggle_normalization(state == Qt.Checked)
        )
        plot_controls_layout.addWidget(self.normalize_cb, 1, 1)
        self.grid_cb = QCheckBox("Show Grid")
        self.grid_cb.setChecked(True)
        self.grid_cb.stateChanged.connect(
            lambda state: self.speed_plot.toggle_grid(state == Qt.Checked)
        )
        plot_controls_layout.addWidget(self.grid_cb, 1, 2)
        monitoring_layout.addWidget(plot_controls_group)
        
        plot_buttons_layout = QHBoxLayout()
        self.reset_plot_button = QPushButton("Reset Plot")
        self.reset_plot_button.clicked.connect(self.reset_plot)
        plot_buttons_layout.addWidget(self.reset_plot_button)
        self.save_plot_button = QPushButton("Save Plot")
        self.save_plot_button.clicked.connect(self.save_plot)
        plot_buttons_layout.addWidget(self.save_plot_button)
        monitoring_layout.addLayout(plot_buttons_layout)
        
        step_test_group = QGroupBox("Step Response Test")
        step_test_layout = QVBoxLayout()
        step_test_group.setLayout(step_test_layout)
        step_test_desc = QLabel(
            "Run a step response test to measure controller performance. "
            "This will step the motor from 0 to the specified target speed."
        )
        step_test_desc.setWordWrap(True)
        step_test_layout.addWidget(step_test_desc)
        test_params_layout = QHBoxLayout()
        test_params_layout.addWidget(QLabel("Target Speed (%):"))
        self.step_test_target = QLineEdit("70")
        test_params_layout.addWidget(self.step_test_target)
        step_test_layout.addLayout(test_params_layout)
        self.start_test_button = QPushButton("Start Step Test")
        self.start_test_button.clicked.connect(self.run_step_test)
        step_test_layout.addWidget(self.start_test_button)
        monitoring_layout.addWidget(step_test_group)
        
        tab_widget.addTab(monitoring_tab, "Monitoring")
        
        # === Data Logging Tab ===
        data_tab = QWidget()
        data_layout = QVBoxLayout()
        data_tab.setLayout(data_layout)
        
        info_label = QLabel(
            "Data logging allows you to record motor performance and controller behavior for later analysis. "
            "Use this feature to compare different controllers or to document experiments."
        )
        info_label.setWordWrap(True)
        data_layout.addWidget(info_label)
        
        log_control_group = QGroupBox("Data Logging Controls")
        log_control_layout = QVBoxLayout()
        log_control_group.setLayout(log_control_layout)
        
        config_layout = QGridLayout()
        config_layout.addWidget(QLabel("Logging Interval (ms):"), 0, 0)
        self.log_interval_input = QLineEdit("200")
        config_layout.addWidget(self.log_interval_input, 0, 1)
        config_layout.addWidget(QLabel("Log Filename Prefix:"), 1, 0)
        self.log_filename_input = QLineEdit("motor_log")
        config_layout.addWidget(self.log_filename_input, 1, 1)
        self.log_speed_checkbox = QCheckBox("Log Speed")
        self.log_speed_checkbox.setChecked(True)
        config_layout.addWidget(self.log_speed_checkbox, 2, 0)
        self.log_pwm_checkbox = QCheckBox("Log PWM")
        self.log_pwm_checkbox.setChecked(True)
        config_layout.addWidget(self.log_pwm_checkbox, 2, 1)
        self.log_error_checkbox = QCheckBox("Log Error")
        self.log_error_checkbox.setChecked(True)
        config_layout.addWidget(self.log_error_checkbox, 3, 0)
        self.log_scaling_checkbox = QCheckBox("Log Scaling Factors")
        self.log_scaling_checkbox.setChecked(True)
        config_layout.addWidget(self.log_scaling_checkbox, 3, 1)
        log_control_layout.addLayout(config_layout)
        
        log_buttons_layout = QHBoxLayout()
        self.start_log_button = QPushButton("Start Logging")
        self.stop_log_button = QPushButton("Stop Logging")
        self.export_log_button = QPushButton("Export Data")
        self.start_log_button.clicked.connect(self.start_logging)
        self.stop_log_button.clicked.connect(self.stop_logging)
        self.export_log_button.clicked.connect(self.export_log_data)
        self.stop_log_button.setEnabled(False)
        self.export_log_button.setEnabled(False)
        log_buttons_layout.addWidget(self.start_log_button)
        log_buttons_layout.addWidget(self.stop_log_button)
        log_buttons_layout.addWidget(self.export_log_button)
        log_control_layout.addLayout(log_buttons_layout)
        
        self.log_status_label = QLabel("Logging: Inactive")
        log_control_layout.addWidget(self.log_status_label)
        
        data_layout.addWidget(log_control_group)
        
        log_display_group = QGroupBox("Logged Data Preview")
        log_display_layout = QVBoxLayout()
        log_display_group.setLayout(log_display_layout)
        preview_label = QLabel("Showing the 5 most recent data points:")
        log_display_layout.addWidget(preview_label)
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont("Courier", 9))
        self.log_display.setText("No data logged yet")
        log_display_layout.addWidget(self.log_display)
        self.clear_log_button = QPushButton("Clear Log")
        self.clear_log_button.clicked.connect(self.clear_log_data)
        log_display_layout.addWidget(self.clear_log_button)
        data_layout.addWidget(log_display_group)
        
        analysis_group = QGroupBox("Log Analysis Options")
        analysis_layout = QVBoxLayout()
        analysis_group.setLayout(analysis_layout)
        analysis_buttons_layout = QHBoxLayout()
        self.view_stats_button = QPushButton("View Statistics")
        self.view_stats_button.clicked.connect(self.show_log_statistics)
        self.view_stats_button.setEnabled(False)
        analysis_buttons_layout.addWidget(self.view_stats_button)
        self.plot_log_button = QPushButton("Plot Logged Data")
        self.plot_log_button.clicked.connect(self.plot_log_data)
        self.plot_log_button.setEnabled(False)
        analysis_buttons_layout.addWidget(self.plot_log_button)
        analysis_layout.addLayout(analysis_buttons_layout)
        self.analysis_info_label = QLabel("Log data analysis will be available after logging is completed.")
        analysis_layout.addWidget(self.analysis_info_label)
        data_layout.addWidget(analysis_group)
        
        tab_widget.addTab(data_tab, "Data Logging")
        
        # === Educational Content Tab ===
        edu_tab = QWidget()
        edu_layout = QVBoxLayout()
        edu_tab.setLayout(edu_layout)
        edu_content = QTextEdit()
        edu_content.setReadOnly(True)
        edu_content.setHtml("""
        <h2>DC Motor Speed Control Educational Guide</h2>
        <p>This training kit demonstrates different approaches to speed control of a separately excited DC motor.</p>
        <h3>Control Methods</h3>
        <ul>
            <li><b>PI Control</b>: Proportional-Integral control is a widely used feedback control method where the control signal is a sum of terms proportional to the error and the integral of the error.</li>
            <li><b>PID Control</b>: Proportional-Integral-Derivative control adds a term proportional to the derivative of the error, improving transient response.</li>
            <li><b>ANFIS Control</b>: Adaptive Neuro-Fuzzy Inference System combines fuzzy logic with neural networks for adaptive control.</li>
        </ul>
        <h3>Advantages of Neuro-Fuzzy Control</h3>
        <ul>
            <li>Combines the human-like reasoning of fuzzy systems with the learning capability of neural networks</li>
            <li>Adapts to changing operating conditions through automatic tuning of scaling factors</li>
            <li>Better handling of nonlinearities in the motor system</li>
            <li>More robust against disturbances and parameter variations</li>
            <li>Improved dynamic response (faster settling time, less overshoot)</li>
        </ul>
        <h3>Experiment Suggestions</h3>
        <ol>
            <li>Compare step response of different controllers</li>
            <li>Observe disturbance rejection by applying physical load while running</li>
            <li>Tune PI and PID parameters to see their effects on performance</li>
            <li>Track how ANFIS scaling factors adapt to changes</li>
            <li>Export data for different controllers and compare key metrics</li>
        </ol>
        """)
        edu_layout.addWidget(edu_content)
        
        tab_widget.addTab(edu_tab, "Educational Guide")
    
    def init_threads(self):
        self.speed_thread = SpeedSensorThread()
        self.speed_thread.speed_updated.connect(self.update_speed)
        self.speed_thread.start()
        self.controller_thread = ControllerThread(self.active_controller)
        self.controller_thread.motor_enabled = False
        self.controller_thread.controller_updated.connect(self.update_controller_info)
        self.controller_thread.start()
    
    def speed_slider_changed(self):
        value = self.speed_slider.value()
        self.speed_value_label.setText(f"{value} %")
        self.target_rpm = (value / 100.0) * self.max_rpm
        self.controller_thread.update_speeds(value, self.current_rpm)
        motor_pwm.ChangeDutyCycle(value)
    
    def start_motor(self):
        value = self.speed_slider.value()
        self.target_rpm = (value / 100.0) * self.max_rpm
        self.controller_thread.update_speeds(value, self.current_rpm)
        self.controller_thread.motor_enabled = True
        motor_pwm.ChangeDutyCycle(value)
    
    def stop_motor(self):
        self.speed_slider.setValue(0)
        motor_pwm.ChangeDutyCycle(0)
        self.target_rpm = 0
        self.controller_thread.motor_enabled = False
        self.controller_thread.update_speeds(0, self.current_rpm)
    
    def update_speed(self, rpm):
        self.current_rpm = rpm
        self.speed_display.setText(f"{rpm:.2f} RPM")
        self.controller_thread.update_speeds(self.speed_slider.value(), rpm)
    
    def update_controller_info(self, pwm, error_scale=1.0, delta_error_scale=1.0, output_scale=1.0, error=0):
        self.pwm_label.setText(f"{pwm:.2f} %")
        self.error_label.setText(f"{error:.2f}")
        if self.controller_type == "ANFIS":
            self.error_scale_label.setText(f"{error_scale:.4f}")
            self.delta_error_scale_label.setText(f"{delta_error_scale:.4f}")
            self.output_scale_label.setText(f"{output_scale:.4f}")
        else:
            if self.controller_type == "PI":
                self.error_scale_label.setText(f"Kp: {self.pi_controller.kp}")
                self.delta_error_scale_label.setText(f"Ki: {self.pi_controller.ki}")
                self.output_scale_label.setText("N/A")
            else:
                self.error_scale_label.setText(f"Kp: {self.pid_controller.kp}")
                self.delta_error_scale_label.setText(f"Ki: {self.pid_controller.ki}")
                self.output_scale_label.setText(f"Kd: {self.pid_controller.kd}")
    
    def update_plot(self):
        self.speed_plot.update_plot(self.current_rpm, self.target_rpm)
    
    def reset_plot(self):
        self.speed_plot.reset_plot()
    
    def change_controller(self, controller_type):
        self.anfis_button.setChecked(controller_type == "ANFIS")
        self.pi_button.setChecked(controller_type == "PI")
        self.pid_button.setChecked(controller_type == "PID")
        self.pi_controller.reset()
        self.pid_controller.reset()
        if controller_type == "ANFIS":
            self.active_controller = self.neuro_fuzzy_controller
        elif controller_type == "PI":
            self.active_controller = self.pi_controller
        elif controller_type == "PID":
            self.active_controller = self.pid_controller
        self.controller_thread.controller = self.active_controller
        self.controller_type = controller_type
        self.speed_plot.set_current_controller(controller_type)
    
    def apply_controller_parameters(self):
        try:
            self.pi_controller.kp = float(self.pi_kp_input.text())
            self.pi_controller.ki = float(self.pi_ki_input.text())
            self.pid_controller.kp = float(self.pid_kp_input.text())
            self.pid_controller.ki = float(self.pid_ki_input.text())
            self.pid_controller.kd = float(self.pid_kd_input.text())
            if self.controller_type in ["PI", "PID"]:
                self.error_scale_label.setText(f"Kp: {self.pi_controller.kp}")
                self.delta_error_scale_label.setText(f"Ki: {self.pi_controller.ki}")
                if self.controller_type == "PID":
                    self.output_scale_label.setText(f"Kd: {self.pid_controller.kd}")
        except ValueError:
            self.show_message("Error", "Please enter valid numeric values for controller parameters.")
    
    def on_training_update(self, network, current, total, metrics, status, error_msg=None):
        self.training_progress_callback(network, current, total, metrics, status, error_msg)
    
    def training_progress_callback(self, network, current, total, metrics, status, error_msg=None):
        if total > 0:
            progress = int((current + 1) / total * 100)
        else:
            progress = 0
        if network == "all":
            if hasattr(self, 'training_status_label'):
                if status == "started":
                    self.training_status_label.setText("Training Status: Starting training process...")
                elif status == "completed":
                    self.training_status_label.setText("Training Status: All networks trained successfully")
                    if hasattr(self, 'cancel_training_button'):
                        self.cancel_training_button.setEnabled(False)
                    self.train_nn_button.setEnabled(True)
                    self.update_model_info()
                elif status == "error":
                    self.training_status_label.setText(f"Training Error: {error_msg}")
                    if hasattr(self, 'cancel_training_button'):
                        self.cancel_training_button.setEnabled(False)
                    self.train_nn_button.setEnabled(True)
        elif hasattr(self, 'training_progress_bars') and network in self.training_progress_bars:
            progress_bar = self.training_progress_bars[network]
            status_label = self.training_status_labels[network]
            if status == "started":
                status_label.setText(f"{network.replace('_', ' ').title()} Network: Starting...")
                progress_bar.setValue(0)
            elif status == "running":
                status_label.setText(f"{network.replace('_', ' ').title()} Network: Epoch {current+1}/{total}")
                progress_bar.setValue(progress)
                if metrics and 'loss' in metrics:
                    loss = metrics['loss']
                    val_loss = metrics.get('val_loss', 0)
                    status_label.setText(
                        f"{network.replace('_', ' ').title()} Network: Epoch {current+1}/{total}, Loss: {loss:.4f}, Val Loss: {val_loss:.4f}"
                    )
            elif status == "completed":
                status_label.setText(f"{network.replace('_', ' ').title()} Network: Completed")
                progress_bar.setValue(100)
    
    def train_neural_networks(self):
        if not os.path.exists("training_data.json"):
            self.show_message("Error", "No training data found. Please collect data first.")
            return
        try:
            try:
                epochs = int(self.epochs_input.text())
                batch_size = int(self.batch_size_input.text())
            except (AttributeError, ValueError) as e:
                self.show_message("Warning", f"Using default training parameters: 50 epochs, 32 batch size. Error: {str(e)}")
                epochs = 50
                batch_size = 32
            self.training_status_label.setText("Training Status: Initializing...")
            self.train_nn_button.setEnabled(False)
            if hasattr(self, 'cancel_training_button'):
                self.cancel_training_button.setEnabled(True)
            if hasattr(self, 'training_progress_bars'):
                for network in self.training_progress_bars:
                    self.training_progress_bars[network].setValue(0)
                    self.training_status_labels[network].setText(f"{network.replace('_', ' ').title()} Network: Not started")
            self.training_cancelled = False
            self.training_thread = threading.Thread(target=self.run_training, args=(epochs, batch_size))
            self.training_thread.daemon = True
            self.training_thread.start()
        except Exception as e:
            self.show_message("Error", f"Failed to start training: {str(e)}")
            self.train_nn_button.setEnabled(True)
            if hasattr(self, 'cancel_training_button'):
                self.cancel_training_button.setEnabled(False)
    
    def run_training(self, epochs, batch_size):
        try:
            trainer = NeuralNetworkTrainer()
            def signal_callback(network, current, total, metrics, status, error_msg=None):
                self.training_update_signal.emit(network, current, total, metrics or {}, status, error_msg or "")
            success = trainer.train_networks(
                epochs=epochs, 
                batch_size=batch_size,
                callback=signal_callback
            )
        except Exception as e:
            self.training_update_signal.emit("all", 0, 0, {}, "error", str(e))
    
    def cancel_training(self):
        self.training_cancelled = True
        self.cancel_training_button.setEnabled(False)
        self.training_status_label.setText("Training Status: Canceling...")
        self.train_nn_button.setEnabled(True)
    
    def show_message(self, title, message):
        msg_box = QMessageBox()
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec_()
    
    # Data Collection Methods (Restored)
    def start_data_collection(self):
        self.data_collector = DataCollector(
            MOTOR_PIN1, MOTOR_PIN2, MOTOR_PWM_PIN, IR_SENSOR_PIN, 
            existing_pwm=motor_pwm)
        self.start_collection_button.setEnabled(False)
        self.stop_collection_button.setEnabled(True)
        self.collection_status_label.setText("Collection Status: Collecting Data...")
        self.collection_thread = threading.Thread(target=self.run_data_collection)
        self.collection_thread.daemon = True
        self.collection_thread.start()

    def run_data_collection(self):
        try:
            self.data_collector.collect_training_data_auto()
            self.data_collector.save_training_data()
            self.collection_status_label.setText(f"Collection Status: Complete ({len(self.data_collector.training_data)} points)")
        except Exception as e:
            self.collection_status_label.setText(f"Collection Error: {str(e)}")
        finally:
            self.start_collection_button.setEnabled(True)
            self.stop_collection_button.setEnabled(False)

    def stop_data_collection(self):
        if hasattr(self, 'data_collector'):
            self.data_collector.cleanup()
            self.collection_status_label.setText("Collection Status: Stopped")
            self.start_collection_button.setEnabled(True)
            self.stop_collection_button.setEnabled(False)
    
    # Data Logging Methods with Enhanced Features
    def start_logging(self):
        """Start logging data"""
        try:
            interval_ms = int(self.log_interval_input.text())
            if interval_ms < 50:
                raise ValueError("Logging interval must be at least 50ms")
            self.log_data = []
            self.logging_active = True
            self.log_start_time = time.time()
            self.start_log_button.setEnabled(False)
            self.stop_log_button.setEnabled(True)
            self.export_log_button.setEnabled(False)
            self.view_stats_button.setEnabled(False)
            self.plot_log_button.setEnabled(False)
            self.log_status_label.setText("Logging: Active")
            self.log_timer = QTimer()
            self.log_timer.timeout.connect(self.log_data_point)
            self.log_timer.start(interval_ms)
            self.update_log_display_headers()
        except ValueError as e:
            self.show_message("Invalid Input", str(e))
    
    def update_log_display_headers(self):
        """Update the log display with appropriate headers"""
        headers = ["Time(s)", "Target", "Actual"]
        if self.log_pwm_checkbox.isChecked():
            headers.append("PWM(%)")
        if self.log_error_checkbox.isChecked():
            headers.append("Error")
        if self.log_scaling_checkbox.isChecked() and self.controller_type == "ANFIS":
            headers.extend(["E_Scale", "DE_Scale", "O_Scale"])
        headers.append("Controller")
        header_row = " | ".join([f"{h:10}" for h in headers])
        separator = "-" * len(header_row)
        preview = f"{header_row}\n{separator}\n"
        self.log_display.setText(preview)
    
    def log_data_point(self):
        """Log a single data point"""
        if self.logging_active:
            log_time = time.time() - self.log_start_time
            data_point = {
                'time': log_time,
                'target_speed': self.target_rpm,
                'actual_speed': self.current_rpm,
                'controller': self.controller_type
            }
            if self.log_pwm_checkbox.isChecked():
                data_point['pwm'] = float(self.pwm_label.text().replace(' %', ''))
            if self.log_error_checkbox.isChecked():
                data_point['error'] = float(self.error_label.text())
            if self.log_scaling_checkbox.isChecked() and self.controller_type == "ANFIS":
                data_point['error_scale'] = float(self.error_scale_label.text())
                data_point['delta_error_scale'] = float(self.delta_error_scale_label.text())
                data_point['output_scale'] = float(self.output_scale_label.text())
            self.log_data.append(data_point)
            self.update_log_display()
    
    def update_log_display(self):
        """Update the log display with the most recent data points"""
        if not self.log_data:
            return
        current_text = self.log_display.toPlainText()
        lines = current_text.split('\n')
        if len(lines) >= 2:
            header = lines[0]
            separator = lines[1]
            data_rows = []
            for point in self.log_data[-5:]:
                row_items = [
                    f"{point['time']:.2f}",
                    f"{point['target_speed']:.2f}",
                    f"{point['actual_speed']:.2f}"
                ]
                if self.log_pwm_checkbox.isChecked():
                    row_items.append(f"{point.get('pwm', 0):.2f}")
                if self.log_error_checkbox.isChecked():
                    row_items.append(f"{point.get('error', 0):.2f}")
                if self.log_scaling_checkbox.isChecked() and self.controller_type == "ANFIS":
                    row_items.append(f"{point.get('error_scale', 1.0):.2f}")
                    row_items.append(f"{point.get('delta_error_scale', 1.0):.2f}")
                    row_items.append(f"{point.get('output_scale', 1.0):.2f}")
                row_items.append(f"{point['controller']}")
                data_rows.append(" | ".join([f"{item:10}" for item in row_items]))
            updated_text = f"{header}\n{separator}\n" + "\n".join(data_rows)
            self.log_display.setText(updated_text)
            cursor = self.log_display.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.log_display.setTextCursor(cursor)
    
    def stop_logging(self):
        """Stop logging data"""
        self.logging_active = False
        self.log_timer.stop()
        self.start_log_button.setEnabled(True)
        self.stop_log_button.setEnabled(False)
        self.export_log_button.setEnabled(True)
        self.view_stats_button.setEnabled(True)
        self.plot_log_button.setEnabled(True)
        log_points = len(self.log_data)
        duration = time.time() - self.log_start_time
        self.log_status_label.setText(
            f"Logging: Stopped ({log_points} points collected over {duration:.1f} seconds)")
        self.analysis_info_label.setText(
            f"Log data analysis ready: {log_points} data points collected.")
    
    def clear_log_data(self):
        """Clear logged data"""
        if self.logging_active:
            self.show_message("Error", "Cannot clear log while logging is active")
            return
        self.log_data = []
        self.log_display.setText("No data logged yet")
        self.export_log_button.setEnabled(False)
        self.view_stats_button.setEnabled(False)
        self.plot_log_button.setEnabled(False)
        self.log_status_label.setText("Logging: Inactive")
        self.analysis_info_label.setText("Log data analysis will be available after logging is completed.")
    
    def export_log_data(self):
        """Export logged data to a CSV file"""
        if not self.log_data or len(self.log_data) == 0:
            self.show_message("Error", "No data to export")
            return
        try:
            filename_prefix = self.log_filename_input.text()
            if not filename_prefix:
                filename_prefix = "motor_log"
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"{filename_prefix}_{timestamp}.csv"
            with open(filename, 'w') as f:
                headers = ["Time(s)", "TargetSpeed(RPM)", "ActualSpeed(RPM)", "Controller"]
                if self.log_pwm_checkbox.isChecked():
                    headers.insert(3, "PWM(%)")
                if self.log_error_checkbox.isChecked():
                    headers.insert(-1, "Error")
                if self.log_scaling_checkbox.isChecked():
                    headers.insert(-1, "ErrorScale")
                    headers.insert(-1, "DeltaErrorScale")
                    headers.insert(-1, "OutputScale")
                f.write(",".join(headers) + "\n")
                for point in self.log_data:
                    row = [
                        f"{point['time']:.3f}",
                        f"{point['target_speed']:.2f}",
                        f"{point['actual_speed']:.2f}"
                    ]
                    if self.log_pwm_checkbox.isChecked():
                        row.append(f"{point.get('pwm', 0):.2f}")
                    if self.log_error_checkbox.isChecked():
                        row.append(f"{point.get('error', 0):.2f}")
                    if self.log_scaling_checkbox.isChecked():
                        row.append(f"{point.get('error_scale', 1.0):.4f}")
                        row.append(f"{point.get('delta_error_scale', 1.0):.4f}")
                        row.append(f"{point.get('output_scale', 1.0):.4f}")
                    row.append(f"{point['controller']}")
                    f.write(",".join(row) + "\n")
            self.show_message("Success", f"Data exported to {filename}")
        except Exception as e:
            self.show_message("Error", f"Failed to export data: {str(e)}")
    
    def show_log_statistics(self):
        """Show statistics from logged data"""
        if not self.log_data or len(self.log_data) == 0:
            self.show_message("Error", "No data to analyze")
            return
        try:
            actual_speeds = [point['actual_speed'] for point in self.log_data]
            target_speeds = [point['target_speed'] for point in self.log_data]
            errors = [abs(t - a) for t, a in zip(target_speeds, actual_speeds)]
            avg_speed = sum(actual_speeds) / len(actual_speeds)
            max_speed = max(actual_speeds)
            min_speed = min(actual_speeds)
            avg_error = sum(errors) / len(errors)
            max_error = max(errors)
            stats = f"""
            <h3>Log Data Statistics</h3>
            <table border="0" cellspacing="5">
                <tr><td><b>Data Points:</b></td><td>{len(self.log_data)}</td></tr>
                <tr><td><b>Duration:</b></td><td>{self.log_data[-1]['time'] - self.log_data[0]['time']:.2f} seconds</td></tr>
                <tr><td><b>Average Speed:</b></td><td>{avg_speed:.2f} RPM</td></tr>
                <tr><td><b>Maximum Speed:</b></td><td>{max_speed:.2f} RPM</td></tr>
                <tr><td><b>Minimum Speed:</b></td><td>{min_speed:.2f} RPM</td></tr>
                <tr><td><b>Average Error:</b></td><td>{avg_error:.2f}</td></tr>
                <tr><td><b>Maximum Error:</b></td><td>{max_error:.2f}</td></tr>
            </table>
            
            <p>Controller: {self.log_data[0]['controller']}</p>
            """
            msg_box = QMessageBox()
            msg_box.setWindowTitle("Log Statistics")
            msg_box.setTextFormat(Qt.RichText)
            msg_box.setText(stats)
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec_()
        except Exception as e:
            self.show_message("Error", f"Failed to analyze data: {str(e)}")
    
    def plot_log_data(self):
        """Plot the logged data"""
        if not self.log_data or len(self.log_data) == 0:
            self.show_message("Error", "No data to plot")
            return
        try:
            times = [point['time'] for point in self.log_data]
            target_speeds = [point['target_speed'] for point in self.log_data]
            actual_speeds = [point['actual_speed'] for point in self.log_data]
            plt.figure(figsize=(10, 6))
            plt.plot(times, actual_speeds, 'b-', linewidth=2, label='Actual Speed')
            plt.plot(times, target_speeds, 'r--', linewidth=2, label='Target Speed')
            if self.log_pwm_checkbox.isChecked() and 'pwm' in self.log_data[0]:
                pwm_values = [point.get('pwm', 0) for point in self.log_data]
                plt.plot(times, pwm_values, 'g-.', linewidth=1.5, label='PWM (%)')
            if self.log_error_checkbox.isChecked() and 'error' in self.log_data[0]:
                error_values = [point.get('error', 0) for point in self.log_data]
                plt.plot(times, error_values, 'm:', linewidth=1.5, label='Error')
            plt.title(f'Motor Performance with {self.log_data[0]["controller"]} Controller')
            plt.xlabel('Time (s)')
            plt.ylabel('Speed (RPM) / Control Value')
            plt.grid(True, linestyle='--', alpha=0.7)
            plt.legend()
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"{self.log_filename_input.text()}_plot_{timestamp}.png"
            plt.savefig(filename)
            plt.tight_layout()
            plt.show()
            self.show_message("Plot Saved", f"Plot saved as {filename}")
        except Exception as e:
            self.show_message("Error", f"Failed to plot data: {str(e)}")
    
    def reload_neural_networks(self):
        new_controller = NeuralFuzzyController()
        if self.controller_type == "ANFIS":
            self.active_controller = new_controller
            self.neuro_fuzzy_controller = new_controller
            self.controller_thread.controller = new_controller
        else:
            self.neuro_fuzzy_controller = new_controller
        self.update_model_info()
        self.show_message("Models Reloaded", "Neural network models have been reloaded. If trained models were found, they will be used.")
    
    def check_available_models(self):
        self.model_info_text.clear()
        model_info = ""
        models_found = 0
        if os.path.exists("models/error_scale.h5"):
            self.error_model_status.setText("Found")
            self.error_model_status.setStyleSheet("color: green")
            self.error_model_checkbox.setEnabled(True)
            self.error_model_checkbox.setChecked(True)
            model_info += "• Error Scale Model: Found\n"
            models_found += 1
        else:
            self.error_model_status.setText("Not Found")
            self.error_model_status.setStyleSheet("color: red")
            self.error_model_checkbox.setEnabled(False)
            self.error_model_checkbox.setChecked(False)
            model_info += "• Error Scale Model: Not Found\n"
        if os.path.exists("models/delta_error_scale.h5"):
            self.delta_model_status.setText("Found")
            self.delta_model_status.setStyleSheet("color: green")
            self.delta_model_checkbox.setEnabled(True)
            self.delta_model_checkbox.setChecked(True)
            model_info += "• Delta Error Scale Model: Found\n"
            models_found += 1
        else:
            self.delta_model_status.setText("Not Found")
            self.delta_model_status.setStyleSheet("color: red")
            self.delta_model_checkbox.setEnabled(False)
            self.delta_model_checkbox.setChecked(False)
            model_info += "• Delta Error Scale Model: Not Found\n"
        if os.path.exists("models/output_scale.h5"):
            self.output_model_status.setText("Found")
            self.output_model_status.setStyleSheet("color: green")
            self.output_model_checkbox.setEnabled(True)
            self.output_model_checkbox.setChecked(True)
            model_info += "• Output Scale Model: Found\n"
            models_found += 1
        else:
            self.output_model_status.setText("Not Found")
            self.output_model_status.setStyleSheet("color: red")
            self.output_model_checkbox.setEnabled(False)
            self.output_model_checkbox.setChecked(False)
            model_info += "• Output Scale Model: Not Found\n"
        self.load_models_button.setEnabled(models_found > 0)
        if models_found == 0:
            model_info += "\nNo trained models found. Please complete Steps 1 and 2 to create models."
        else:
            model_info += f"\n{models_found} of 3 models found. "
            if models_found < 3:
                model_info += "You can still load the available models, but the performance may be limited."
            else:
                model_info += "All models are available for use."
            if os.path.exists("error_scale_history.png"):
                model_info += "\n\nTraining history plots are available for visualization in the project directory."
        self.model_info_text.setText(model_info)
    
    def load_selected_models(self):
        models_to_use = {
            "error_scale": self.error_model_checkbox.isChecked(),
            "delta_error": self.delta_model_checkbox.isChecked(),
            "output_scale": self.output_model_checkbox.isChecked()
        }
        new_controller = NeuralFuzzyController(models_to_use=models_to_use)
        if self.controller_type == "ANFIS":
            self.active_controller = new_controller
            self.neuro_fuzzy_controller = new_controller
            self.controller_thread.controller = new_controller
        else:
            self.neuro_fuzzy_controller = new_controller
        models_used = sum(1 for use in models_to_use.values() if use)
        self.show_message(
            "Models Loaded", 
            f"{models_used} neural network models have been loaded and are now being used by the ANFIS controller."
        )
    
    def update_model_info(self):
        try:
            self.check_available_models()
        except Exception as e:
            self.model_info_text.setText(f"Error retrieving model info: {str(e)}")
    
    def save_plot(self):
        try:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"motor_response_{timestamp}.png"
            saved_file = self.speed_plot.save_plot(filename)
            self.show_message("Plot Saved", f"Plot saved as {saved_file}")
        except Exception as e:
            self.show_message("Error", f"Failed to save plot: {str(e)}")
    
    def run_step_test(self):
        try:
            target_speed = int(self.step_test_target.text())
            if target_speed < 0 or target_speed > 100:
                self.show_message("Error", "Target speed must be between 0 and 100%")
                return
            self.stop_motor()
            time.sleep(0.5)
            self.speed_plot.set_current_controller(self.controller_type)
            self.speed_slider.setValue(target_speed)
            self.controller_thread.motor_enabled = True
            motor_pwm.ChangeDutyCycle(target_speed)
            self.show_message("Test Started", f"Step response test started with target speed {target_speed}%")
        except ValueError:
            self.show_message("Error", "Please enter a valid number for target speed")
    
    def closeEvent(self, event):
        self.speed_thread.stop()
        self.controller_thread.stop()
        motor_pwm.stop()
        GPIO.cleanup()
        event.accept()

if __name__ == "__main__":
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
