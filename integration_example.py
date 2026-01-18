"""
Integration Example: Adding Advanced Features to Modern Motor GUI

This file demonstrates how to integrate the new advanced plotting
and educational features into the existing modern_motor_gui.py
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QLabel, QApplication
)
from PyQt5.QtCore import QTimer
import sys
import time

# Import existing components
from modern_theme import ModernTheme
from conventional_controllers import PIDController, PIController
from fuzzy_controller import FuzzyController
from anfis_controller import ANFISController

# Import new advanced features
from advanced_plotting import AdvancedPlottingTabWidget
from educational_features import EducationalPanel, ExplanationDialog

from logger_utils import get_logger

logger = get_logger(__name__)


class EnhancedMotorGUI(QMainWindow):
    """
    Enhanced Motor Control GUI with Advanced Plotting and Educational Features

    This example shows how to integrate the new features into your existing GUI
    """

    def __init__(self):
        super().__init__()

        self.setWindowTitle("DC Motor Control System v2.2 - Advanced Features")
        self.setMinimumSize(1200, 800)

        # Controllers
        self.controllers = {
            'PI': PIController(kp=0.6, ki=0.15),
            'PID': PIDController(kp=0.6, ki=0.15, kd=0.05),
            'Fuzzy': FuzzyController(),
            'ANFIS': ANFISController()
        }
        self.current_controller = self.controllers['PID']
        self.current_controller_name = 'PID'

        # Simulation state
        self.target_speed = 50.0
        self.current_speed = 0.0
        self.start_time = time.time()
        self.running = False

        self.init_ui()
        self.init_simulation()

    def init_ui(self):
        """Initialize user interface"""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Main tab widget
        self.main_tabs = QTabWidget()

        # 1. Basic Control Tab (existing)
        control_tab = self.create_control_tab()
        self.main_tabs.addTab(control_tab, "🎮 Control")

        # 2. Advanced Plotting Tab (NEW!)
        self.advanced_plots = AdvancedPlottingTabWidget()
        self.main_tabs.addTab(self.advanced_plots, "📊 Advanced Plots")

        # 3. Educational Panel (NEW!)
        self.edu_panel = EducationalPanel()
        self.main_tabs.addTab(self.edu_panel, "📚 Learn")

        # Add tabs to layout
        layout.addWidget(self.main_tabs)

        # Apply modern theme
        QApplication.instance().setStyleSheet(ModernTheme.get_stylesheet('modern_light'))
        QApplication.instance().setPalette(ModernTheme.get_palette('modern_light'))

        logger.info("Enhanced GUI initialized with advanced features")

    def create_control_tab(self) -> QWidget:
        """Create basic control tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Header
        header = QLabel("Basic Motor Control")
        header.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")

        # Controller selector with help button
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Controller:"))

        for name in ['PI', 'PID', 'Fuzzy', 'ANFIS']:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, n=name: self.select_controller(n))
            selector_layout.addWidget(btn)

        # Help button for current controller
        help_btn = QPushButton("❓ Help")
        help_btn.clicked.connect(self.show_controller_help)
        selector_layout.addWidget(help_btn)
        selector_layout.addStretch()

        # Status display
        self.status_label = QLabel("Status: Idle")
        self.status_label.setStyleSheet("font-size: 14px; padding: 10px;")

        self.metrics_label = QLabel("Target: 0% | Actual: 0% | Error: 0% | PWM: 0%")
        self.metrics_label.setStyleSheet("font-family: monospace; padding: 10px;")

        # Control buttons
        button_layout = QHBoxLayout()

        self.start_btn = QPushButton("▶ Start")
        self.start_btn.clicked.connect(self.start_simulation)

        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.clicked.connect(self.stop_simulation)
        self.stop_btn.setEnabled(False)

        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        button_layout.addStretch()

        # Layout
        layout.addWidget(header)
        layout.addLayout(selector_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.metrics_label)
        layout.addLayout(button_layout)
        layout.addStretch()

        return tab

    def select_controller(self, name: str):
        """Select controller"""
        self.current_controller = self.controllers[name]
        self.current_controller_name = name
        self.current_controller.reset()

        # Update plot widget controller name
        self.advanced_plots.multi_trace.data.controller_name = name

        logger.info(f"Controller changed to {name}")

    def show_controller_help(self):
        """Show help for current controller"""
        topic_map = {
            'PI': 'pi_controller',
            'PID': 'pid_controller',
            'Fuzzy': 'fuzzy_controller',
            'ANFIS': 'anfis_controller'
        }

        topic = topic_map.get(self.current_controller_name, 'pid_controller')
        dialog = ExplanationDialog(topic, self)
        dialog.exec_()

    def init_simulation(self):
        """Initialize simulation timer"""
        # Update timer (100ms = 10Hz)
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_simulation)
        self.update_timer.setInterval(100)  # 100ms

    def start_simulation(self):
        """Start simulation"""
        self.running = True
        self.start_time = time.time()
        self.current_speed = 0.0
        self.current_controller.reset()

        # Clear plot
        self.advanced_plots.multi_trace.clear_plot()

        self.update_timer.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("Status: Running")

        logger.info("Simulation started")

    def stop_simulation(self):
        """Stop simulation"""
        self.running = False
        self.update_timer.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("Status: Stopped")

        logger.info("Simulation stopped")

    def update_simulation(self):
        """Update simulation (called every 100ms)"""
        if not self.running:
            return

        current_time = time.time() - self.start_time

        # Simple motor simulation
        # (In real system, this would come from hardware)
        error = self.target_speed - self.current_speed

        # Compute control output
        pwm = self.current_controller.compute_output(self.target_speed, self.current_speed)

        # Simulate motor response (very simple first-order model)
        # Real motor: current_speed would come from IR sensor
        tau = 0.5  # Time constant
        dt = 0.1   # 100ms
        self.current_speed += (pwm - self.current_speed) / tau * dt

        # Extract PID terms if using PID controller
        if isinstance(self.current_controller, PIDController):
            p_term = self.current_controller.kp * error
            i_term = self.current_controller.ki * self.current_controller.integral
            d_term = self.current_controller.kd * self.current_controller.derivative
        elif isinstance(self.current_controller, PIController):
            p_term = self.current_controller.kp * error
            i_term = self.current_controller.ki * self.current_controller.integral
            d_term = 0.0
        else:
            # Fuzzy/ANFIS don't have explicit P/I/D terms
            p_term = i_term = d_term = 0.0

        # Update metrics display
        self.metrics_label.setText(
            f"Target: {self.target_speed:.1f}% | "
            f"Actual: {self.current_speed:.1f}% | "
            f"Error: {error:+.1f}% | "
            f"PWM: {pwm:.1f}%"
        )

        # Add sample to advanced plots (KEY INTEGRATION POINT!)
        self.advanced_plots.add_sample(
            time=current_time,
            target=self.target_speed,
            actual=self.current_speed,
            error=error,
            pwm=pwm,
            p_term=p_term,
            i_term=i_term,
            d_term=d_term
        )

        # Update plots (automatically updates visible plot)
        self.advanced_plots.update_plots()

        # Vary target speed for interesting demo
        if current_time > 10 and current_time < 10.2:
            self.target_speed = 70.0
        elif current_time > 20 and current_time < 20.2:
            self.target_speed = 40.0
        elif current_time > 30 and current_time < 30.2:
            self.target_speed = 60.0


