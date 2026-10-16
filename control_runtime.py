"""Qt workers for measured sensor samples and serialized motor control."""

import math
import threading
import time
from collections import deque

from PyQt5.QtCore import QThread, pyqtSignal

from constants import (CONTROL_LOOP_INTERVAL_SEC, SPEED_MEASUREMENT_DURATION_SEC,
                       SENSOR_POLL_INTERVAL_SEC, SPEED_SENSOR_SMOOTHING_SAMPLES,
                       WATCHDOG_TIMEOUT_SEC)
from performance_metrics import PerformanceMetrics
from logger_utils import get_logger

logger = get_logger(__name__)


class ThreadSafeSpeedSensor(QThread):
    speed_updated = pyqtSignal(float, float)
    faulted = pyqtSignal(str)

    def __init__(self, config, hardware):
        super().__init__()
        self.config = config
        self.hardware = hardware
        self._cancel = threading.Event()
        self.rpm_history = deque(maxlen=SPEED_SENSOR_SMOOTHING_SAMPLES)

    def run(self):
        try:
            while not self._cancel.is_set():
                speed = self.hardware.read_speed(SPEED_MEASUREMENT_DURATION_SEC, self._cancel)
                self.rpm_history.append(speed)
                self.speed_updated.emit(sum(self.rpm_history) / len(self.rpm_history), time.monotonic())
                self._cancel.wait(SENSOR_POLL_INTERVAL_SEC)
        except InterruptedError:
            if not self._cancel.is_set():
                self.faulted.emit('Speed measurement was interrupted')
        except Exception as exc:
            logger.exception('Speed sensor failed')
            self.faulted.emit(str(exc))

    def stop(self):
        self._cancel.set()


class ThreadSafeController(QThread):
    pwm_updated = pyqtSignal(float)
    metrics_updated = pyqtSignal(dict)
    faulted = pyqtSignal(str)

    def __init__(self, controller, config, motor_pwm=None):
        super().__init__()
        self.controller = controller
        self.config = config
        self.motor_pwm = motor_pwm
        self.state_lock = threading.RLock()
        self._stop = threading.Event()
        self._generation = 0
        self._reset_pending = True
        self.target_speed = 0.0
        self.current_speed = 0.0
        self.current_pwm = 0.0
        self.motor_enabled = False
        self.last_update_time = None
        self.watchdog_timeout = WATCHDOG_TIMEOUT_SEC
        self.metrics = PerformanceMetrics()
        self._metrics_sample = None
        self._output_fault_reported = False

    def run(self):
        try:
            while not self._stop.is_set():
                self._step()
                self._stop.wait(CONTROL_LOOP_INTERVAL_SEC)
        except Exception as exc:
            logger.exception('Motor control failed')
            self.disable_motor()
            self.faulted.emit(str(exc))
        finally:
            self.disable_motor()

    def _fresh(self):
        return self.last_update_time is not None and 0 <= time.monotonic() - self.last_update_time <= self.watchdog_timeout

    def _step(self):
        with self.state_lock:
            if not self.motor_enabled or self._stop.is_set():
                return
            if not self._fresh():
                self.disable_motor()
                self.faulted.emit('No fresh speed-sensor sample; motor stopped')
                return
            target, current = self.target_speed, self.current_speed
            controller, generation = self.controller, self._generation
            sampled_at = self.last_update_time
            reset = self._reset_pending
            self._reset_pending = False
        if reset:
            controller.reset()
        pwm = float(controller.compute_output(target, current))
        if not math.isfinite(pwm) or not 0 <= pwm <= 100:
            raise ValueError('Controller returned an invalid PWM duty')
        with self.state_lock:
            if not self.motor_enabled or self._stop.is_set() or generation != self._generation:
                return
            if time.monotonic() - sampled_at > self.watchdog_timeout:
                self.disable_motor()
                self.faulted.emit('Sensor sample expired during computation; motor stopped')
                return
            self.motor_pwm.ChangeDutyCycle(pwm)
            self.current_pwm = pwm
            if sampled_at != self._metrics_sample:
                self.metrics.update(target, current)
                self._metrics_sample = sampled_at
        self.pwm_updated.emit(pwm)

    def set_target_speed(self, speed):
        if not math.isfinite(speed) or not 0 <= speed <= 100:
            raise ValueError('Target speed must be a finite percentage')
        with self.state_lock:
            if speed != self.target_speed:
                self._generation += 1
                self._reset_pending = True
                self.metrics.reset()
            self.target_speed = speed

    def update_current_speed(self, speed, sampled_at=None):
        sampled_at = time.monotonic() if sampled_at is None else sampled_at
        if not math.isfinite(speed) or not 0 <= speed <= 100 or not math.isfinite(sampled_at) or sampled_at > time.monotonic():
            self.disable_motor()
            self.faulted.emit('Invalid speed-sensor sample; motor stopped')
            return
        with self.state_lock:
            if self.last_update_time is None or sampled_at >= self.last_update_time:
                self.current_speed = speed
                self.last_update_time = sampled_at

    def enable_motor(self):
        with self.state_lock:
            if self.motor_pwm is None or self._stop.is_set() or not self._fresh():
                self.faulted.emit('Motor requires connected hardware and a fresh sensor sample')
                return False
            try:
                self.motor_pwm.arm()
            except Exception as exc:
                self.disable_motor()
                self.faulted.emit(str(exc))
                return False
            self._generation += 1
            self._reset_pending = True
            self.metrics.reset()
            self.motor_enabled = True
            self._output_fault_reported = False
            return True

    def disable_motor(self):
        fault = None
        report = False
        with self.state_lock:
            self.motor_enabled = False
            self.current_pwm = 0.0
            self._generation += 1
            self._reset_pending = True
            if self.motor_pwm is not None:
                try:
                    self.motor_pwm.ChangeDutyCycle(0)
                except Exception as exc:
                    self.current_pwm = float('nan')
                    fault = f'GPIO could not confirm zero output: {exc}'
                    report = not self._output_fault_reported
                    self._output_fault_reported = True
                    logger.exception('Motor shutdown output failed')
        if fault is None:
            self.pwm_updated.emit(0.0)
        elif report:
            self.faulted.emit(fault)

    def set_controller(self, controller):
        self.disable_motor()
        with self.state_lock:
            self.controller = controller
            self.metrics.reset()

    def reset_controller(self):
        self.disable_motor()
        with self.state_lock:
            self.metrics.reset()

    def request_metrics(self):
        with self.state_lock:
            metrics = self.metrics.calculate(self.target_speed)
        self.metrics_updated.emit(metrics)

    def stop(self):
        self._stop.set()
        self.disable_motor()
