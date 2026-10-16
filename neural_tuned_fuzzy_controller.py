"""
Neural-Tuned Mamdani Fuzzy Controller
Uses trained neural networks to predict scaling factors for a Mamdani fuzzy controller's inputs and output.
"""

from typing import Optional, Dict
from pathlib import Path
from importlib import import_module
import numpy as np

from base_controller import FuzzyControllerBase
from logger_utils import log_exception
from config import get_config

# Import TensorFlow/Keras conditionally
try:
    import_module('tensorflow.keras')
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False


class NeuralTunedFuzzyController(FuzzyControllerBase):
    """
    Neural-Tuned Mamdani Fuzzy Controller

    This controller combines:
    1. Mamdani fuzzy inference system (base layer)
    2. Neural networks for adaptive parameter tuning (adaptation layer)

    The neural networks learn the supplied scaling-factor labels for:
    - Error scaling
    - Delta error scaling
    - Output scaling

    Trained networks are loaded only as a complete, checksum-verified set.
    """

    def __init__(
        self,
        models_dir: Optional[Path] = None,
        use_neural_networks: bool = True,
        models_to_use: Optional[Dict[str, bool]] = None
    ):
        """
        Initialize Neural-Tuned Fuzzy Controller

        Args:
            models_dir: Directory containing trained neural network models
            use_neural_networks: If False, use fuzzy logic only (fallback mode)
        """
        super().__init__()

        self.config = get_config()
        self.models_dir = models_dir if models_dir else self.config.paths.models_dir

        # Scaling factors (adaptive parameters)
        self.error_scale = 1.0
        self.delta_error_scale = 1.0
        self.output_scale = 1.0

        # Neural network models
        self.error_network = None
        self.delta_error_network = None
        self.output_network = None

        # Flag indicating if neural networks are loaded
        self.using_neural_networks = False

        self.models_used = dict.fromkeys(('error_scale', 'delta_error_scale', 'output_scale'), True)
        if models_to_use is not None:
            if any(k not in self.models_used or not isinstance(v, bool) for k, v in models_to_use.items()):
                raise ValueError('Model selection must map known scaling names to booleans')
            self.models_used.update(models_to_use)

        # Attempt to load neural networks if requested
        if use_neural_networks:
            if not TENSORFLOW_AVAILABLE:
                self.logger.warning("TensorFlow not available, using fuzzy-only mode")
            else:
                self._load_neural_networks()

        mode = "Neural-Tuned Fuzzy (neural-fuzzy)" if self.using_neural_networks else "Fuzzy-only"
        self.logger.info(f"Neural-Tuned Fuzzy Controller initialized in {mode} mode")

    def _load_neural_networks(self) -> None:
        from nn_models import ScalingFactorNetwork
        networks = {name: ScalingFactorNetwork(name=name) for name, enabled in self.models_used.items() if enabled}
        if not networks:
            return
        if not all(network.load(self.models_dir) for network in networks.values()):
            self.logger.warning('A complete set of requested checksum-verified models was not found; using fuzzy-only mode')
            return
        self.error_network = networks.get('error_scale')
        self.delta_error_network = networks.get('delta_error_scale')
        self.output_network = networks.get('output_scale')
        self.using_neural_networks = True

    def _compute_scaling_factors(self, target_speed: float, current_speed: float) -> None:
        """
        Compute adaptive scaling factors using neural networks

        Args:
            target_speed: Target speed (0-100%)
            current_speed: Current speed (0-100%)
        """
        if not self.using_neural_networks:
            # Use fixed scaling in fallback mode
            self.error_scale = 1.0
            self.delta_error_scale = 1.0
            self.output_scale = 1.0
            return

        try:
            # Supply raw percentages; saved models contain input normalization.
            input_data = np.array([[target_speed, current_speed]], dtype=np.float32)

            # Predict scaling factors using neural networks
            self.error_scale = float(self.error_network.predict(input_data)[0][0]) if self.error_network is not None else 1.0
            self.delta_error_scale = float(self.delta_error_network.predict(input_data)[0][0]) if self.delta_error_network is not None else 1.0
            self.output_scale = float(self.output_network.predict(input_data)[0][0]) if self.output_network is not None else 1.0

            # Clamp scaling factors to reasonable ranges
            self.error_scale = max(0.5, min(2.0, self.error_scale))
            self.delta_error_scale = max(0.5, min(2.0, self.delta_error_scale))
            self.output_scale = max(0.5, min(1.5, self.output_scale))

        except Exception as e:
            log_exception(self.logger, "Error computing scaling factors", e)
            # Use default scaling on error
            self.error_scale = 1.0
            self.delta_error_scale = 1.0
            self.output_scale = 1.0

    def _compute_control_output(self, target_speed: float, current_speed: float) -> float:
        """
        Compute Neural-Tuned Fuzzy control output

        Args:
            target_speed: Validated target speed (0-100%)
            current_speed: Validated current speed (0-100%)

        Returns:
            PWM duty cycle (0-100%)
        """
        # Compute adaptive scaling factors using neural networks
        self._compute_scaling_factors(target_speed, current_speed)

        # Calculate error and delta error
        error = target_speed - current_speed
        delta_error = error - self.prev_error

        # Apply adaptive scaling to inputs
        scaled_error = error * self.error_scale
        scaled_delta_error = delta_error * self.delta_error_scale

        # Clamp scaled inputs to fuzzy universe
        scaled_error = max(min(scaled_error, 100), -100)
        scaled_delta_error = max(min(scaled_delta_error, 100), -100)

        try:
            # Compute fuzzy output with scaled inputs
            self.controller.input['error'] = scaled_error
            self.controller.input['delta_error'] = scaled_delta_error
            self.controller.compute()

            # Get fuzzy output
            pwm = self.controller.output['pwm_output']

            # Apply output scaling
            pwm = pwm * self.output_scale

            return pwm

        except Exception as e:
            log_exception(self.logger, "Neural-Tuned Fuzzy computation failed", e)
            return 0.0

    def get_scaling_factors(self) -> Dict[str, float]:
        """
        Get current scaling factors

        Returns:
            Dictionary with current scaling factors
        """
        return {
            'error_scale': self.error_scale,
            'delta_error_scale': self.delta_error_scale,
            'output_scale': self.output_scale,
            'using_neural_networks': self.using_neural_networks
        }

    def reset(self) -> None:
        """Reset Neural-Tuned Fuzzy Controller state"""
        super().reset()
        self.error_scale = 1.0
        self.delta_error_scale = 1.0
        self.output_scale = 1.0
