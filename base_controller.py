"""
Base classes for motor controllers with proper validation and error handling
"""

from abc import ABC, abstractmethod
from typing import Tuple, Optional
import math
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

from logger_utils import get_logger, log_exception
from config import get_config
from constants import (
    MAX_SPEED_PERCENT,
    MIN_SPEED_PERCENT,
    MAX_PWM_DUTY_CYCLE,
    MIN_PWM_DUTY_CYCLE,
    FUZZY_UNIVERSE_MIN,
    FUZZY_UNIVERSE_MAX,
    FUZZY_ERROR_CLAMP_MIN,
    FUZZY_ERROR_CLAMP_MAX
)


class ControllerValidationError(Exception):
    """Raised when controller input validation fails"""
    pass


class BaseController(ABC):
    """Base class for all motor controllers with input validation"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.config = get_config()
        self.prev_speed = 0.0
        self.prev_error = 0.0

    def validate_inputs(self, target_speed: float, current_speed: float) -> Tuple[float, float]:
        """
        Validate controller inputs

        Args:
            target_speed: Desired motor speed (0-100%)
            current_speed: Current measured speed (0-100%)

        Returns:
            Tuple of validated (target_speed, current_speed)

        Raises:
            ControllerValidationError: If inputs are invalid
        """
        # Check for NaN or Inf
        if math.isnan(target_speed) or math.isinf(target_speed):
            raise ControllerValidationError(f"Invalid target_speed: {target_speed}")

        if math.isnan(current_speed) or math.isinf(current_speed):
            raise ControllerValidationError(f"Invalid current_speed: {current_speed}")

        # Check range
        if not (MIN_SPEED_PERCENT <= target_speed <= MAX_SPEED_PERCENT):
            self.logger.warning(
                f"target_speed {target_speed} out of range, "
                f"clamping to {MIN_SPEED_PERCENT}-{MAX_SPEED_PERCENT}"
            )
            target_speed = max(MIN_SPEED_PERCENT, min(MAX_SPEED_PERCENT, target_speed))

        if not (MIN_SPEED_PERCENT <= current_speed <= MAX_SPEED_PERCENT):
            self.logger.warning(
                f"current_speed {current_speed} out of range, "
                f"clamping to {MIN_SPEED_PERCENT}-{MAX_SPEED_PERCENT}"
            )
            current_speed = max(MIN_SPEED_PERCENT, min(MAX_SPEED_PERCENT, current_speed))

        return target_speed, current_speed

    @abstractmethod
    def _compute_control_output(self, target_speed: float, current_speed: float) -> float:
        """
        Internal method to compute control output (to be implemented by subclasses)

        Args:
            target_speed: Validated target speed (0-100%)
            current_speed: Validated current speed (0-100%)

        Returns:
            PWM duty cycle (0-100%)
        """
        pass

    def compute_output(self, target_speed: float, current_speed: float) -> float:
        """
        Compute controller output with validation

        Args:
            target_speed: Desired motor speed (0-100%)
            current_speed: Current measured speed (0-100%)

        Returns:
            PWM duty cycle (0-100%)
        """
        try:
            # Validate inputs
            target_speed, current_speed = self.validate_inputs(target_speed, current_speed)

            # Compute control output
            output = self._compute_control_output(target_speed, current_speed)

            # Update history
            self.prev_speed = current_speed
            self.prev_error = target_speed - current_speed

            # Clamp output
            output = max(MIN_PWM_DUTY_CYCLE, min(MAX_PWM_DUTY_CYCLE, output))

            return output

        except ControllerValidationError as e:
            log_exception(self.logger, "Controller validation error", e)
            return MIN_PWM_DUTY_CYCLE
        except (ValueError, TypeError, ArithmeticError) as e:
            # Catch specific numeric/type errors
            log_exception(self.logger, "Computation error in controller", e)
            return MIN_PWM_DUTY_CYCLE
        except Exception as e:
            # Last resort - log and fail safe
            log_exception(self.logger, "Unexpected error in controller computation", e)
            return MIN_PWM_DUTY_CYCLE

    def reset(self) -> None:
        """Reset controller state"""
        self.prev_speed = 0.0
        self.prev_error = 0.0
        self.logger.info(f"{self.__class__.__name__} reset")


class FuzzyControllerBase(BaseController):
    """
    Base class for fuzzy logic controllers
    Eliminates code duplication between fuzzy-based controllers
    """

    def __init__(self):
        super().__init__()
        self._initialize_fuzzy_system()

    def _initialize_fuzzy_system(self) -> None:
        """Initialize the fuzzy inference system"""
        try:
            # Get configuration (use constants as fallback)
            universe_min = getattr(self.config.controller, 'fuzzy_universe_min', FUZZY_UNIVERSE_MIN)
            universe_max = getattr(self.config.controller, 'fuzzy_universe_max', FUZZY_UNIVERSE_MAX)

            # Create fuzzy variables
            self.error = ctrl.Antecedent(
                np.arange(universe_min, universe_max + 1, 1), 'error'
            )
            self.delta_error = ctrl.Antecedent(
                np.arange(universe_min, universe_max + 1, 1), 'delta_error'
            )
            self.pwm_output = ctrl.Consequent(
                np.arange(MIN_PWM_DUTY_CYCLE, MAX_PWM_DUTY_CYCLE + 1, 1), 'pwm_output'
            )

            # Define membership functions
            self._define_membership_functions()

            # Define fuzzy rules
            rules = self._define_fuzzy_rules()

            # Create control system
            self.control_system = ctrl.ControlSystem(rules)
            self.controller = ctrl.ControlSystemSimulation(self.control_system)

            self.logger.info("Fuzzy system initialized successfully")

        except Exception as e:
            log_exception(self.logger, "Failed to initialize fuzzy system", e)
            raise

    def _define_membership_functions(self) -> None:
        """Define membership functions for fuzzy variables"""
        # Error membership functions
        self.error['NB'] = fuzz.trapmf(self.error.universe, [-100, -100, -80, -40])
        self.error['NS'] = fuzz.trimf(self.error.universe, [-60, -30, 0])
        self.error['ZE'] = fuzz.trimf(self.error.universe, [-20, 0, 20])
        self.error['PS'] = fuzz.trimf(self.error.universe, [0, 30, 60])
        self.error['PB'] = fuzz.trapmf(self.error.universe, [40, 80, 100, 100])

        # Delta error membership functions
        self.delta_error['NB'] = fuzz.trapmf(self.delta_error.universe, [-100, -100, -80, -40])
        self.delta_error['NS'] = fuzz.trimf(self.delta_error.universe, [-60, -30, 0])
        self.delta_error['ZE'] = fuzz.trimf(self.delta_error.universe, [-20, 0, 20])
        self.delta_error['PS'] = fuzz.trimf(self.delta_error.universe, [0, 30, 60])
        self.delta_error['PB'] = fuzz.trapmf(self.delta_error.universe, [40, 80, 100, 100])

        # Output membership functions
        self.pwm_output['VL'] = fuzz.trimf(self.pwm_output.universe, [0, 0, 25])
        self.pwm_output['LO'] = fuzz.trimf(self.pwm_output.universe, [0, 25, 50])
        self.pwm_output['ME'] = fuzz.trimf(self.pwm_output.universe, [25, 50, 75])
        self.pwm_output['HI'] = fuzz.trimf(self.pwm_output.universe, [50, 75, 100])
        self.pwm_output['VH'] = fuzz.trimf(self.pwm_output.universe, [75, 100, 100])

    def _define_fuzzy_rules(self) -> list:
        """
        Define fuzzy control rules

        Returns:
            List of fuzzy rules
        """
        rules = []

        # Core rules
        rules.append(ctrl.Rule(self.error['NB'] & self.delta_error['NB'], self.pwm_output['VL']))
        rules.append(ctrl.Rule(self.error['NB'] & self.delta_error['NS'], self.pwm_output['VL']))
        rules.append(ctrl.Rule(self.error['NB'] & self.delta_error['ZE'], self.pwm_output['LO']))

        rules.append(ctrl.Rule(self.error['NS'] & self.delta_error['NS'], self.pwm_output['LO']))
        rules.append(ctrl.Rule(self.error['NS'] & self.delta_error['ZE'], self.pwm_output['ME']))

        rules.append(ctrl.Rule(self.error['ZE'] & self.delta_error['ZE'], self.pwm_output['ME']))
        rules.append(ctrl.Rule(self.error['ZE'] & self.delta_error['NS'], self.pwm_output['ME']))
        rules.append(ctrl.Rule(self.error['ZE'] & self.delta_error['PS'], self.pwm_output['ME']))

        rules.append(ctrl.Rule(self.error['PS'] & self.delta_error['ZE'], self.pwm_output['HI']))
        rules.append(ctrl.Rule(self.error['PS'] & self.delta_error['PS'], self.pwm_output['HI']))

        rules.append(ctrl.Rule(self.error['PB'] & self.delta_error['PB'], self.pwm_output['VH']))
        rules.append(ctrl.Rule(self.error['PB'] & self.delta_error['ZE'], self.pwm_output['VH']))

        return rules

    def _compute_control_output(self, target_speed: float, current_speed: float) -> float:
        """
        Compute fuzzy control output

        Args:
            target_speed: Validated target speed (0-100%)
            current_speed: Validated current speed (0-100%)

        Returns:
            PWM duty cycle (0-100%)
        """
        # Calculate error and delta error
        error = target_speed - current_speed
        delta_error = error - self.prev_error

        # Clamp inputs to fuzzy universe
        error = max(min(error, FUZZY_ERROR_CLAMP_MAX), FUZZY_ERROR_CLAMP_MIN)
        delta_error = max(min(delta_error, FUZZY_ERROR_CLAMP_MAX), FUZZY_ERROR_CLAMP_MIN)

        try:
            # Set fuzzy inputs
            self.controller.input['error'] = error
            self.controller.input['delta_error'] = delta_error

            # Compute fuzzy output
            self.controller.compute()
            pwm = self.controller.output['pwm_output']

            return pwm

        except (ValueError, KeyError, RuntimeError) as e:
            log_exception(self.logger, "Fuzzy computation failed", e)
            # Return proportional control as fallback
            proportional_gain = 0.5
            fallback_output = (MAX_PWM_DUTY_CYCLE / 2) + error * proportional_gain
            return max(MIN_PWM_DUTY_CYCLE, min(MAX_PWM_DUTY_CYCLE, fallback_output))

    def reset(self) -> None:
        """Reset fuzzy controller state"""
        super().reset()
        # Reset fuzzy system simulation state
        if hasattr(self, 'controller'):
            self.controller = ctrl.ControlSystemSimulation(self.control_system)
