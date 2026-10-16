"""Regression checks for the real control algorithm using an output-recording test adapter."""
import threading
import time

import pytest

from config import get_config
from control_runtime import ThreadSafeController


class RecordedOutput:
    def __init__(self):
        self.values = []
        self.armed = False
    def arm(self):
        self.armed = True
    def ChangeDutyCycle(self, value):
        self.values.append(value)


class FixedController:
    def __init__(self, output=37):
        self.output = output
    def reset(self):
        return None
    def compute_output(self, target, current):
        return self.output


@pytest.fixture
def worker():
    hardware = RecordedOutput()
    result = ThreadSafeController(FixedController(), get_config(), hardware)
    result.set_target_speed(50)
    return result, hardware


def test_enabling_requires_a_recent_sample(worker):
    control, hardware = worker
    assert not control.enable_motor()
    control.update_current_speed(30, time.monotonic() - 2)
    assert not control.enable_motor()
    control.update_current_speed(30)
    assert control.enable_motor()
    assert hardware.armed


def test_sensor_freshness_is_not_refreshed_by_control_iterations(worker):
    control, hardware = worker
    control.update_current_speed(30)
    assert control.enable_motor()
    control._step()
    assert hardware.values[-1] == 37
    control.last_update_time = time.monotonic() - 2
    control._step()
    assert not control.motor_enabled
    assert control.current_pwm == 0
    assert hardware.values[-1] == 0


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -1, 101])
def test_invalid_sensor_samples_stop_motor(worker, value):
    control, hardware = worker
    control.update_current_speed(30)
    assert control.enable_motor()
    control._step()
    control.update_current_speed(value)
    assert not control.motor_enabled
    assert hardware.values[-1] == 0


def test_older_queued_sensor_samples_cannot_replace_newer_measurement(worker):
    control, _ = worker
    now = time.monotonic()
    control.update_current_speed(40, now)
    control.update_current_speed(90, now - 0.2)
    assert control.current_speed == 40
    assert control.last_update_time == now


def test_stop_writes_zero_before_worker_has_exited(worker):
    control, hardware = worker
    control.update_current_speed(30)
    control.enable_motor()
    control._step()
    control.stop()
    control._step()
    assert hardware.values == [37, 0]
    assert not control.enable_motor()


def test_stopping_during_computation_rejects_late_output(worker):
    control, hardware = worker
    entered, release = threading.Event(), threading.Event()
    class BlockingController(FixedController):
        def compute_output(self, target, current):
            entered.set()
            assert release.wait(2)
            return 80
    control.set_controller(BlockingController())
    control.update_current_speed(30)
    control.enable_motor()
    thread = threading.Thread(target=control._step)
    thread.start()
    assert entered.wait(2)
    control.disable_motor()
    release.set()
    thread.join(2)
    assert not thread.is_alive()
    assert hardware.values[-1] == 0
    assert 80 not in hardware.values


@pytest.mark.parametrize('output', [float('nan'), float('inf'), -1, 101])
def test_worker_stops_when_controller_returns_invalid_output(worker, output):
    control, hardware = worker
    control.controller = FixedController(output)
    control.update_current_speed(30)
    control.enable_motor()
    control.run()
    assert not control.motor_enabled
    assert hardware.values[-1] == 0


def test_controller_replacement_disables_previous_output(worker):
    control, hardware = worker
    control.update_current_speed(30)
    control.enable_motor()
    control._step()
    control.set_controller(FixedController(60))
    control._step()
    assert not control.motor_enabled
    assert hardware.values[-1] == 0
    assert 60 not in hardware.values


def test_new_sensor_sample_cannot_validate_output_computed_from_expired_input(worker, monkeypatch):
    clock = [0.0]
    monkeypatch.setattr('control_runtime.time.monotonic', lambda: clock[0])
    control, hardware = worker
    class SlowController(FixedController):
        def compute_output(self, target, current):
            clock[0] = 2.0
            control.update_current_speed(40, 2.0)
            return 80
    control.controller = SlowController()
    control.update_current_speed(30, 0.0)
    assert control.enable_motor()
    control._step()
    assert not control.motor_enabled
    assert hardware.values[-1] == 0
    assert 80 not in hardware.values


def test_failed_zero_write_is_reported_as_unknown_output_without_recursive_failure(worker):
    control, hardware = worker
    control.update_current_speed(30)
    control.enable_motor()
    def failed_write(value):
        raise OSError('GPIO disconnected')
    hardware.ChangeDutyCycle = failed_write
    faults = []
    control.faulted.connect(faults.append)
    control.disable_motor()
    control.disable_motor()
    assert not control.motor_enabled
    import math
    assert math.isnan(control.current_pwm)
    assert len(faults) == 1