def main():
    """
    Main entry point

    This demonstrates the complete integration of advanced features
    """
    app = QApplication(sys.argv)

    # Create enhanced GUI
    gui = EnhancedMotorGUI()
    gui.show()

    logger.info("Application started with advanced features")
    logger.info("Features available:")
    logger.info("  - Multi-trace plotting (7 traces)")
    logger.info("  - Export (PNG, CSV, JSON, MATLAB)")
    logger.info("  - FFT analysis")
    logger.info("  - Phase portraits")
    logger.info("  - Controller comparison")
    logger.info("  - Educational panel (8 topics)")
    logger.info("  - Interactive tutorial (7 steps)")

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()


"""
INTEGRATION CHECKLIST:

✅ Step 1: Import new modules
    from advanced_plotting import AdvancedPlottingTabWidget
    from educational_features import EducationalPanel, ExplanationDialog

✅ Step 2: Create widgets in __init__()
    self.advanced_plots = AdvancedPlottingTabWidget()
    self.edu_panel = EducationalPanel()

✅ Step 3: Add to tab widget
    self.main_tabs.addTab(self.advanced_plots, "📊 Advanced Plots")
    self.main_tabs.addTab(self.edu_panel, "📚 Learn")

✅ Step 4: Extract P/I/D terms in update loop
    if isinstance(self.controller, PIDController):
        p_term = self.controller.kp * error
        i_term = self.controller.ki * self.controller.integral
        d_term = self.controller.kd * self.controller.derivative

✅ Step 5: Feed data to advanced plots
    self.advanced_plots.add_sample(
        time, target, actual, error, pwm,
        p_term, i_term, d_term
    )

✅ Step 6: Update plots
    self.advanced_plots.update_plots()

✅ Step 7: Add help buttons (optional)
    help_btn.clicked.connect(self.show_controller_help)

    def show_controller_help(self):
        dialog = ExplanationDialog('pid_controller', self)
        dialog.exec_()

THAT'S IT! Advanced features fully integrated.

Users can now:
- View 7 traces simultaneously
- Export to 4 formats
- Analyze with FFT
- View phase portraits
- Compare controllers
- Learn control theory
- Follow interactive tutorial
"""
