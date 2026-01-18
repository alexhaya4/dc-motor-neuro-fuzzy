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
        if not (0 <= target_speed <= 100):
            self.logger.warning(f"target_speed {target_speed} out of range, clamping to 0-100")
            target_speed = max(0, min(100, target_speed))

        if not (0 <= current_speed <= 100):
            self.logger.warning(f"current_speed {current_speed} out of range, clamping to 0-100")
            current_speed = max(0, min(100, current_speed))

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
            output = max(0, min(100, output))

            return output

        except ControllerValidationError as e:
            log_exception(self.logger, "Controller validation error", e)
            return 0.0
        except Exception as e:
            log_exception(self.logger, "Unexpected error in controller computation", e)
            return 0.0

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
            # Get configuration
            universe_min = self.config.controller.fuzzy_universe_min
            universe_max = self.config.controller.fuzzy_universe_max

            # Create fuzzy variables
            self.error = ctrl.Antecedent(
                np.arange(universe_min, universe_max + 1, 1), 'error'
            )
            self.delta_error = ctrl.Antecedent(
                np.arange(universe_min, universe_max + 1, 1), 'delta_error'
            )
            self.pwm_output = ctrl.Consequent(np.arange(0, 101, 1), 'pwm_output')

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
        error = max(min(error, 100), -100)
        delta_error = max(min(delta_error, 100), -100)

        try:
            # Set fuzzy inputs
            self.controller.input['error'] = error
            self.controller.input['delta_error'] = delta_error

            # Compute fuzzy output
            self.controller.compute()
            pwm = self.controller.output['pwm_output']

            return pwm

        except Exception as e:
            log_exception(self.logger, "Fuzzy computation failed", e)
            # Return proportional control as fallback
            return 50 + error * 0.5

    def reset(self) -> None:
        """Reset fuzzy controller state"""
        super().reset()
        # Reset fuzzy system simulation state
        if hasattr(self, 'controller'):
            self.controller = ctrl.ControlSystemSimulation(self.control_system)
