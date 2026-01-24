"""
Test cases for configuration module
"""

import pytest
import os
from pathlib import Path
from config import (
    GPIOConfig,
    PathConfig,
    ConfigurationError,
    validate_gpio_pin,
    validate_directory_path
)


class TestGPIOValidation:
    """Test GPIO pin validation"""

    def test_valid_gpio_pin(self):
        """Test that valid GPIO pins are accepted"""
        assert validate_gpio_pin(17, "TEST_PIN") == 17
        assert validate_gpio_pin(2, "TEST_PIN") == 2
        assert validate_gpio_pin(27, "TEST_PIN") == 27

    def test_invalid_gpio_pin_too_low(self):
        """Test that GPIO pin 0 is rejected"""
        with pytest.raises(ConfigurationError, match="Invalid GPIO pin"):
            validate_gpio_pin(0, "TEST_PIN")

    def test_invalid_gpio_pin_too_high(self):
        """Test that GPIO pin 30 is rejected"""
        with pytest.raises(ConfigurationError, match="Invalid GPIO pin"):
            validate_gpio_pin(30, "TEST_PIN")

    def test_invalid_gpio_pin_negative(self):
        """Test that negative GPIO pins are rejected"""
        with pytest.raises(ConfigurationError, match="Invalid GPIO pin"):
            validate_gpio_pin(-1, "TEST_PIN")


class TestPathValidation:
    """Test path validation"""

    def test_valid_subdirectory_path(self, tmp_path):
        """Test that subdirectory paths are accepted"""
        base = tmp_path / "project"
        base.mkdir()
        sub = base / "models"
        sub.mkdir()

        validated = validate_directory_path(sub, base, "MODELS_DIR")
        assert validated == sub.resolve()

    def test_invalid_parent_directory_traversal(self, tmp_path):
        """Test that parent directory traversal is rejected"""
        base = tmp_path / "project"
        base.mkdir()
        parent = tmp_path / "outside"
        parent.mkdir()

        with pytest.raises(ConfigurationError, match="outside allowed directory"):
            validate_directory_path(parent, base, "MALICIOUS_DIR")

    def test_invalid_symlink_escape(self, tmp_path):
        """Test that symlinks escaping base directory are rejected"""
        base = tmp_path / "project"
        base.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()

        # Create symlink inside base pointing outside
        link = base / "escape"
        link.symlink_to(outside)

        with pytest.raises(ConfigurationError, match="outside allowed directory"):
            validate_directory_path(link, base, "SYMLINK_DIR")


class TestGPIOConfig:
    """Test GPIO configuration"""

    def test_default_gpio_config(self):
        """Test default GPIO configuration"""
        config = GPIOConfig()
        assert config.motor_in1 == 17
        assert config.motor_in2 == 18
        assert config.motor_ena == 12
        assert config.ir_sensor_pin == 23

    def test_gpio_config_from_env_valid(self, monkeypatch):
        """Test loading valid GPIO config from environment"""
        monkeypatch.setenv('GPIO_MOTOR_IN1', '22')
        monkeypatch.setenv('GPIO_MOTOR_IN2', '23')
        monkeypatch.setenv('GPIO_MOTOR_ENA', '24')
        monkeypatch.setenv('GPIO_IR_SENSOR', '25')
        monkeypatch.setenv('GPIO_IR_SENSOR_2', '26')

        config = GPIOConfig.from_env()
        assert config.motor_in1 == 22
        assert config.motor_in2 == 23
        assert config.motor_ena == 24
        assert config.ir_sensor_pin == 25
        assert config.ir_sensor_pin_2 == 26

    def test_gpio_config_from_env_invalid(self, monkeypatch):
        """Test that invalid GPIO pins from environment are rejected"""
        monkeypatch.setenv('GPIO_MOTOR_IN1', '50')  # Invalid pin

        with pytest.raises(ConfigurationError, match="Invalid GPIO pin"):
            GPIOConfig.from_env()


class TestPathConfig:
    """Test path configuration"""

    def test_path_config_creates_directories(self, tmp_path):
        """Test that PathConfig creates directories"""
        base = tmp_path / "project"
        base.mkdir()

        # Temporarily change working directory
        original_file = Path(__file__)
        config_file = base / "config.py"
        config_file.touch()

        config = PathConfig(
            base_dir=base,
            models_dir=base / "models",
            logs_dir=base / "logs",
            data_dir=base / "data"
        )

        assert (base / "models").exists()
        assert (base / "logs").exists()
        assert (base / "data").exists()

    def test_path_config_rejects_traversal(self, tmp_path, monkeypatch):
        """Test that PathConfig rejects directory traversal attempts"""
        base = tmp_path / "project"
        base.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()

        # Try to set base dir outside project
        monkeypatch.setenv('APP_BASE_DIR', str(outside))

        # This should raise an error when validated
        with pytest.raises(ConfigurationError):
            PathConfig.from_env()
