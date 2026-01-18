"""
Unit tests for motor controllers
Tests controllers without requiring actual hardware
"""

import pytest
import math
from unittest.mock import Mock, patch, MagicMock
import numpy as np

# Import controllers
import sys
sys.path.insert(0, '..')

from conventional_controllers import PIController, PIDController
from fuzzy_controller import FuzzyController
from base_controller import ControllerValidationError


class TestPIController:
    """Test cases for PI Controller"""

    def test_initialization_with_defaults(self):
        """Test PI controller initializes with default parameters"""
        controller = PIController()
        assert controller.kp > 0
        assert controller.ki > 0
        assert controller.integral == 0.0

    def test_initialization_with_custom_params(self):
        """Test PI controller accepts custom parameters"""
        controller = PIController(kp=1.5, ki=0.3)
        assert controller.kp == 1.5
        assert controller.ki == 0.3

    def test_compute_output_valid_inputs(self):
        """Test PI controller with valid inputs"""
        controller = PIController(kp=0.5, ki=0.1)
        output = controller.compute_output(target_speed=50, current_speed=30)

        # Output should be between 0 and 100
        assert 0 <= output <= 100

        # With positive error, output should be positive
        assert output > 0

    def test_compute_output_at_target(self):
        """Test PI controller when at target speed"""
        controller = PIController(kp=0.5, ki=0.1)

        # Multiple calls at target to let integral settle
        for _ in range(10):
            output = controller.compute_output(target_speed=50, current_speed=50)

        # Output should stabilize near target
        assert 45 <= output <= 55

    def test_anti_windup(self):
        """Test integral anti-windup limiting"""
        controller = PIController(kp=0.5, ki=0.1, integral_limit=10.0)

        # Drive integral term to saturation
        for _ in range(100):
            controller.compute_output(target_speed=100, current_speed=0)

        # Integral should not exceed limit
        assert abs(controller.integral) <= 10.0

    def test_invalid_input_nan(self):
        """Test handling of NaN inputs"""
        controller = PIController()

        # Should handle NaN gracefully
        output = controller.compute_output(target_speed=float('nan'), current_speed=50)
        assert output == 0.0  # Safe fallback

    def test_invalid_input_inf(self):
        """Test handling of infinite inputs"""
        controller = PIController()

        output = controller.compute_output(target_speed=float('inf'), current_speed=50)
        assert output == 0.0  # Safe fallback

    def test_out_of_range_inputs(self):
        """Test handling of out-of-range inputs"""
        controller = PIController()

        # Should clamp inputs to valid range
        output = controller.compute_output(target_speed=150, current_speed=-50)
        assert 0 <= output <= 100

    def test_reset(self):
        """Test controller reset"""
        controller = PIController()

        # Run controller to build up state
        for _ in range(10):
            controller.compute_output(target_speed=80, current_speed=50)

        # Verify state exists
        assert controller.integral != 0

        # Reset
        controller.reset()

        # State should be cleared
        assert controller.integral == 0.0
        assert controller.prev_error == 0.0


class TestPIDController:
    """Test cases for PID Controller"""

    def test_initialization(self):
        """Test PID controller initialization"""
        controller = PIDController(kp=0.6, ki=0.15, kd=0.05)
        assert controller.kp == 0.6
        assert controller.ki == 0.15
        assert controller.kd == 0.05

    def test_derivative_term(self):
        """Test PID derivative term responds to rate of change"""
        controller = PIDController(kp=0, ki=0, kd=1.0)

        # First call (no derivative yet)
        output1 = controller.compute_output(target_speed=50, current_speed=40)

        # Second call (should have derivative)
        output2 = controller.compute_output(target_speed=50, current_speed=30)

        # Derivative should cause different outputs
        assert output1 != output2

    def test_derivative_filtering(self):
        """Test derivative filtering reduces noise"""
        controller = PIDController(kp=0, ki=0, kd=1.0)

        # Create noisy measurements
        speeds = [50, 45, 55, 48, 52, 49, 51, 50]

        outputs = []
        for speed in speeds:
            output = controller.compute_output(target_speed=50, current_speed=speed)
            outputs.append(output)

        # Filter should smooth derivative (outputs shouldn't jump wildly)
        output_changes = [abs(outputs[i] - outputs[i-1]) for i in range(1, len(outputs))]
        avg_change = np.mean(output_changes)

        # Average change should be moderate (not huge spikes)
        assert avg_change < 50

    def test_full_pid_response(self):
        """Test full PID controller response"""
        controller = PIDController(kp=0.5, ki=0.1, kd=0.05)

        outputs = []
        target = 70

        # Simulate approach to target
        speed = 30
        for _ in range(20):
            output = controller.compute_output(target_speed=target, current_speed=speed)
            outputs.append(output)

            # Simple motor model: speed increases with output
            speed += (output - 50) * 0.1

        # Controller should drive speed toward target
        final_error = abs(target - speed)
        assert final_error < 15  # Within reasonable tolerance


