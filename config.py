"""
Configuration management for DC Motor Control System
Centralized configuration with environment variable support
"""

import os
import logging
import math
from dataclasses import dataclass, field
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv
from constants import VALID_GPIO_PINS

# Load environment variables from .env file if it exists
load_dotenv()


class ConfigurationError(Exception):
    """Raised when configuration validation fails"""
    pass


def env_number(cast, name, default):
    try:
        return cast(os.getenv(name, default))
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(f'{name} must be a valid {cast.__name__}') from exc


def validate_gpio_pin(pin: int, pin_name: str) -> int:
    """
    Validate GPIO pin number is within valid BCM range

    Args:
        pin: GPIO pin number to validate
        pin_name: Name of the pin for error messages

    Returns:
        Validated pin number

    Raises:
        ConfigurationError: If pin is invalid
    """
    if isinstance(pin, bool) or not isinstance(pin, int) or pin not in VALID_GPIO_PINS:
        raise ConfigurationError(
            f"Invalid GPIO pin for {pin_name}: {pin}. "
            f"Valid BCM pins are {VALID_GPIO_PINS[0]}-{VALID_GPIO_PINS[-1]}"
        )
    return pin


def validate_directory_path(path: Path, base_path: Path, path_name: str) -> Path:
    """
    Validate directory path is within allowed boundaries (prevent directory traversal)

    Args:
        path: Path to validate
        base_path: Base directory that path must be under
        path_name: Name of the path for error messages

    Returns:
        Validated absolute path

    Raises:
        ConfigurationError: If path is outside allowed directory
    """
    try:
        real_path = Path(path).resolve()
        real_base = base_path.resolve()

        # Check if path is under base_path
        try:
            real_path.relative_to(real_base)
        except ValueError:
            raise ConfigurationError(
                f"{path_name} '{path}' is outside allowed directory '{base_path}'"
            )

        return real_path
    except Exception as e:
        raise ConfigurationError(f"Invalid path for {path_name}: {e}")


@dataclass
class GPIOConfig:
    """GPIO pin configuration for Raspberry Pi"""
    motor_in1: int = 17
    motor_in2: int = 18
    motor_ena: int = 12
    ir_sensor_pin: int = 23
    ir_sensor_pin_2: int = 24  # Optional second sensor

    def __post_init__(self):
        pins = vars(self)
        for name, pin in pins.items():
            validate_gpio_pin(pin, name)
        if len(set(pins.values())) != len(pins):
            raise ConfigurationError('GPIO pins must be distinct')

    @classmethod
    def from_env(cls) -> 'GPIOConfig':
        """Load GPIO configuration from environment variables with validation"""
        motor_in1 = validate_gpio_pin(env_number(int, 'GPIO_MOTOR_IN1', 17), 'MOTOR_IN1')
        motor_in2 = validate_gpio_pin(env_number(int, 'GPIO_MOTOR_IN2', 18), 'MOTOR_IN2')
        motor_ena = validate_gpio_pin(env_number(int, 'GPIO_MOTOR_ENA', 12), 'MOTOR_ENA')
        ir_sensor = validate_gpio_pin(env_number(int, 'GPIO_IR_SENSOR', 23), 'IR_SENSOR')
        ir_sensor_2 = validate_gpio_pin(env_number(int, 'GPIO_IR_SENSOR_2', 24), 'IR_SENSOR_2')

        return cls(
            motor_in1=motor_in1,
            motor_in2=motor_in2,
            motor_ena=motor_ena,
            ir_sensor_pin=ir_sensor,
            ir_sensor_pin_2=ir_sensor_2
        )


