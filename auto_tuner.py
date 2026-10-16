"""Relay-feedback PID candidates measured through the configured motor hardware."""

import json
import math
import time

import numpy as np
from dotenv import set_key

from config import get_config
from conventional_controllers import PIDController
from motor_hardware import hardware_session
from performance_metrics import PerformanceMetrics


def positive(value, name):
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f'{name} must be finite and positive')


class AutoTuner:
    """Estimate Ziegler-Nichols candidates from observed relay oscillations."""

    def __init__(self, config=None, hardware=None):
        self.config = config or get_config()
        self.hardware = hardware

    def tune_pid(self, target_speed=50.0, relay_amplitude=20.0, test_duration=60.0):
        ku, tu = self.relay_test(target_speed, relay_amplitude, test_duration)
        if ku is None:
            raise RuntimeError('No usable relay oscillations were measured; no gains were produced')
        return self.validate_parameters(*self.calculate_ziegler_nichols(ku, tu))

    def relay_test(self, target_speed, relay_amplitude, duration):
        positive(duration, 'duration')
        positive(relay_amplitude, 'relay_amplitude')
        if not math.isfinite(target_speed) or not relay_amplitude <= target_speed <= 100 - relay_amplitude:
            raise ValueError('Relay outputs must remain within 0..100 without clipping')
        crossings, speeds = [], []
        high = True
        started = time.monotonic()
        with hardware_session(self.config, self.hardware) as hardware:
            while time.monotonic() - started < duration:
                hardware.ChangeDutyCycle(target_speed + relay_amplitude if high else target_speed - relay_amplitude)
                current = hardware.read_speed(0.3)
                if not math.isfinite(current) or not 0 <= current <= 100:
                    raise ValueError('Invalid measured speed')
                error = target_speed - current
                if (high and error < 0) or (not high and error > 0):
                    high = not high
                    crossings.append(time.monotonic() - started)
                speeds.append(current)
        if len(crossings) < 6:
            return None, None
        # Discard two startup crossings; each subsequent interval is a half-period.
        periods = np.diff(crossings[2:])
        amplitude = (max(speeds) - min(speeds)) / 2
        if amplitude <= 0 or not np.all(np.isfinite(periods)) or np.any(periods <= 0):
            return None, None
        return float(4 * relay_amplitude / (np.pi * amplitude)), float(2 * np.mean(periods))

    def calculate_ziegler_nichols(self, ku, tu):
        positive(ku, 'ku')
        positive(tu, 'tu')
        return 0.6 * ku, 1.2 * ku / tu, 0.075 * ku * tu

    def validate_parameters(self, kp, ki, kd):
        if not all(math.isfinite(x) and x >= 0 for x in (kp, ki, kd)):
            raise ValueError('PID gains must be finite and nonnegative')
        return float(kp), float(ki), float(kd)

    def measure_speed(self, duration=0.3):
        with hardware_session(self.config, self.hardware) as hardware:
            return hardware.read_speed(duration)

    def test_parameters(self, kp, ki, kd, target_speed=50.0, test_duration=30.0):
        positive(test_duration, 'test_duration')
        if not math.isfinite(target_speed) or not 0 < target_speed <= 100:
            raise ValueError('target_speed must be in (0, 100]')
        controller = PIDController(*self.validate_parameters(kp, ki, kd))
        metrics = PerformanceMetrics()
        started = time.monotonic()
        with hardware_session(self.config, self.hardware) as hardware:
            while time.monotonic() - started < test_duration:
                current = hardware.read_speed(0.3)
                hardware.ChangeDutyCycle(controller.compute_output(target_speed, current))
                metrics.update(target_speed, current)
        result = metrics.calculate(target_speed)
        return {'overshoot_percent': result['overshoot'], 'settling_time': result['settling_time'],
                'ss_error': result['ss_error'], 'kp': kp, 'ki': ki, 'kd': kd}


def run_auto_tuning():
    print('Relay testing operates the connected motor. Secure the rig and verify its configuration first.')
    input('Press ENTER to run the relay test, or Ctrl+C to cancel: ')
    tuner = AutoTuner()
    gains = tuner.tune_pid()
    print('Candidate gains:', gains)
    print(json.dumps(tuner.test_parameters(*gains), indent=2, allow_nan=False))
    if input('Save these candidate gains to .env? [y/N]: ').strip().lower() == 'y':
        path = tuner.config.paths.base_dir / '.env'
        for name, value in zip(('CONTROLLER_PID_KP', 'CONTROLLER_PID_KI', 'CONTROLLER_PID_KD'), gains):
            set_key(path, name, str(value))
        print('Saved candidate gains. Restart the application to load them.')


if __name__ == '__main__':
    run_auto_tuning()
