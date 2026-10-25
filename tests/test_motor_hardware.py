"""GPIO protocol and watchdog unit tests. These do not certify a physical motor rig."""
import time
import types

import pytest

import motor_hardware
from config import get_config


class GPIORecorder:
    BCM, OUT, IN, LOW, HIGH = 11, 0, 1, 0, 1
    def __init__(self):
        self.levels = {}
        self.cleaned = None
        self.duty = 0
        self.fail_positive = False
    def setmode(self, mode):
        assert mode == self.BCM
    def setup(self, pin, mode, initial=None):
        if initial is not None:
            self.levels[pin] = initial
    def output(self, pin, level):
        self.levels[pin] = level
    def input(self, pin):
        return 1
    def PWM(self, pin, frequency):
        assert frequency == get_config().motor.pwm_frequency
        return self
    def start(self, duty):
        self.duty = duty
    def ChangeDutyCycle(self, duty):
        if duty > 0 and self.fail_positive:
            raise OSError('Test output-write failure')
        self.duty = duty
    def stop(self):
        self.duty = 0
    def cleanup(self, channels):
        self.cleaned = tuple(channels)


@pytest.fixture
def gpio(monkeypatch):
    recorder = GPIORecorder()
    original = motor_hardware.importlib.import_module
    monkeypatch.setattr(motor_hardware, 'is_raspberry_pi', lambda: True)
    monkeypatch.setattr(motor_hardware.importlib, 'import_module', lambda name: recorder if name == 'RPi.GPIO' else original(name))
    return recorder


def test_non_pi_is_rejected_without_substituting_simulation(monkeypatch):
    monkeypatch.setattr(motor_hardware, 'is_raspberry_pi', lambda: False)
    with pytest.raises(RuntimeError, match='--offline'):
        motor_hardware.MotorHardware()


def test_start_disabled_then_explicit_arm_and_stop(gpio):
    hardware = motor_hardware.MotorHardware()
    try:
        assert gpio.duty == 0
        with pytest.raises(RuntimeError, match='armed'):
            hardware.ChangeDutyCycle(20)
        hardware.arm()
        hardware.ChangeDutyCycle(37)
        assert gpio.duty == 37
        hardware.ChangeDutyCycle(0)
        assert gpio.duty == 0
        assert gpio.levels[get_config().gpio.motor_in1] == 0
        assert gpio.levels[get_config().gpio.motor_in2] == 0
    finally:
        hardware.stop()
    hardware.stop()
    assert gpio.cleaned == hardware._channels


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -1, 101])
def test_invalid_duty_disables_output(gpio, value):
    with motor_hardware.MotorHardware() as hardware:
        hardware.arm()
        hardware.ChangeDutyCycle(20)
        with pytest.raises(ValueError):
            hardware.ChangeDutyCycle(value)
        assert gpio.duty == 0
        with pytest.raises(RuntimeError):
            hardware.ChangeDutyCycle(20)


def test_gpio_write_failure_attempts_zero_output(gpio):
    with motor_hardware.MotorHardware() as hardware:
        hardware.arm()
        gpio.fail_positive = True
        with pytest.raises(OSError):
            hardware.ChangeDutyCycle(20)
        assert gpio.duty == 0
        assert gpio.levels[get_config().gpio.motor_in1] == 0


def test_watchdog_runs_independently_and_latches_until_explicit_arm(gpio, monkeypatch):
    monkeypatch.setattr(motor_hardware, 'WATCHDOG_TIMEOUT_SEC', 0.05)
    monkeypatch.setattr(motor_hardware, 'WATCHDOG_CHECK_INTERVAL_SEC', 0.005)
    with motor_hardware.MotorHardware() as hardware:
        hardware.arm()
        hardware.ChangeDutyCycle(40)
        deadline = time.monotonic() + 1
        while gpio.duty and time.monotonic() < deadline:
            time.sleep(0.01)
        assert gpio.duty == 0
        with pytest.raises(RuntimeError, match='watchdog'):
            hardware.ChangeDutyCycle(40)
        hardware.arm()
        hardware.ChangeDutyCycle(20)
        assert gpio.duty == 20


def test_measurement_uses_elapsed_time_and_pulses_per_revolution(gpio, monkeypatch):
    now = [0.0]
    states = iter([1, 0, 1, 0, 1, 1, 1, 1])
    gpio.input = lambda pin: next(states)
    config = types.SimpleNamespace(gpio=get_config().gpio,
        motor=types.SimpleNamespace(max_rpm=600, pulses_per_revolution=2, pwm_frequency=100, min_pulse_width_ms=1))
    gpio.PWM = lambda pin, freq: gpio
    with motor_hardware.MotorHardware(config) as hardware:
        monkeypatch.setattr(motor_hardware.time, 'monotonic', lambda: now[0])
        monkeypatch.setattr(motor_hardware.time, 'sleep', lambda _: now.__setitem__(0, now[0] + 0.1))
        assert hardware.read_speed(0.5) == pytest.approx(20)

@pytest.mark.parametrize('value', [None, '25', True, 10 ** 400])
def test_invalid_duty_type_or_unbounded_integer_forces_zero(gpio, value):
    with motor_hardware.MotorHardware() as hardware:
        hardware.arm()
        hardware.ChangeDutyCycle(25)
        with pytest.raises(ValueError, match='PWM duty'):
            hardware.ChangeDutyCycle(value)
        assert gpio.duty == 0
        assert gpio.levels[get_config().gpio.motor_in1] == gpio.LOW
        assert gpio.levels[get_config().gpio.motor_in2] == gpio.LOW
        with pytest.raises(RuntimeError, match='armed'):
            hardware.ChangeDutyCycle(25)
