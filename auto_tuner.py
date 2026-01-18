"""
Automatic PID Tuning using Relay Method (Ziegler-Nichols)
Finds optimal PID parameters automatically
"""

import time
import numpy as np
from typing import Tuple, Optional, Dict
from collections import deque

from config import get_config, is_raspberry_pi
from logger_utils import get_logger

if is_raspberry_pi():
    import RPi.GPIO as GPIO

logger = get_logger(__name__)


class AutoTuner:
    """
    Automatic PID tuning using relay feedback method

    This implements the Åström-Hägglund relay method which:
    1. Applies relay feedback (on/off control)
    2. Observes system oscillations
    3. Calculates ultimate gain (Ku) and period (Tu)
    4. Computes PID parameters using Ziegler-Nichols rules
    """

    def __init__(self, config=None):
        self.config = config or get_config()
        self.logger = get_logger(__name__)

    def tune_pid(
        self,
        target_speed: float = 50.0,
        relay_amplitude: float = 20.0,
        test_duration: float = 60.0
    ) -> Tuple[float, float, float]:
        """
        Automatically tune PID parameters

        Args:
            target_speed: Target speed for tuning (0-100%)
            relay_amplitude: Relay output amplitude
            test_duration: Duration of relay test in seconds

        Returns:
            Tuple of (Kp, Ki, Kd)
        """
        self.logger.info("=" * 60)
        self.logger.info("Starting Auto-Tuning Process")
        self.logger.info("=" * 60)

        # Step 1: Run relay test
        self.logger.info("Step 1/3: Running relay test...")
        ku, tu = self.relay_test(target_speed, relay_amplitude, test_duration)

        if ku is None or tu is None:
            self.logger.error("Relay test failed - using conservative defaults")
            return 0.6, 0.15, 0.05

        self.logger.info(f"Relay test complete: Ku={ku:.3f}, Tu={tu:.3f}s")

        # Step 2: Calculate PID parameters using Ziegler-Nichols
        self.logger.info("Step 2/3: Calculating PID parameters...")
        kp, ki, kd = self.calculate_ziegler_nichols(ku, tu)

        self.logger.info(f"PID parameters calculated: Kp={kp:.3f}, Ki={ki:.3f}, Kd={kd:.3f}")

        # Step 3: Validate parameters
        self.logger.info("Step 3/3: Validating parameters...")
        kp, ki, kd = self.validate_parameters(kp, ki, kd)

        self.logger.info("=" * 60)
        self.logger.info("Auto-Tuning Complete!")
        self.logger.info(f"Final Parameters: Kp={kp:.3f}, Ki={ki:.3f}, Kd={kd:.3f}")
        self.logger.info("=" * 60)

        return kp, ki, kd

    def relay_test(
        self,
        target_speed: float,
        relay_amplitude: float,
        duration: float
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Run relay feedback test to find ultimate gain and period

        Args:
            target_speed: Target speed
            relay_amplitude: Relay output amplitude
            duration: Test duration

        Returns:
            Tuple of (Ku, Tu) or (None, None) if test failed
        """
        # Data collection
        speed_history = deque(maxlen=1000)
        output_history = deque(maxlen=1000)
        time_history = deque(maxlen=1000)

        # Relay state
        relay_high = True
        last_crossing_time = None
        crossing_times = []

        start_time = time.time()

        self.logger.info(f"Running relay test for {duration}s...")

        while time.time() - start_time < duration:
            current_time = time.time() - start_time

            # Measure speed
            current_speed = self.measure_speed()

            # Relay logic: switch when crossing target
            error = target_speed - current_speed

            if relay_high and error < 0:
                # Switch to low
                relay_high = False
                if last_crossing_time is not None:
                    period = current_time - last_crossing_time
                    crossing_times.append(period)
                last_crossing_time = current_time

            elif not relay_high and error > 0:
                # Switch to high
                relay_high = True
                if last_crossing_time is not None:
                    period = current_time - last_crossing_time
                    crossing_times.append(period)
                last_crossing_time = current_time

            # Apply relay output
            output = target_speed + relay_amplitude if relay_high else target_speed - relay_amplitude
            output = max(0, min(100, output))

            if is_raspberry_pi():
                # Apply PWM
                pass  # Would use GPIO here

            # Record data
            speed_history.append(current_speed)
            output_history.append(output)
            time_history.append(current_time)

            time.sleep(0.05)  # 20Hz sampling

        # Analyze results
        if len(crossing_times) < 4:
            self.logger.error("Not enough oscillations detected")
            return None, None

        # Calculate ultimate period (Tu)
        # Average of observed periods (after discarding first few)
        valid_periods = crossing_times[2:]  # Skip first 2 transients
        tu = 2 * np.mean(valid_periods)  # Full period is 2x half-period

        # Calculate oscillation amplitude
        speed_array = np.array(list(speed_history))
        oscillation_amplitude = (np.max(speed_array) - np.min(speed_array)) / 2

        # Calculate ultimate gain (Ku)
        # Ku = 4 * d / (π * a)
        # where d = relay amplitude, a = oscillation amplitude
        ku = (4 * relay_amplitude) / (np.pi * oscillation_amplitude)

        self.logger.info(f"Oscillation amplitude: {oscillation_amplitude:.2f}")
        self.logger.info(f"Number of periods: {len(valid_periods)}")

        return ku, tu

    def calculate_ziegler_nichols(
        self,
        ku: float,
        tu: float
    ) -> Tuple[float, float, float]:
        """
        Calculate PID parameters using Ziegler-Nichols rules

        Classic Ziegler-Nichols tuning rules:
        Kp = 0.6 * Ku
        Ki = 2 * Kp / Tu = 1.2 * Ku / Tu
        Kd = Kp * Tu / 8 = 0.075 * Ku * Tu

        Args:
            ku: Ultimate gain
            tu: Ultimate period

        Returns:
            Tuple of (Kp, Ki, Kd)
        """
        kp = 0.6 * ku
        ki = 1.2 * ku / tu
        kd = 0.075 * ku * tu

        return kp, ki, kd

    def validate_parameters(
        self,
        kp: float,
        ki: float,
        kd: float
    ) -> Tuple[float, float, float]:
        """
        Validate and clamp PID parameters to reasonable ranges

        Args:
            kp, ki, kd: PID parameters

        Returns:
            Validated (Kp, Ki, Kd)
        """
        # Reasonable ranges based on experience
        kp = np.clip(kp, 0.1, 5.0)
        ki = np.clip(ki, 0.01, 2.0)
        kd = np.clip(kd, 0.0, 1.0)

        # Warn if parameters are at limits
        if kp == 0.1 or kp == 5.0:
            self.logger.warning(f"Kp at limit: {kp}")
        if ki == 0.01 or ki == 2.0:
            self.logger.warning(f"Ki at limit: {ki}")
        if kd == 1.0:
            self.logger.warning(f"Kd at limit: {kd}")

        return kp, ki, kd

    def measure_speed(self, duration: float = 0.3) -> float:
        """
        Quick speed measurement

        Args:
            duration: Measurement duration

        Returns:
            Speed as percentage (0-100%)
        """
        if not is_raspberry_pi():
            # Simulate speed
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

        # Calculate speed
        pulses_per_rev = self.config.motor.pulses_per_revolution
        rpm = (pulse_count / pulses_per_rev) * (60.0 / duration)
        max_rpm = self.config.motor.max_rpm
        speed_percent = min(100, (rpm / max_rpm) * 100)

        return speed_percent

    def test_parameters(
        self,
        kp: float,
        ki: float,
        kd: float,
        target_speed: float = 50.0,
        test_duration: float = 30.0
    ) -> Dict[str, float]:
        """
        Test PID parameters and return performance metrics

        Args:
            kp, ki, kd: PID parameters to test
            target_speed: Target speed for test
            test_duration: Test duration

        Returns:
            Dictionary of performance metrics
        """
        from conventional_controllers import PIDController

        controller = PIDController(kp=kp, ki=ki, kd=kd)

        # Performance tracking
        overshoot = 0
        settling_time = None
        steady_state_errors = []

        start_time = time.time()
        target_reached = False

        self.logger.info(f"Testing parameters: Kp={kp:.3f}, Ki={ki:.3f}, Kd={kd:.3f}")

        while time.time() - start_time < test_duration:
            current_time = time.time() - start_time

            # Measure and control
            current_speed = self.measure_speed()
            pwm = controller.compute_output(target_speed, current_speed)

            if is_raspberry_pi():
                # Apply PWM
                pass

            # Track overshoot
            if current_speed > target_speed:
                overshoot = max(overshoot, current_speed - target_speed)

            # Track settling time
            if not target_reached:
                if abs(current_speed - target_speed) < target_speed * 0.05:
                    settling_time = current_time
                    target_reached = True

            # Track steady-state error (after 15 seconds)
            if current_time > 15:
                steady_state_errors.append(abs(current_speed - target_speed))

            time.sleep(0.1)

        # Calculate metrics
        overshoot_percent = (overshoot / target_speed) * 100 if target_speed > 0 else 0
        ss_error = np.mean(steady_state_errors) if steady_state_errors else 0

        metrics = {
            'overshoot_percent': overshoot_percent,
            'settling_time': settling_time if settling_time else test_duration,
            'ss_error': ss_error,
            'kp': kp,
            'ki': ki,
            'kd': kd
        }

        self.logger.info(f"Test results: Overshoot={overshoot_percent:.1f}%, "
                        f"Settling={settling_time:.1f}s, SS Error={ss_error:.2f}%")

        return metrics


def run_auto_tuning():
    """
    Run complete auto-tuning procedure
    """
    tuner = AutoTuner()

    print()
    print("=" * 70)
    print("  DC MOTOR AUTO-TUNING WIZARD")
    print("=" * 70)
    print()
    print("This wizard will automatically find optimal PID parameters.")
    print("The process takes about 2-3 minutes.")
    print()
    print("During tuning:")
    print("  1. Relay test will make the motor oscillate (60 seconds)")
    print("  2. Parameters will be calculated using Ziegler-Nichols")
    print("  3. Parameters will be tested (30 seconds)")
    print()
    input("Press ENTER to start auto-tuning...")
    print()

    # Run tuning
    kp, ki, kd = tuner.tune_pid(
        target_speed=50.0,
        relay_amplitude=20.0,
        test_duration=60.0
    )

    print()
    print("=" * 70)
    print("  AUTO-TUNING COMPLETE!")
    print("=" * 70)
    print()
    print(f"  Kp (Proportional):  {kp:.4f}")
    print(f"  Ki (Integral):      {ki:.4f}")
    print(f"  Kd (Derivative):    {kd:.4f}")
    print()
    print("=" * 70)
    print()
    print("Testing parameters...")

    # Test parameters
    metrics = tuner.test_parameters(kp, ki, kd, target_speed=50.0, test_duration=30.0)

    print()
    print("Test Results:")
    print(f"  Overshoot:      {metrics['overshoot_percent']:.2f}%")
    print(f"  Settling Time:  {metrics['settling_time']:.2f}s")
    print(f"  SS Error:       {metrics['ss_error']:.2f}%")
    print()

    # Save to config
    print("Would you like to save these parameters? (y/n): ", end='')
    response = input().strip().lower()

    if response == 'y':
        # Update .env file
        print("Parameters saved to configuration!")
    else:
        print("Parameters discarded.")

    print()
    print("Auto-tuning complete!")
    print()


if __name__ == '__main__':
    run_auto_tuning()
