"""Raspberry Pi motor I/O with explicit ownership and an independent output watchdog."""

import importlib
import math
import threading
import time
from contextlib import contextmanager

from config import get_config, is_raspberry_pi
from constants import WATCHDOG_TIMEOUT_SEC, WATCHDOG_CHECK_INTERVAL_SEC, SPEED_SENSOR_SLEEP_MICROSEC


class MotorHardware:
    """Own the configured GPIO channels. No simulated readings or outputs are substituted."""

    def __init__(self, config=None):
        self.config = config or get_config()
        if not is_raspberry_pi():
            raise RuntimeError('Motor hardware requires a Raspberry Pi. Use --offline to inspect the GUI without hardware.')
        self.gpio = importlib.import_module('RPi.GPIO')
        self._lock = threading.RLock()
        self._closed = threading.Event()
        self._armed = False
        self._fault = None
        self._duty = 0.0
        self._last_write = time.monotonic()
        self._pwm = None
        pins = self.config.gpio
        self._channels = (pins.motor_in1, pins.motor_in2, pins.motor_ena, pins.ir_sensor_pin)
        try:
            self.gpio.setmode(self.gpio.BCM)
            for pin in self._channels[:3]:
                self.gpio.setup(pin, self.gpio.OUT, initial=self.gpio.LOW)
            self.gpio.setup(pins.ir_sensor_pin, self.gpio.IN)
            self._pwm = self.gpio.PWM(pins.motor_ena, self.config.motor.pwm_frequency)
            self._pwm.start(0)
        except Exception:
            try:
                if self._pwm is not None:
                    self._pwm.stop()
            finally:
                self.gpio.cleanup(self._channels)
            raise
        self._watchdog = threading.Thread(target=self._watch, name='motor-output-watchdog', daemon=True)
        self._watchdog.start()

    def arm(self):
        with self._lock:
            if self._closed.is_set():
                raise RuntimeError('Motor hardware is closed')
            self._off()
            self._fault = None
            self._armed = True
            self._last_write = time.monotonic()

    def _off(self):
        """Attempt all off operations even if a GPIO operation fails."""
        self._duty = 0.0
        try:
            self._pwm.ChangeDutyCycle(0)
        finally:
            try:
                self.gpio.output(self.config.gpio.motor_in1, self.gpio.LOW)
            finally:
                self.gpio.output(self.config.gpio.motor_in2, self.gpio.LOW)

    def ChangeDutyCycle(self, duty):
        """Validate an output and refresh its deadline only after a successful write."""
        with self._lock:
            if self._closed.is_set():
                raise RuntimeError('Motor hardware is closed')
            if not math.isfinite(duty) or not 0 <= duty <= 100:
                self._armed = False
                self._off()
                raise ValueError('PWM duty must be finite and between 0 and 100')
            if duty == 0:
                self._off()
                return
            if self._duty and time.monotonic() - self._last_write > WATCHDOG_TIMEOUT_SEC:
                self._fault = 'Motor output watchdog expired'
                self._armed = False
                self._off()
            if not self._armed:
                raise RuntimeError(self._fault or 'Motor must be explicitly armed')
            try:
                self.gpio.output(self.config.gpio.motor_in1, self.gpio.HIGH)
                self.gpio.output(self.config.gpio.motor_in2, self.gpio.LOW)
                self._pwm.ChangeDutyCycle(duty)
            except Exception:
                self._armed = False
                self._fault = 'Motor output failed'
                self._off()
                raise
            self._duty = float(duty)
            self._last_write = time.monotonic()

    def _watch(self):
        while not self._closed.wait(WATCHDOG_CHECK_INTERVAL_SEC):
            with self._lock:
                if self._duty and time.monotonic() - self._last_write > WATCHDOG_TIMEOUT_SEC:
                    self._armed = False
                    self._fault = 'Motor output watchdog expired'
                    try:
                        self._off()
                    except Exception:
                        # Keep retrying the physical off operation until closed.
                        self._duty = -1.0

    def read_speed(self, duration=0.5, cancel=None):
        """Return measured speed in percent using debounced falling edges and elapsed time."""
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError('Measurement duration must be finite and positive')
        if self._closed.is_set():
            raise RuntimeError('Motor hardware is closed')
        pin = self.config.gpio.ir_sensor_pin
        previous = self.gpio.input(pin)
        pulses = 0
        last_edge = -math.inf
        started = time.monotonic()
        while time.monotonic() - started < duration:
            if self._closed.is_set() or (cancel is not None and cancel.is_set()):
                raise InterruptedError('Speed measurement cancelled')
            state = self.gpio.input(pin)
            now = time.monotonic()
            if previous and not state and now - last_edge >= self.config.motor.min_pulse_width_ms / 1000:
                pulses += 1
                last_edge = now
            previous = state
            time.sleep(SPEED_SENSOR_SLEEP_MICROSEC)
        elapsed = time.monotonic() - started
        rpm = pulses * 60 / (self.config.motor.pulses_per_revolution * elapsed)
        return min(100.0, rpm * 100 / self.config.motor.max_rpm)

    def stop(self):
        """Stop output, terminate the watchdog and release only this instance's channels."""
        with self._lock:
            if self._closed.is_set():
                return
            self._armed = False
            try:
                self._off()
            finally:
                self._closed.set()
                try:
                    self._pwm.stop()
                finally:
                    self.gpio.cleanup(self._channels)
        self._watchdog.join(timeout=WATCHDOG_CHECK_INTERVAL_SEC * 3)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.stop()


@contextmanager
def hardware_session(config, hardware=None):
    """Arm a real I/O session and always disable output, including on cancellation."""
    owned = hardware is None
    hardware = MotorHardware(config) if owned else hardware
    try:
        hardware.arm()
        yield hardware
    finally:
        try:
            hardware.ChangeDutyCycle(0)
        finally:
            if owned:
                hardware.stop()
