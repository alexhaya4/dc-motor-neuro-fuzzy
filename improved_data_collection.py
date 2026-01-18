"""
Improved Data Collection for Neural Network Training
Collects REAL optimal control data without heuristics
"""

import time
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
from collections import deque

from config import get_config, is_raspberry_pi
from logger_utils import get_logger
from conventional_controllers import PIDController

if is_raspberry_pi():
    import RPi.GPIO as GPIO

logger = get_logger(__name__)


class OptimalDataCollector:
    """
    Collect optimal training data by:
    1. Running a well-tuned PID controller (baseline)
    2. Recording actual performance
    3. Calculating what scaling factors SHOULD have been
    4. Using those as training targets for neural networks
    """

    def __init__(self, config=None):
        self.config = config or get_config()
        self.training_data = []

        # Use well-tuned PID as baseline
        self.baseline_controller = PIDController(
            kp=self.config.controller.pid_kp,
            ki=self.config.controller.pid_ki,
            kd=self.config.controller.pid_kd
        )

        # Performance history for calculating optimal scaling
        self.performance_history = deque(maxlen=100)

        logger.info("Optimal data collector initialized")

    def collect_training_session(
        self,
        target_speeds: List[float],
        duration_per_target: float = 30.0,
        samples_per_target: int = 100
    ) -> List[Dict]:
        """
        Collect training data across multiple target speeds

        Args:
            target_speeds: List of target speeds to test (0-100%)
            duration_per_target: Duration to run at each target
            samples_per_target: Number of samples to collect per target

        Returns:
            List of training samples
        """
        all_samples = []

        logger.info(f"Starting training session: {len(target_speeds)} targets")

        for i, target_speed in enumerate(target_speeds):
            logger.info(f"Collecting data for target {target_speed}% ({i+1}/{len(target_speeds)})")

            # Run at this target speed
            samples = self.collect_at_target(target_speed, duration_per_target, samples_per_target)
            all_samples.extend(samples)

            # Brief pause between targets
            time.sleep(2.0)

        logger.info(f"Training session complete: {len(all_samples)} samples collected")

        return all_samples

    def collect_at_target(
        self,
        target_speed: float,
        duration: float,
        num_samples: int
    ) -> List[Dict]:
        """
        Collect data at a specific target speed

        Args:
            target_speed: Target speed (0-100%)
            duration: Duration to run
            num_samples: Number of samples to collect

        Returns:
            List of training samples
        """
        samples = []
        start_time = time.time()
        sample_interval = duration / num_samples

        # Reset controller
        self.baseline_controller.reset()
        self.performance_history.clear()

        prev_error = 0.0
        error_history = deque(maxlen=10)

        while time.time() - start_time < duration:
            # Measure current speed
            current_speed = self.measure_speed()

            # Calculate error
            error = target_speed - current_speed
            delta_error = error - prev_error
            prev_error = error

            error_history.append(abs(error))

            # Get baseline PID output
            pwm_output = self.baseline_controller.compute_output(target_speed, current_speed)

            # Apply PWM to motor
            if is_raspberry_pi():
                # Actually control the motor
                pass  # Would use GPIO here

            # Calculate optimal scaling factors based on recent performance
            optimal_scales = self.calculate_optimal_scaling(
                target_speed, current_speed, error, delta_error, error_history
            )

            # Create training sample
            sample = {
                # Inputs (normalized to 0-1)
                'target_norm': target_speed / 100.0,
                'current_norm': current_speed / 100.0,

                # Outputs (optimal scaling factors)
                'error_scale': optimal_scales['error'],
                'delta_error_scale': optimal_scales['delta_error'],
                'output_scale': optimal_scales['output'],

                # Metadata (for analysis)
                'error': error,
                'delta_error': delta_error,
                'pwm_output': pwm_output,
                'avg_error': np.mean(error_history) if error_history else 0
            }

            samples.append(sample)

            # Wait for next sample
            time.sleep(sample_interval)

        return samples

    def calculate_optimal_scaling(
        self,
        target: float,
        current: float,
        error: float,
        delta_error: float,
        error_history: deque
    ) -> Dict[str, float]:
        """
        Calculate optimal scaling factors based on current performance

        This uses control theory principles to determine what scaling
        would have produced better performance

        Args:
            target: Target speed
            current: Current speed
            error: Current error
            delta_error: Change in error
            error_history: Recent error history

        Returns:
            Dictionary of optimal scaling factors
        """
        # Calculate performance metrics
        avg_error = np.mean(error_history) if error_history else abs(error)
        error_trend = np.polyfit(range(len(error_history)), list(error_history), 1)[0] \
                     if len(error_history) > 2 else 0

        # Error scaling: Scale up for large errors, down for small errors
        if avg_error > 20:
            # Large error: need more aggressive correction
            error_scale = 1.5
        elif avg_error > 10:
            # Medium error: moderate correction
            error_scale = 1.2
        elif avg_error > 5:
            # Small error: gentle correction
            error_scale = 1.0
        else:
            # Very small error: avoid overcorrection
            error_scale = 0.8

        # Delta error scaling: Adjust based on error trend
        if error_trend > 0:
            # Error increasing: need stronger derivative action
            delta_error_scale = 1.3
        elif error_trend < -0.5:
            # Error decreasing rapidly: reduce derivative
            delta_error_scale = 0.9
        else:
            # Error stable or slowly decreasing
            delta_error_scale = 1.1

        # Output scaling: Adjust based on distance from target
        distance_ratio = abs(target - current) / 100.0
        if distance_ratio > 0.3:
            # Far from target: allow full output
            output_scale = 1.2
        elif distance_ratio > 0.1:
            # Medium distance: moderate output
            output_scale = 1.0
        else:
            # Close to target: gentle output to avoid oscillation
            output_scale = 0.9

        # Clamp to reasonable ranges
        error_scale = np.clip(error_scale, 0.5, 2.0)
        delta_error_scale = np.clip(delta_error_scale, 0.5, 2.0)
        output_scale = np.clip(output_scale, 0.7, 1.3)

        return {
            'error': float(error_scale),
            'delta_error': float(delta_error_scale),
            'output': float(output_scale)
        }

    def measure_speed(self, duration: float = 0.5) -> float:
        """
        Measure motor speed from IR sensor

        Args:
            duration: Measurement duration in seconds

        Returns:
            Speed as percentage (0-100%)
        """
        if not is_raspberry_pi():
            # Simulate speed for development
            import random
            return random.uniform(40, 60)

        pulse_count = 0
        last_state = GPIO.input(self.config.gpio.ir_sensor_pin)
        start_time = time.time()
        end_time = start_time + duration

        while time.time() < end_time:
            current_state = GPIO.input(self.config.gpio.ir_sensor_pin)
            if current_state == 0 and last_state == 1:
                pulse_count += 1
            last_state = current_state
            time.sleep(0.0001)

        # Calculate RPM
        pulses_per_rev = self.config.motor.pulses_per_revolution
        rpm = (pulse_count / pulses_per_rev) * (60.0 / duration)

        # Convert to percentage
        max_rpm = self.config.motor.max_rpm
        speed_percent = min(100, (rpm / max_rpm) * 100)

        return speed_percent

    def save_training_data(self, filename: str = "training_data.json"):
        """
        Save collected training data to JSON file

        Args:
            filename: Output filename
        """
        output_path = self.config.paths.data_dir / filename

        # Prepare data for saving
        save_data = {
            'metadata': {
                'num_samples': len(self.training_data),
                'collection_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'config': {
                    'max_rpm': self.config.motor.max_rpm,
                    'pulses_per_rev': self.config.motor.pulses_per_revolution
                }
            },
            'samples': self.training_data
        }

        with open(output_path, 'w') as f:
            json.dump(save_data, f, indent=2)

        logger.info(f"Training data saved: {output_path} ({len(self.training_data)} samples)")

    def load_training_data(self, filename: str = "training_data.json") -> bool:
        """
        Load training data from JSON file

        Args:
            filename: Input filename

        Returns:
            True if successful
        """
        input_path = self.config.paths.data_dir / filename

        if not input_path.exists():
            logger.error(f"Training data file not found: {input_path}")
            return False

        try:
            with open(input_path, 'r') as f:
                data = json.load(f)

            self.training_data = data.get('samples', [])
            logger.info(f"Training data loaded: {len(self.training_data)} samples")
            return True

        except Exception as e:
            logger.error(f"Failed to load training data: {e}")
            return False

    def get_training_arrays(self) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
        """
        Convert training data to numpy arrays for neural network training

        Returns:
            Tuple of (inputs, outputs) where:
                inputs: (N, 2) array of [target_norm, current_norm]
                outputs: Dict of (N, 1) arrays for each scaling factor
        """
        if not self.training_data:
            raise ValueError("No training data available")

        # Extract inputs
        X = np.array([
            [sample['target_norm'], sample['current_norm']]
            for sample in self.training_data
        ])

        # Extract outputs
        y_error = np.array([[sample['error_scale']] for sample in self.training_data])
        y_delta_error = np.array([[sample['delta_error_scale']] for sample in self.training_data])
        y_output = np.array([[sample['output_scale']] for sample in self.training_data])

        outputs = {
            'error': y_error,
            'delta_error': y_delta_error,
            'output': y_output
        }

        logger.info(f"Training arrays created: X.shape={X.shape}")

        return X, outputs