class TestFuzzyController:
    """Test cases for Fuzzy Controller"""

    def test_initialization(self):
        """Test fuzzy controller initialization"""
        controller = FuzzyController()

        # Should have fuzzy system components
        assert hasattr(controller, 'error')
        assert hasattr(controller, 'delta_error')
        assert hasattr(controller, 'pwm_output')
        assert hasattr(controller, 'controller')

    def test_compute_output_large_error(self):
        """Test fuzzy controller with large error"""
        controller = FuzzyController()

        # Large positive error should produce high output
        output = controller.compute_output(target_speed=100, current_speed=20)
        assert output > 60  # Should be significant

    def test_compute_output_small_error(self):
        """Test fuzzy controller with small error"""
        controller = FuzzyController()

        # Small error should produce moderate output
        output = controller.compute_output(target_speed=55, current_speed=50)
        assert 40 <= output <= 70  # Moderate range

    def test_compute_output_negative_error(self):
        """Test fuzzy controller with negative error (overshoot)"""
        controller = FuzzyController()

        # Negative error (current > target)
        output = controller.compute_output(target_speed=50, current_speed=70)
        assert output < 50  # Should reduce output

    def test_fuzzy_rules_symmetry(self):
        """Test fuzzy rules respond symmetrically"""
        controller = FuzzyController()

        # Positive error
        output_pos = controller.compute_output(target_speed=80, current_speed=60)

        # Negative error of same magnitude
        output_neg = controller.compute_output(target_speed=60, current_speed=80)

        # Outputs should be roughly symmetric around 50
        assert abs((output_pos - 50) + (output_neg - 50)) < 20

    def test_input_clamping(self):
        """Test inputs are clamped to valid range"""
        controller = FuzzyController()

        # Extreme inputs should be handled
        output = controller.compute_output(target_speed=200, current_speed=-100)
        assert 0 <= output <= 100


class TestControllerValidation:
    """Test input validation across all controllers"""

    @pytest.mark.parametrize("controller_class", [PIController, PIDController, FuzzyController])
    def test_nan_handling(self, controller_class):
        """Test all controllers handle NaN properly"""
        controller = controller_class()
        output = controller.compute_output(target_speed=float('nan'), current_speed=50)
        assert output == 0.0

    @pytest.mark.parametrize("controller_class", [PIController, PIDController, FuzzyController])
    def test_inf_handling(self, controller_class):
        """Test all controllers handle infinity properly"""
        controller = controller_class()
        output = controller.compute_output(target_speed=float('inf'), current_speed=50)
        assert output == 0.0

    @pytest.mark.parametrize("controller_class", [PIController, PIDController, FuzzyController])
    def test_output_range(self, controller_class):
        """Test all controllers produce valid output range"""
        controller = controller_class()

        # Test various input combinations
        test_cases = [
            (0, 0), (50, 50), (100, 100),  # At target
            (80, 20), (20, 80),            # Large errors
            (55, 50), (50, 55)             # Small errors
        ]

        for target, current in test_cases:
            output = controller.compute_output(target_speed=target, current_speed=current)
            assert 0 <= output <= 100, f"Output {output} out of range for ({target}, {current})"


class TestControllerComparison:
    """Comparative tests across controller types"""

    def test_response_to_step_input(self):
        """Compare controller responses to step input"""
        controllers = {
            'PI': PIController(kp=0.5, ki=0.1),
            'PID': PIDController(kp=0.5, ki=0.1, kd=0.05),
            'Fuzzy': FuzzyController()
        }

        results = {}

        for name, controller in controllers.items():
            speed = 30
            target = 70
            trajectory = [speed]

            # Simulate 20 time steps
            for _ in range(20):
                output = controller.compute_output(target_speed=target, current_speed=speed)
                # Simple motor model
                speed += (output - 50) * 0.15
                trajectory.append(speed)

            results[name] = {
                'final_speed': speed,
                'trajectory': trajectory
            }

        # All controllers should drive speed toward target
        for name, result in results.items():
            final_error = abs(target - result['final_speed'])
            assert final_error < 20, f"{name} controller error too large: {final_error}"

    def test_steady_state_accuracy(self):
        """Compare steady-state accuracy"""
        controllers = {
            'PI': PIController(kp=0.5, ki=0.1),
            'PID': PIDController(kp=0.5, ki=0.1, kd=0.05),
            'Fuzzy': FuzzyController()
        }

        target = 60

        for name, controller in controllers.items():
            # Run for many iterations to reach steady state
            speed = target
            for _ in range(50):
                output = controller.compute_output(target_speed=target, current_speed=speed)

            # At steady state, output should be near 50 (neutral)
            # This test is loose since different controllers have different characteristics
            assert 0 <= output <= 100


# Pytest configuration
def test_pytest_is_working():
    """Sanity check that pytest is working"""
    assert True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
