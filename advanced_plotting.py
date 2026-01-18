"""
Advanced Plotting System for DC Motor Control
Provides multiple traces, export functionality, and advanced analysis
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from collections import deque
from pathlib import Path
import json
import csv
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox,
    QGroupBox, QLabel, QComboBox, QFileDialog, QTabWidget, QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSignal

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
from scipy import signal
from scipy.fft import fft, fftfreq

from logger_utils import get_logger

logger = get_logger(__name__)


class MultiTraceData:
    """
    Storage for multiple data traces with efficient circular buffers
    """

    def __init__(self, max_samples: int = 3000):
        self.max_samples = max_samples

        # Time series data
        self.time = deque(maxlen=max_samples)

        # Basic traces
        self.target_speed = deque(maxlen=max_samples)
        self.actual_speed = deque(maxlen=max_samples)
        self.error = deque(maxlen=max_samples)
        self.pwm_output = deque(maxlen=max_samples)

        # PID component traces
        self.p_term = deque(maxlen=max_samples)
        self.i_term = deque(maxlen=max_samples)
        self.d_term = deque(maxlen=max_samples)

        # Metadata
        self.start_time = datetime.now()
        self.controller_name = "Unknown"

    def add_sample(
        self,
        time: float,
        target: float,
        actual: float,
        error: float,
        pwm: float,
        p_term: float = 0.0,
        i_term: float = 0.0,
        d_term: float = 0.0
    ):
        """Add a new sample to all traces"""
        self.time.append(time)
        self.target_speed.append(target)
        self.actual_speed.append(actual)
        self.error.append(error)
        self.pwm_output.append(pwm)
        self.p_term.append(p_term)
        self.i_term.append(i_term)
        self.d_term.append(d_term)

    def get_arrays(self) -> Dict[str, np.ndarray]:
        """Convert deques to numpy arrays for plotting/analysis"""
        return {
            'time': np.array(self.time),
            'target_speed': np.array(self.target_speed),
            'actual_speed': np.array(self.actual_speed),
            'error': np.array(self.error),
            'pwm_output': np.array(self.pwm_output),
            'p_term': np.array(self.p_term),
            'i_term': np.array(self.i_term),
            'd_term': np.array(self.d_term)
        }

    def clear(self):
        """Clear all data"""
        self.time.clear()
        self.target_speed.clear()
        self.actual_speed.clear()
        self.error.clear()
        self.pwm_output.clear()
        self.p_term.clear()
        self.i_term.clear()
        self.d_term.clear()
        self.start_time = datetime.now()


class AdvancedPlotWidget(QWidget):
    """
    Advanced plotting widget with multiple configurable traces
    """

    export_requested = pyqtSignal(str, str)  # format, filename

    def __init__(self, parent=None):
        super().__init__(parent)

        self.data = MultiTraceData()

        # Trace visibility flags
        self.show_target = True
        self.show_actual = True
        self.show_error_area = True
        self.show_pwm = False
        self.show_p_term = False
        self.show_i_term = False
        self.show_d_term = False

        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Create matplotlib figure
        self.figure = Figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        self.ax = self.figure.add_subplot(111)
        self.ax.set_xlabel('Time (s)')
        self.ax.set_ylabel('Speed / PWM (%)')
        self.ax.set_title('Motor Control - Real-Time Multi-Trace Plot')
        self.ax.grid(True, alpha=0.3)
        self.ax.set_ylim(-10, 110)

        # Control panel
        control_panel = self.create_control_panel()

        # Layout
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        layout.addWidget(control_panel)

    def create_control_panel(self) -> QWidget:
        """Create trace selection and export controls"""
        panel = QWidget()
        layout = QHBoxLayout(panel)

        # Trace selection group
        trace_group = QGroupBox("Visible Traces")
        trace_layout = QGridLayout(trace_group)

        # Create checkboxes
        self.target_cb = QCheckBox("Target Speed")
        self.target_cb.setChecked(True)
        self.target_cb.toggled.connect(lambda: self.toggle_trace('target'))

        self.actual_cb = QCheckBox("Actual Speed")
        self.actual_cb.setChecked(True)
        self.actual_cb.toggled.connect(lambda: self.toggle_trace('actual'))

        self.error_area_cb = QCheckBox("Error Area")
        self.error_area_cb.setChecked(True)
        self.error_area_cb.toggled.connect(lambda: self.toggle_trace('error_area'))

        self.pwm_cb = QCheckBox("PWM Output")
        self.pwm_cb.setChecked(False)
        self.pwm_cb.toggled.connect(lambda: self.toggle_trace('pwm'))

        self.p_term_cb = QCheckBox("P Term")
        self.p_term_cb.setChecked(False)
        self.p_term_cb.toggled.connect(lambda: self.toggle_trace('p_term'))

        self.i_term_cb = QCheckBox("I Term")
        self.i_term_cb.setChecked(False)
        self.i_term_cb.toggled.connect(lambda: self.toggle_trace('i_term'))

        self.d_term_cb = QCheckBox("D Term")
        self.d_term_cb.setChecked(False)
        self.d_term_cb.toggled.connect(lambda: self.toggle_trace('d_term'))

        # Add to grid
        trace_layout.addWidget(self.target_cb, 0, 0)
        trace_layout.addWidget(self.actual_cb, 0, 1)
        trace_layout.addWidget(self.error_area_cb, 0, 2)
        trace_layout.addWidget(self.pwm_cb, 1, 0)
        trace_layout.addWidget(self.p_term_cb, 1, 1)
        trace_layout.addWidget(self.i_term_cb, 1, 2)
        trace_layout.addWidget(self.d_term_cb, 1, 3)

        # Export group
        export_group = QGroupBox("Export")
        export_layout = QVBoxLayout(export_group)

        self.save_plot_btn = QPushButton("Save Plot (PNG)")
        self.save_plot_btn.clicked.connect(self.save_plot)

        self.export_csv_btn = QPushButton("Export Data (CSV)")
        self.export_csv_btn.clicked.connect(self.export_csv)

        self.export_json_btn = QPushButton("Export Data (JSON)")
        self.export_json_btn.clicked.connect(self.export_json)

        self.export_matlab_btn = QPushButton("Export Data (MATLAB)")
        self.export_matlab_btn.clicked.connect(self.export_matlab)

        export_layout.addWidget(self.save_plot_btn)
        export_layout.addWidget(self.export_csv_btn)
        export_layout.addWidget(self.export_json_btn)
        export_layout.addWidget(self.export_matlab_btn)

        # Clear button
        clear_btn = QPushButton("Clear Plot")
        clear_btn.clicked.connect(self.clear_plot)

        # Layout
        layout.addWidget(trace_group)
        layout.addWidget(export_group)
        layout.addWidget(clear_btn)
        layout.addStretch()

        return panel

    def toggle_trace(self, trace_name: str):
        """Toggle visibility of a trace"""
        if trace_name == 'target':
            self.show_target = self.target_cb.isChecked()
        elif trace_name == 'actual':
            self.show_actual = self.actual_cb.isChecked()
        elif trace_name == 'error_area':
            self.show_error_area = self.error_area_cb.isChecked()
        elif trace_name == 'pwm':
            self.show_pwm = self.pwm_cb.isChecked()
        elif trace_name == 'p_term':
            self.show_p_term = self.p_term_cb.isChecked()
        elif trace_name == 'i_term':
            self.show_i_term = self.i_term_cb.isChecked()
        elif trace_name == 'd_term':
            self.show_d_term = self.d_term_cb.isChecked()

        self.update_plot()

    def add_sample(
        self,
        time: float,
        target: float,
        actual: float,
        error: float,
        pwm: float,
        p_term: float = 0.0,
        i_term: float = 0.0,
        d_term: float = 0.0
    ):
        """Add new data sample"""
        self.data.add_sample(time, target, actual, error, pwm, p_term, i_term, d_term)

    def update_plot(self):
        """Update the plot with current data"""
        if len(self.data.time) == 0:
            return

        arrays = self.data.get_arrays()
        time = arrays['time']

        self.ax.clear()
        self.ax.grid(True, alpha=0.3)
        self.ax.set_xlabel('Time (s)')
        self.ax.set_ylabel('Speed / PWM (%)')
        self.ax.set_title(f'Motor Control - {self.data.controller_name}')

        # Plot selected traces
        if self.show_target and len(arrays['target_speed']) > 0:
            self.ax.plot(time, arrays['target_speed'], 'b--',
                        linewidth=2, label='Target Speed', alpha=0.8)

        if self.show_actual and len(arrays['actual_speed']) > 0:
            self.ax.plot(time, arrays['actual_speed'], 'g-',
                        linewidth=2, label='Actual Speed')

        if self.show_error_area and len(arrays['error']) > 0:
            error_line = arrays['target_speed']
            actual_line = arrays['actual_speed']
            self.ax.fill_between(time, error_line, actual_line,
                                alpha=0.2, color='red', label='Error')

        if self.show_pwm and len(arrays['pwm_output']) > 0:
            self.ax.plot(time, arrays['pwm_output'], 'm-',
                        linewidth=1.5, label='PWM Output', alpha=0.7)

        if self.show_p_term and len(arrays['p_term']) > 0:
            self.ax.plot(time, arrays['p_term'], 'c:',
                        linewidth=1.5, label='P Term', alpha=0.7)

        if self.show_i_term and len(arrays['i_term']) > 0:
            self.ax.plot(time, arrays['i_term'], 'y:',
                        linewidth=1.5, label='I Term', alpha=0.7)

        if self.show_d_term and len(arrays['d_term']) > 0:
            self.ax.plot(time, arrays['d_term'], 'orange',
                        linestyle=':', linewidth=1.5, label='D Term', alpha=0.7)

        # Set limits
        if len(time) > 0:
            self.ax.set_xlim(max(0, time[-1] - 30), time[-1] + 1)
        self.ax.set_ylim(-10, 110)

        self.ax.legend(loc='upper right', fontsize=9)
        self.canvas.draw()

    def clear_plot(self):
        """Clear all plot data"""
        self.data.clear()
        self.ax.clear()
        self.ax.grid(True, alpha=0.3)
        self.ax.set_xlabel('Time (s)')
        self.ax.set_ylabel('Speed / PWM (%)')
        self.ax.set_title('Motor Control - Real-Time Multi-Trace Plot')
        self.canvas.draw()
        logger.info("Plot cleared")

    def save_plot(self):
        """Save current plot as PNG"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Plot",
            f"motor_plot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
            "PNG Files (*.png);;All Files (*)"
        )

        if filename:
            try:
                self.figure.savefig(filename, dpi=300, bbox_inches='tight')
                logger.info(f"Plot saved to {filename}")
            except Exception as e:
                logger.error(f"Failed to save plot: {e}")

    def export_csv(self):
        """Export data to CSV"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export CSV",
            f"motor_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv);;All Files (*)"
        )

        if filename:
            try:
                arrays = self.data.get_arrays()

                with open(filename, 'w', newline='') as f:
                    writer = csv.writer(f)

                    # Header
                    writer.writerow([
                        'Time(s)', 'Target(%)', 'Actual(%)', 'Error(%)',
                        'PWM(%)', 'P_Term', 'I_Term', 'D_Term'
                    ])

                    # Data rows
                    for i in range(len(arrays['time'])):
                        writer.writerow([
                            arrays['time'][i],
                            arrays['target_speed'][i],
                            arrays['actual_speed'][i],
                            arrays['error'][i],
                            arrays['pwm_output'][i],
                            arrays['p_term'][i],
                            arrays['i_term'][i],
                            arrays['d_term'][i]
                        ])

                logger.info(f"Data exported to CSV: {filename}")
            except Exception as e:
                logger.error(f"Failed to export CSV: {e}")

    def export_json(self):
        """Export data to JSON"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export JSON",
            f"motor_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json);;All Files (*)"
        )

        if filename:
            try:
                arrays = self.data.get_arrays()

                export_data = {
                    'metadata': {
                        'controller': self.data.controller_name,
                        'start_time': self.data.start_time.isoformat(),
                        'export_time': datetime.now().isoformat(),
                        'samples': len(arrays['time'])
                    },
                    'data': {
                        'time': arrays['time'].tolist(),
                        'target_speed': arrays['target_speed'].tolist(),
                        'actual_speed': arrays['actual_speed'].tolist(),
                        'error': arrays['error'].tolist(),
                        'pwm_output': arrays['pwm_output'].tolist(),
                        'p_term': arrays['p_term'].tolist(),
                        'i_term': arrays['i_term'].tolist(),
                        'd_term': arrays['d_term'].tolist()
                    }
                }

                with open(filename, 'w') as f:
                    json.dump(export_data, f, indent=2)

                logger.info(f"Data exported to JSON: {filename}")
            except Exception as e:
                logger.error(f"Failed to export JSON: {e}")

    def export_matlab(self):
        """Export data to MATLAB .m file"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export MATLAB",
            f"motor_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.m",
            "MATLAB Files (*.m);;All Files (*)"
        )

        if filename:
            try:
                arrays = self.data.get_arrays()

                with open(filename, 'w') as f:
                    f.write(f"% Motor Control Data - {self.data.controller_name}\n")
                    f.write(f"% Exported: {datetime.now().isoformat()}\n\n")

                    # Write arrays
                    f.write(f"time = {self._array_to_matlab(arrays['time'])};\n")
                    f.write(f"target_speed = {self._array_to_matlab(arrays['target_speed'])};\n")
                    f.write(f"actual_speed = {self._array_to_matlab(arrays['actual_speed'])};\n")
                    f.write(f"error = {self._array_to_matlab(arrays['error'])};\n")
                    f.write(f"pwm_output = {self._array_to_matlab(arrays['pwm_output'])};\n")
                    f.write(f"p_term = {self._array_to_matlab(arrays['p_term'])};\n")
                    f.write(f"i_term = {self._array_to_matlab(arrays['i_term'])};\n")
                    f.write(f"d_term = {self._array_to_matlab(arrays['d_term'])};\n\n")

                    f.write("% Plot example\n")
                    f.write("figure;\n")
                    f.write("plot(time, target_speed, 'b--', time, actual_speed, 'g-');\n")
                    f.write("xlabel('Time (s)');\n")
                    f.write("ylabel('Speed (%)');\n")
                    f.write("legend('Target', 'Actual');\n")
                    f.write("grid on;\n")

                logger.info(f"Data exported to MATLAB: {filename}")
            except Exception as e:
                logger.error(f"Failed to export MATLAB: {e}")

    @staticmethod
    def _array_to_matlab(arr: np.ndarray) -> str:
        """Convert numpy array to MATLAB array format"""
        return '[' + ' '.join([f'{x:.6f}' for x in arr]) + ']'


class FFTAnalysisWidget(QWidget):
    """
    Frequency domain analysis using FFT
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Create matplotlib figure
        self.figure = Figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        self.ax = self.figure.add_subplot(111)
        self.ax.set_xlabel('Frequency (Hz)')
        self.ax.set_ylabel('Magnitude')
        self.ax.set_title('FFT Analysis - Frequency Response')
        self.ax.grid(True, alpha=0.3)

        # Control panel
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)

        self.signal_combo = QComboBox()
        self.signal_combo.addItems(['Error', 'PWM Output', 'Actual Speed'])
        self.signal_combo.currentTextChanged.connect(self.update_plot)

        self.analyze_btn = QPushButton("Analyze")
        self.analyze_btn.clicked.connect(self.analyze)

        control_layout.addWidget(QLabel("Signal:"))
        control_layout.addWidget(self.signal_combo)
        control_layout.addWidget(self.analyze_btn)
        control_layout.addStretch()

        # Layout
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        layout.addWidget(control_panel)

        self.data_source = None

    def set_data_source(self, plot_widget: AdvancedPlotWidget):
        """Set the data source"""
        self.data_source = plot_widget

    def analyze(self):
        """Perform FFT analysis"""
        if not self.data_source or len(self.data_source.data.time) < 10:
            logger.warning("Not enough data for FFT analysis")
            return

        arrays = self.data_source.data.get_arrays()

        # Select signal based on combo box
        signal_name = self.signal_combo.currentText()
        if signal_name == 'Error':
            signal_data = arrays['error']
        elif signal_name == 'PWM Output':
            signal_data = arrays['pwm_output']
        else:
            signal_data = arrays['actual_speed']

        # Calculate sampling frequency
        time_data = arrays['time']
        if len(time_data) < 2:
            return

        dt = np.mean(np.diff(time_data))
        sampling_freq = 1.0 / dt if dt > 0 else 10.0

        # Perform FFT
        N = len(signal_data)
        yf = fft(signal_data)
        xf = fftfreq(N, dt)[:N//2]

        # Magnitude spectrum
        magnitude = 2.0/N * np.abs(yf[:N//2])

        # Plot
        self.ax.clear()
        self.ax.plot(xf, magnitude, 'b-', linewidth=1.5)
        self.ax.set_xlabel('Frequency (Hz)')
        self.ax.set_ylabel('Magnitude')
        self.ax.set_title(f'FFT Analysis - {signal_name}')
        self.ax.grid(True, alpha=0.3)
        self.ax.set_xlim(0, min(10, sampling_freq / 2))

        # Find dominant frequency
        if len(magnitude) > 0:
            dominant_idx = np.argmax(magnitude)
            dominant_freq = xf[dominant_idx]
            self.ax.axvline(dominant_freq, color='r', linestyle='--',
                          label=f'Dominant: {dominant_freq:.2f} Hz')
            self.ax.legend()

        self.canvas.draw()
        logger.info(f"FFT analysis complete for {signal_name}")

    def update_plot(self):
        """Update plot when signal selection changes"""
        self.analyze()


class PhasePlotWidget(QWidget):
    """
    Phase portrait (error vs delta_error)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Create matplotlib figure
        self.figure = Figure(figsize=(8, 8))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        self.ax = self.figure.add_subplot(111)
        self.ax.set_xlabel('Error (%)')
        self.ax.set_ylabel('Error Rate (%/s)')
        self.ax.set_title('Phase Portrait - Error vs Error Rate')
        self.ax.grid(True, alpha=0.3)
        self.ax.axhline(0, color='k', linewidth=0.5)
        self.ax.axvline(0, color='k', linewidth=0.5)

        # Control panel
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)

        self.update_btn = QPushButton("Update Phase Plot")
        self.update_btn.clicked.connect(self.update_plot)

        control_layout.addWidget(self.update_btn)
        control_layout.addStretch()

        # Layout
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        layout.addWidget(control_panel)

        self.data_source = None

    def set_data_source(self, plot_widget: AdvancedPlotWidget):
        """Set the data source"""
        self.data_source = plot_widget

    def update_plot(self):
        """Update phase portrait"""
        if not self.data_source or len(self.data_source.data.time) < 2:
            logger.warning("Not enough data for phase plot")
            return

        arrays = self.data_source.data.get_arrays()

        error = arrays['error']
        time_data = arrays['time']

        # Calculate error rate
        error_rate = np.gradient(error, time_data)

        # Plot
        self.ax.clear()

        # Plot trajectory
        self.ax.plot(error, error_rate, 'b-', alpha=0.6, linewidth=1)

        # Mark start and end
        if len(error) > 0:
            self.ax.plot(error[0], error_rate[0], 'go', markersize=10, label='Start')
            self.ax.plot(error[-1], error_rate[-1], 'ro', markersize=10, label='End')

        # Origin (target state)
        self.ax.plot(0, 0, 'k*', markersize=15, label='Target')

        self.ax.set_xlabel('Error (%)')
        self.ax.set_ylabel('Error Rate (%/s)')
        self.ax.set_title('Phase Portrait - Error vs Error Rate')
        self.ax.grid(True, alpha=0.3)
        self.ax.axhline(0, color='k', linewidth=0.5)
        self.ax.axvline(0, color='k', linewidth=0.5)
        self.ax.legend()

        self.canvas.draw()
        logger.info("Phase plot updated")


class ComparisonWidget(QWidget):
    """
    Side-by-side comparison of multiple controller runs
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.recordings = []  # List of (name, data_dict) tuples

        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Create matplotlib figure with subplots
        self.figure = Figure(figsize=(12, 8))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        # Create subplots
        self.ax_speed = self.figure.add_subplot(221)
        self.ax_error = self.figure.add_subplot(222)
        self.ax_pwm = self.figure.add_subplot(223)
        self.ax_metrics = self.figure.add_subplot(224)

        # Control panel
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)

        self.add_current_btn = QPushButton("Add Current Run")
        self.add_current_btn.clicked.connect(self.add_current_recording)

        self.clear_btn = QPushButton("Clear Comparisons")
        self.clear_btn.clicked.connect(self.clear_recordings)

        self.load_btn = QPushButton("Load Recording")
        self.load_btn.clicked.connect(self.load_recording)

        control_layout.addWidget(self.add_current_btn)
        control_layout.addWidget(self.load_btn)
        control_layout.addWidget(self.clear_btn)
        control_layout.addStretch()

        # Layout
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        layout.addWidget(control_panel)

        self.data_source = None

    def set_data_source(self, plot_widget: AdvancedPlotWidget):
        """Set the data source"""
        self.data_source = plot_widget

    def add_current_recording(self):
        """Add current run to comparison"""
        if not self.data_source or len(self.data_source.data.time) < 10:
            logger.warning("Not enough data to add to comparison")
            return

        arrays = self.data_source.data.get_arrays()
        name = f"{self.data_source.data.controller_name}_{datetime.now().strftime('%H:%M:%S')}"

        self.recordings.append((name, arrays.copy()))
        self.update_comparison()
        logger.info(f"Added recording: {name}")

    def load_recording(self):
        """Load recording from JSON file"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Recording",
            "",
            "JSON Files (*.json);;All Files (*)"
        )

        if filename:
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)

                arrays = {
                    key: np.array(values)
                    for key, values in data['data'].items()
                }

                name = data['metadata'].get('controller', 'Loaded')
                self.recordings.append((name, arrays))
                self.update_comparison()
                logger.info(f"Loaded recording from {filename}")
            except Exception as e:
                logger.error(f"Failed to load recording: {e}")

    def clear_recordings(self):
        """Clear all recordings"""
        self.recordings.clear()
        self.update_comparison()
        logger.info("Cleared all recordings")

    def update_comparison(self):
        """Update comparison plots"""
        # Clear all axes
        for ax in [self.ax_speed, self.ax_error, self.ax_pwm, self.ax_metrics]:
            ax.clear()

        if len(self.recordings) == 0:
            self.ax_speed.text(0.5, 0.5, 'No recordings to compare',
                              ha='center', va='center', transform=self.ax_speed.transAxes)
            self.canvas.draw()
            return

        colors = plt.cm.tab10(np.linspace(0, 1, len(self.recordings)))

        metrics_data = {'overshoot': [], 'settling': [], 'ss_error': []}
        labels = []

        for (name, arrays), color in zip(self.recordings, colors):
            time = arrays['time']

            # Speed comparison
            self.ax_speed.plot(time, arrays['actual_speed'],
                             label=name, color=color, linewidth=1.5)
            if len(time) > 0:
                self.ax_speed.plot(time, arrays['target_speed'],
                                  '--', color=color, alpha=0.3, linewidth=1)

            # Error comparison
            self.ax_error.plot(time, arrays['error'],
                             label=name, color=color, linewidth=1.5)

            # PWM comparison
            self.ax_pwm.plot(time, arrays['pwm_output'],
                           label=name, color=color, linewidth=1.5)

            # Calculate metrics
            if len(arrays['error']) > 0:
                overshoot = np.max(np.abs(arrays['error']))
                settling_idx = np.where(np.abs(arrays['error']) < 5)[0]
                settling = time[settling_idx[0]] if len(settling_idx) > 0 else time[-1]
                ss_error = np.mean(np.abs(arrays['error'][-100:])) if len(arrays['error']) > 100 else 0

                metrics_data['overshoot'].append(overshoot)
                metrics_data['settling'].append(settling)
                metrics_data['ss_error'].append(ss_error)
                labels.append(name)

        # Configure speed plot
        self.ax_speed.set_xlabel('Time (s)')
        self.ax_speed.set_ylabel('Speed (%)')
        self.ax_speed.set_title('Speed Comparison')
        self.ax_speed.grid(True, alpha=0.3)
        self.ax_speed.legend(fontsize=8)

        # Configure error plot
        self.ax_error.set_xlabel('Time (s)')
        self.ax_error.set_ylabel('Error (%)')
        self.ax_error.set_title('Error Comparison')
        self.ax_error.grid(True, alpha=0.3)
        self.ax_error.axhline(0, color='k', linewidth=0.5)
        self.ax_error.legend(fontsize=8)

        # Configure PWM plot
        self.ax_pwm.set_xlabel('Time (s)')
        self.ax_pwm.set_ylabel('PWM (%)')
        self.ax_pwm.set_title('PWM Output Comparison')
        self.ax_pwm.grid(True, alpha=0.3)
        self.ax_pwm.legend(fontsize=8)

        # Metrics bar chart
        x = np.arange(len(labels))
        width = 0.25

        self.ax_metrics.bar(x - width, metrics_data['overshoot'], width,
                          label='Max Overshoot (%)', color='r', alpha=0.7)
        self.ax_metrics.bar(x, metrics_data['settling'], width,
                          label='Settling Time (s)', color='g', alpha=0.7)
        self.ax_metrics.bar(x + width, metrics_data['ss_error'], width,
                          label='SS Error (%)', color='b', alpha=0.7)

        self.ax_metrics.set_xlabel('Controller')
        self.ax_metrics.set_ylabel('Metric Value')
        self.ax_metrics.set_title('Performance Metrics Comparison')
        self.ax_metrics.set_xticks(x)
        self.ax_metrics.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
        self.ax_metrics.legend(fontsize=8)
        self.ax_metrics.grid(True, alpha=0.3, axis='y')

        self.figure.tight_layout()
        self.canvas.draw()
        logger.info(f"Comparison updated with {len(self.recordings)} recordings")


class AdvancedPlottingTabWidget(QTabWidget):
    """
    Main tab widget containing all advanced plotting features
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Create widgets
        self.multi_trace = AdvancedPlotWidget()
        self.fft_analysis = FFTAnalysisWidget()
        self.phase_plot = PhasePlotWidget()
        self.comparison = ComparisonWidget()

        # Link data sources
        self.fft_analysis.set_data_source(self.multi_trace)
        self.phase_plot.set_data_source(self.multi_trace)
        self.comparison.set_data_source(self.multi_trace)

        # Add tabs
        self.addTab(self.multi_trace, "Multi-Trace Plot")
        self.addTab(self.fft_analysis, "FFT Analysis")
        self.addTab(self.phase_plot, "Phase Portrait")
        self.addTab(self.comparison, "Controller Comparison")

        logger.info("Advanced plotting system initialized")

    def add_sample(
        self,
        time: float,
        target: float,
        actual: float,
        error: float,
        pwm: float,
        p_term: float = 0.0,
        i_term: float = 0.0,
        d_term: float = 0.0
    ):
        """Add sample to multi-trace plot"""
        self.multi_trace.add_sample(time, target, actual, error, pwm,
                                   p_term, i_term, d_term)

    def update_plots(self):
        """Update all visible plots"""
        self.multi_trace.update_plot()

        # Update other tabs if visible
        current_tab = self.currentWidget()
        if current_tab == self.fft_analysis:
            self.fft_analysis.analyze()
        elif current_tab == self.phase_plot:
            self.phase_plot.update_plot()
