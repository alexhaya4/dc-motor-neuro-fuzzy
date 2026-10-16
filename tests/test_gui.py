from modern_motor_gui import ModernMotorControlGUI, RealTimePlotWidget
from animated_widgets import StatusIndicator


def test_offline_gui_has_no_motor_io_or_fabricated_readings(qapp):
    window = ModernMotorControlGUI(offline=True)
    try:
        assert window.motor_pwm is None
        assert window.controller_thread is None
        assert window.speed_sensor is None
        assert not window.start_button.isEnabled()
        assert 'unavailable' in window.actual_label.text()
        assert 'unavailable' in window.pwm_label.text()
        window.update_display()
        assert not window.plot_widget.actual_data
    finally:
        window.close()


def test_status_widget_initializes_before_first_paint(qapp):
    widget = StatusIndicator('Sensor')
    widget.setStatus('warning')
    widget.setStatus('ok')
    widget.close()


def test_plot_updates_axes_with_observed_points(qapp):
    widget = RealTimePlotWidget()
    widget.start_time -= 40
    widget.update_data(50, 45)
    point_time = widget.time_data[-1]
    minimum, maximum = widget.ax.get_xlim()
    assert minimum <= point_time <= maximum
    assert list(widget.line_actual.get_ydata()) == [45]
    widget.clear_data()
    assert not widget.time_data
    widget.close()
