"""
Conventional PID Controllers with proper validation and type hints
"""

import time
from typing import Optional

from base_controller import BaseController
from logger_utils import get_logger
from config import get_config
from constants import MIN_TIMESTEP_SECONDS, DEFAULT_DERIVATIVE_FILTER_ALPHA


class PIController(BaseController):
    """
    Proportional-Integral (PI) Controller with anti-windup

    Args:
        kp: Proportional gain
        ki: Integral gain
        integral_limit: Anti-windup limit for integral term
    """

    def __init__(
        self,
        kp: Optional[float] = None,
        ki: Optional[float] = None,
        integral_limit: Optional[float] = None
    ):
        super().__init__()

        # Load from config if not provided
        config = get_config()
        self.kp = kp if kp is not None else config.controller.pi_kp
        self.ki = ki if ki is not None else config.controller.pi_ki
        self.integral_limit = integral_limit if integral_limit is not None else config.controller.pi_integral_limit

        # Controller state
        self.integral = 0.0
        self.prev_time = time.time()

        self.logger.info(f"PI Controller initialized: Kp={self.kp}, Ki={self.ki}")

    def _compute_control_output(self, target_speed: float, current_speed: float) -> float:
        """
        Compute PI control output

        Args:
            target_speed: Validated target speed (0-100%)
            current_speed: Validated current speed (0-100%)

        Returns:
            PWM duty cycle (0-100%)
        """
        # Time delta
        current_time = time.time()
        dt = current_time - self.prev_time
        self.prev_time = current_time

        # Avoid computation if dt is too small
        if dt < MIN_TIMESTEP_SECONDS:
            dt = MIN_TIMESTEP_SECONDS

        # Calculate error
        error = target_speed - current_speed

        # Update integral term with anti-windup
        self.integral += error * dt

        # Apply anti-windup limits
        if self.integral > self.integral_limit:
            self.integral = self.integral_limit
            self.logger.debug(f"Integral windup limited to {self.integral_limit}")
        elif self.integral < -self.integral_limit:
            self.integral = -self.integral_limit
            self.logger.debug(f"Integral windup limited to -{self.integral_limit}")

        # Calculate output terms
        p_term = self.kp * error
        i_term = self.ki * self.integral

        output = p_term + i_term

        return output

    def reset(self) -> None:
        """Reset PI controller state"""
        super().reset()
        self.integral = 0.0
        self.prev_time = time.time()


class PIDController(BaseController):
    """
    Proportional-Integral-Derivative (PID) Controller with anti-windup and derivative filtering

    Args:
        kp: Proportional gain
        ki: Integral gain
        kd: Derivative gain
        integral_limit: Anti-windup limit for integral term
    """

    def __init__(
        self,
        kp: Optional[float] = None,
        ki: Optional[float] = None,
        kd: Optional[float] = None,
        integral_limit: Optional[float] = None
    ):
        super().__init__()

        # Load from config if not provided
        config = get_config()
        self.kp = kp if kp is not None else config.controller.pid_kp
        self.ki = ki if ki is not None else config.controller.pid_ki
        self.kd = kd if kd is not None else config.controller.pid_kd
        self.integral_limit = integral_limit if integral_limit is not None else config.controller.pid_integral_limit

        # Controller state
        self.integral = 0.0
        self.prev_time = time.time()
        self.derivative = 0.0

        # Derivative filtering (exponential moving average)
        self.derivative_filter_alpha = DEFAULT_DERIVATIVE_FILTER_ALPHA

        self.logger.info(f"PID Controller initialized: Kp={self.kp}, Ki={self.ki}, Kd={self.kd}")

    def _compute_control_output(self, target_speed: float, current_speed: float) -> float:
        """
        Compute PID control output

        Args:
            target_speed: Validated target speed (0-100%)
            current_speed: Validated current speed (0-100%)

        Returns:
            PWM duty cycle (0-100%)
        """
        # Time delta
        current_time = time.time()
        dt = current_time - self.prev_time
        self.prev_time = current_time

        # Avoid computation if dt is too small
        if dt < MIN_TIMESTEP_SECONDS:
            dt = MIN_TIMESTEP_SECONDS

        # Calculate error
        error = target_speed - current_speed

        # Update integral term with anti-windup
        self.integral += error * dt

        # Apply anti-windup limits
        if self.integral > self.integral_limit:
            self.integral = self.integral_limit
        elif self.integral < -self.integral_limit:
            self.integral = -self.integral_limit

        # Calculate derivative term with filtering to reduce noise
        raw_derivative = (error - self.prev_error) / dt if dt > 0 else 0.0

        # Apply exponential moving average filter
        self.derivative = (
            self.derivative_filter_alpha * raw_derivative +
            (1 - self.derivative_filter_alpha) * self.derivative
        )

        # Calculate output terms
        p_term = self.kp * error
        i_term = self.ki * self.integral
        d_term = self.kd * self.derivative

        output = p_term + i_term + d_term

        return output

    def reset(self) -> None:
        """Reset PID controller state"""
        super().reset()
        self.integral = 0.0
        self.derivative = 0.0
        self.prev_time = time.time()
