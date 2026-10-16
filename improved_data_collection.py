"""Measured motor samples with explicitly heuristic scaling-factor labels."""

import json
import math
import time
from collections import deque
from pathlib import Path

import numpy as np

from config import get_config
from conventional_controllers import PIDController
from motor_hardware import hardware_session


class HeuristicDataCollector:
    """Record physical feedback; scaling labels are heuristic, not measured optima."""

    def __init__(self, config=None, hardware=None):
        self.config = config or get_config()
        self.hardware = hardware
        self.training_data = []
        self.baseline_controller = PIDController()

    def collect_training_session(self, target_speeds, duration_per_target=30.0, samples_per_target=100):
        if not target_speeds:
            raise ValueError('At least one target is required')
        for target in target_speeds:
            self.collect_at_target(target, duration_per_target, samples_per_target)
        return list(self.training_data)

    def collect_at_target(self, target_speed, duration, num_samples):
        if not math.isfinite(target_speed) or not 0 <= target_speed <= 100:
            raise ValueError('Target must be a finite speed percentage')
        if not math.isfinite(duration) or duration <= 0 or isinstance(num_samples, bool) or not isinstance(num_samples, int) or num_samples <= 0:
            raise ValueError('Duration and sample count must be positive')
        interval = duration / num_samples
        if interval < 0.01:
            raise ValueError('Sampling interval must be at least 0.01 seconds')
        samples, errors = [], deque(maxlen=10)
        previous = 0.0
        self.baseline_controller.reset()
        with hardware_session(self.config, self.hardware) as hardware:
            started = time.monotonic()
            for index in range(num_samples):
                deadline = started + (index + 1) * interval
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    current = hardware.read_speed(min(0.3, remaining))
                    if not math.isfinite(current) or not 0 <= current <= 100:
                        raise ValueError('Invalid measured speed')
                    error = target_speed - current
                    delta = error - previous
                    previous = error
                    errors.append(abs(error))
                    hardware.ChangeDutyCycle(self.baseline_controller.compute_output(target_speed, current))
                scales = self.calculate_heuristic_scaling(target_speed, current, error, delta, errors)
                samples.append({'target_speed': float(target_speed), 'actual_speed': float(current),
                                'error_scale': scales['error'], 'delta_error_scale': scales['delta_error'],
                                'output_scale': scales['output']})
        self.training_data.extend(samples)
        return samples

    @staticmethod
    def calculate_heuristic_scaling(target, current, error, delta_error, error_history):
        average = float(np.mean(error_history)) if error_history else abs(error)
        trend = float(np.polyfit(range(len(error_history)), list(error_history), 1)[0]) if len(error_history) > 2 else 0.0
        error_scale = 1.5 if average > 20 else 1.2 if average > 10 else 1.0 if average > 5 else 0.8
        delta_scale = 1.3 if trend > 0 else 0.9 if trend < -0.5 else 1.1
        distance = abs(target - current) / 100
        output_scale = 1.2 if distance > 0.3 else 1.0 if distance > 0.1 else 0.9
        return {'error': error_scale, 'delta_error': delta_scale, 'output': output_scale}

    calculate_optimal_scaling = calculate_heuristic_scaling  # Compatibility name; these labels are heuristic.

    def _data_path(self, filename):
        if not filename or Path(filename).name != filename:
            raise ValueError('Training-data filename must not contain path components')
        return self.config.paths.data_dir / filename

    def save_training_data(self, filename='training_data.json'):
        from nn_models import TRAINING_DATA_SCHEMA
        from jsonschema import validate
        validate(instance=self.training_data, schema=TRAINING_DATA_SCHEMA)
        payload = {'metadata': {'label_source': 'heuristic', 'measurement_source': 'gpio',
                                'max_rpm': self.config.motor.max_rpm,
                                'pulses_per_revolution': self.config.motor.pulses_per_revolution},
                   'samples': self.training_data}
        self._data_path(filename).write_text(json.dumps(payload, indent=2, allow_nan=False) + '\n')

    def load_training_data(self, filename='training_data.json'):
        from nn_models import NeuralNetworkTrainer
        samples = NeuralNetworkTrainer().load_training_data(self._data_path(filename))
        if samples is None:
            return False
        self.training_data = samples
        return True

    def get_training_arrays(self):
        if not self.training_data:
            raise ValueError('No training data available')
        X = np.array([[d['target_speed'], d['actual_speed']] for d in self.training_data], dtype=np.float32)
        y = {label: np.array([[d[key]] for d in self.training_data], dtype=np.float32)
             for label, key in [('error', 'error_scale'), ('delta_error', 'delta_error_scale'), ('output', 'output_scale')]}
        return X, y


OptimalDataCollector = HeuristicDataCollector


def collect_comprehensive_dataset():
    collector = HeuristicDataCollector()
    collector.collect_training_session(list(range(10, 100, 5)), 20.0, 50)
    collector.save_training_data()
    return collector


if __name__ == '__main__':
    print('Collecting physical motor data with heuristic scaling labels. Verify the rig and configuration first.')
    input('Press ENTER to start, or Ctrl+C to cancel: ')
    collector = collect_comprehensive_dataset()
    print(f'Saved {len(collector.training_data)} samples to {collector.config.paths.data_dir}')