@dataclass
class MotorConfig:
    """Motor hardware configuration"""
    max_rpm: int = 100
    pulses_per_revolution: int = 1
    pwm_frequency: int = 1000
    min_pulse_width_ms: float = 1.0

    def __post_init__(self):
        for name in ('max_rpm', 'pulses_per_revolution', 'pwm_frequency'):
            value = getattr(self, name)
            if isinstance(value, bool) or not math.isfinite(value) or value <= 0:
                raise ConfigurationError(f'{name} must be finite and positive')
        for name in ('pulses_per_revolution', 'pwm_frequency'):
            if not isinstance(getattr(self, name), int):
                raise ConfigurationError(f'{name} must be an integer')
        if not math.isfinite(self.min_pulse_width_ms) or self.min_pulse_width_ms < 0:
            raise ConfigurationError('min_pulse_width_ms must be finite and nonnegative')

    @classmethod
    def from_env(cls) -> 'MotorConfig':
        """Load motor configuration from environment variables"""
        return cls(
            max_rpm=env_number(int, 'MOTOR_MAX_RPM', 100),
            pulses_per_revolution=env_number(int, 'MOTOR_PULSES_PER_REV', 1),
            pwm_frequency=env_number(int, 'MOTOR_PWM_FREQ', 1000),
            min_pulse_width_ms=env_number(float, 'MOTOR_MIN_PULSE_WIDTH', 1.0)
        )


@dataclass
class ControllerConfig:
    """Controller parameters configuration"""
    # PI Controller defaults
    pi_kp: float = 0.5
    pi_ki: float = 0.1
    pi_integral_limit: float = 100.0

    # PID Controller defaults
    pid_kp: float = 0.6
    pid_ki: float = 0.15
    pid_kd: float = 0.05
    pid_integral_limit: float = 100.0

    # Fuzzy Controller defaults
    fuzzy_universe_min: float = -100.0
    fuzzy_universe_max: float = 100.0

    # Neural Network defaults
    nn_hidden_layers: list = field(default_factory=lambda: [16, 8])
    nn_dropout_rate: float = 0.2
    nn_learning_rate: float = 0.001
    nn_batch_size: int = 32
    nn_epochs: int = 100

    def __post_init__(self):
        for name in ('pi_kp', 'pi_ki', 'pid_kp', 'pid_ki', 'pid_kd', 'pi_integral_limit', 'pid_integral_limit'):
            value = getattr(self, name)
            if not math.isfinite(value) or value < 0 or ('limit' in name and value == 0):
                raise ConfigurationError(f'{name} must be finite and nonnegative; integral limits must be positive')

    @classmethod
    def from_env(cls) -> 'ControllerConfig':
        """Load controller configuration from environment variables"""
        return cls(
            pi_kp=env_number(float, 'CONTROLLER_PI_KP', 0.5),
            pi_ki=env_number(float, 'CONTROLLER_PI_KI', 0.1),
            pid_kp=env_number(float, 'CONTROLLER_PID_KP', 0.6),
            pid_ki=env_number(float, 'CONTROLLER_PID_KI', 0.15),
            pid_kd=env_number(float, 'CONTROLLER_PID_KD', 0.05)
        )


@dataclass
class PathConfig:
    """File paths configuration"""
    base_dir: Path = field(default_factory=lambda: Path(__file__).parent)
    models_dir: Path = field(default_factory=lambda: Path(__file__).parent / "models")
    logs_dir: Path = field(default_factory=lambda: Path(__file__).parent / "logs")
    data_dir: Path = field(default_factory=lambda: Path(__file__).parent / "data")

    def __post_init__(self):
        """Create directories if they don't exist"""
        self.base_dir = Path(self.base_dir).resolve()
        for name in ('models_dir', 'logs_dir', 'data_dir'):
            setattr(self, name, validate_directory_path(Path(getattr(self, name)), self.base_dir, name))
        for name in ('models_dir', 'logs_dir', 'data_dir'):
            getattr(self, name).mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls) -> 'PathConfig':
        """Load path configuration from environment variables with validation"""
        default_base = Path(__file__).parent
        base_env = os.getenv('APP_BASE_DIR', str(default_base))

        # Validate base directory
        base = validate_directory_path(Path(base_env), default_base.parent, 'APP_BASE_DIR')

        # Validate subdirectories
        models_env = os.getenv('APP_MODELS_DIR', str(base / "models"))
        logs_env = os.getenv('APP_LOGS_DIR', str(base / "logs"))
        data_env = os.getenv('APP_DATA_DIR', str(base / "data"))

        models = validate_directory_path(Path(models_env), base, 'APP_MODELS_DIR')
        logs = validate_directory_path(Path(logs_env), base, 'APP_LOGS_DIR')
        data = validate_directory_path(Path(data_env), base, 'APP_DATA_DIR')

        return cls(
            base_dir=base,
            models_dir=models,
            logs_dir=logs,
            data_dir=data
        )


