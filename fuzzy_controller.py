"""
Pure Fuzzy Logic Controller using the base class
Eliminates code duplication and adds proper error handling
"""

from base_controller import FuzzyControllerBase


class FuzzyController(FuzzyControllerBase):
    """
    Pure Mamdani-style Fuzzy Logic Controller for DC motor speed control

    This controller uses fuzzy inference to compute PWM output based on:
    - Error: target_speed - current_speed
    - Delta error: change in error over time

    The fuzzy system uses:
    - 5 input fuzzy sets (NB, NS, ZE, PS, PB)
    - 5 output fuzzy sets (VL, LO, ME, HI, VH)
    - 12+ fuzzy rules based on control theory
    """

    def __init__(self):
        """Initialize the fuzzy controller with base class configuration"""
        super().__init__()
        self.logger.info("Pure Fuzzy Controller initialized")
