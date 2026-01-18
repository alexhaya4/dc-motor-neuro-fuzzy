"""
ANFIS (Adaptive Neuro-Fuzzy Inference System) Controller
Uses REAL trained neural networks to adapt fuzzy scaling factors
"""

from typing import Optional, Dict
from pathlib import Path
import numpy as np

from base_controller import FuzzyControllerBase
from logger_utils import get_logger, log_exception
from config import get_config

# Import TensorFlow/Keras conditionally
try:
    from tensorflow import keras
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False


class ANFISController(FuzzyControllerBase):
    """
    Adaptive Neuro-Fuzzy Inference System (ANFIS) Controller

    This controller combines:
    1. Fuzzy logic inference system (base layer)
    2. Neural networks for adaptive parameter tuning (adaptation layer)

    The neural networks learn optimal scaling factors for:
    - Error scaling
    - Delta error scaling
    - Output scaling

    Unlike the false "neural networks" in the old code, these are ACTUAL
    trained neural networks loaded from model files.
    """

    def __init__(
        self,
        models_dir: Optional[Path] = None,
        use_neural_networks: bool = True
    ):
        """
        Initialize ANFIS controller

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

        # Attempt to load neural networks if requested
        if use_neural_networks:
            if not TENSORFLOW_AVAILABLE:
                self.logger.warning("TensorFlow not available, using fuzzy-only mode")
            else:
                self._load_neural_networks()

        mode = "ANFIS (neural-fuzzy)" if self.using_neural_networks else "Fuzzy-only"
        self.logger.info(f"ANFIS Controller initialized in {mode} mode")

    def _load_neural_networks(self) -> None:
        """Load trained neural network models from disk"""
        try:
            error_model_path = self.models_dir / "error_scale_network.keras"
            delta_error_model_path = self.models_dir / "delta_error_scale_network.keras"
            output_model_path = self.models_dir / "output_scale_network.keras"

            # Check if model files exist
            if not error_model_path.exists():
                self.logger.warning(f"Error scale model not found: {error_model_path}")
                return

            if not delta_error_model_path.exists():
                self.logger.warning(f"Delta error scale model not found: {delta_error_model_path}")
                return

            if not output_model_path.exists():
                self.logger.warning(f"Output scale model not found: {output_model_path}")
                return

            # Load models
            self.logger.info("Loading neural network models...")

            self.error_network = keras.models.load_model(str(error_model_path))
            self.delta_error_network = keras.models.load_model(str(delta_error_model_path))
            self.output_network = keras.models.load_model(str(output_model_path))

            self.using_neural_networks = True
            self.logger.info("Neural network models loaded successfully")

        except Exception as e:
            log_exception(self.logger, "Failed to load neural network models", e)
            self.using_neural_networks = False
            self.logger.warning("Falling back to fuzzy-only mode")

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
            # Prepare input data (normalized to 0-1 range)
            input_data = np.array([[target_speed / 100.0, current_speed / 100.0]], dtype=np.float32)

            # Predict scaling factors using neural networks
            self.error_scale = float(self.error_network.predict(input_data, verbose=0)[0][0])
            self.delta_error_scale = float(self.delta_error_network.predict(input_data, verbose=0)[0][0])
            self.output_scale = float(self.output_network.predict(input_data, verbose=0)[0][0])

            # Clamp scaling factors to reasonable ranges
            self.error_scale = max(0.1, min(2.0, self.error_scale))
            self.delta_error_scale = max(0.1, min(2.0, self.delta_error_scale))
            self.output_scale = max(0.5, min(1.5, self.output_scale))

        except Exception as e:
            log_exception(self.logger, "Error computing scaling factors", e)
            # Use default scaling on error
            self.error_scale = 1.0
            self.delta_error_scale = 1.0
            self.output_scale = 1.0

    def _compute_control_output(self, target_speed: float, current_speed: float) -> float:
        """
        Compute ANFIS control output

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
            log_exception(self.logger, "ANFIS computation failed", e)
            # Fallback to proportional control
            return 50 + error * 0.5

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
        """Reset ANFIS controller state"""
        super().reset()
        self.error_scale = 1.0
        self.delta_error_scale = 1.0
        self.output_scale = 1.0