@dataclass
class GUIConfig:
    """GUI appearance and behavior configuration"""
    window_width: int = 1200
    window_height: int = 800
    plot_update_interval_ms: int = 100
    max_time_window_sec: int = 30
    theme: str = "modern"  # "modern", "classic", "dark"
    enable_animations: bool = True

    def __post_init__(self):
        for name in ('window_width', 'window_height', 'plot_update_interval_ms', 'max_time_window_sec'):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ConfigurationError(f'{name} must be a positive integer')

    @classmethod
    def from_env(cls) -> 'GUIConfig':
        """Load GUI configuration from environment variables"""
        return cls(
            window_width=env_number(int, 'GUI_WINDOW_WIDTH', 1200),
            window_height=env_number(int, 'GUI_WINDOW_HEIGHT', 800),
            plot_update_interval_ms=env_number(int, 'GUI_PLOT_UPDATE_MS', 100),
            theme=os.getenv('GUI_THEME', 'modern')
        )


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_enabled: bool = True
    console_enabled: bool = True
    max_file_size_mb: int = 10
    backup_count: int = 5

    @classmethod
    def from_env(cls) -> 'LoggingConfig':
        """Load logging configuration from environment variables"""
        return cls(
            level=os.getenv('LOG_LEVEL', 'INFO'),
            file_enabled=os.getenv('LOG_FILE_ENABLED', 'true').lower() == 'true',
            console_enabled=os.getenv('LOG_CONSOLE_ENABLED', 'true').lower() == 'true'
        )


class AppConfig:
    """Main application configuration"""

    def __init__(self, load_from_env: bool = True):
        """
        Initialize application configuration

        Args:
            load_from_env: If True, load configuration from environment variables
        """
        if load_from_env:
            self.gpio = GPIOConfig.from_env()
            self.motor = MotorConfig.from_env()
            self.controller = ControllerConfig.from_env()
            self.paths = PathConfig.from_env()
            self.gui = GUIConfig.from_env()
            self.logging = LoggingConfig.from_env()
        else:
            self.gpio = GPIOConfig()
            self.motor = MotorConfig()
            self.controller = ControllerConfig()
            self.paths = PathConfig()
            self.gui = GUIConfig()
            self.logging = LoggingConfig()

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'gpio': self.gpio.__dict__,
            'motor': self.motor.__dict__,
            'controller': self.controller.__dict__,
            'paths': {k: str(v) for k, v in self.paths.__dict__.items()},
            'gui': self.gui.__dict__,
            'logging': self.logging.__dict__
        }

    def setup_logging(self) -> None:
        """Setup logging based on configuration"""
        log_level = getattr(logging, self.logging.level.upper())

        # Create formatters
        formatter = logging.Formatter(self.logging.format)

        # Get root logger
        logger = logging.getLogger()
        logger.setLevel(log_level)

        # Remove existing handlers
        logger.handlers.clear()

        # Console handler
        if self.logging.console_enabled:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(log_level)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        # File handler
        if self.logging.file_enabled:
            from logging.handlers import RotatingFileHandler
            log_file = self.paths.logs_dir / "motor_control.log"
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=self.logging.max_file_size_mb * 1024 * 1024,
                backupCount=self.logging.backup_count
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)


# Global configuration instance
config = AppConfig()


def get_config() -> AppConfig:
    """Get the global configuration instance"""
    return config


def is_raspberry_pi() -> bool:
    """Check if running on Raspberry Pi"""
    for filename in ('/proc/device-tree/model', '/sys/firmware/devicetree/base/model', '/proc/cpuinfo'):
        try:
            if 'Raspberry Pi' in Path(filename).read_text(errors='replace'):
                return True
        except OSError:
            continue
    return False