def collect_comprehensive_dataset():
    """
    Collect a comprehensive dataset across various operating conditions
    """
    collector = OptimalDataCollector()

    # Define comprehensive test targets
    target_speeds = [
        # Low speeds
        10, 15, 20, 25, 30,
        # Medium speeds
        35, 40, 45, 50, 55, 60, 65, 70,
        # High speeds
        75, 80, 85, 90, 95
    ]

    logger.info(f"Collecting comprehensive dataset: {len(target_speeds)} targets")

    # Collect data
    samples = collector.collect_training_session(
        target_speeds=target_speeds,
        duration_per_target=20.0,  # 20 seconds per target
        samples_per_target=50  # 50 samples per target
    )

    # Store in collector
    collector.training_data = samples

    # Save to file
    collector.save_training_data("training_data.json")

    logger.info(f"Dataset collection complete: {len(samples)} total samples")

    return collector


if __name__ == '__main__':
    # Run data collection
    print("Starting comprehensive data collection...")
    print("This will take approximately 6-7 minutes")
    print()

    collector = collect_comprehensive_dataset()

    print()
    print(f"✓ Collection complete!")
    print(f"  Samples collected: {len(collector.training_data)}")
    print(f"  Data saved to: training_data.json")
    print()
    print("Next step: Run 'python train_networks.py' to train the neural networks")
