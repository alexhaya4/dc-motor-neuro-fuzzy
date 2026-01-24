"""
Test cases for neural network models module
"""

import pytest
import json
import os
from pathlib import Path
from nn_models import (
    compute_file_checksum,
    verify_file_checksum,
    save_checksum,
    load_checksum,
    NeuralNetworkTrainer,
    TRAINING_DATA_SCHEMA
)
from jsonschema import validate, ValidationError


class TestChecksumFunctions:
    """Test checksum computation and verification"""

    def test_compute_checksum(self, tmp_path):
        """Test checksum computation"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        checksum = compute_file_checksum(str(test_file))
        assert isinstance(checksum, str)
        assert len(checksum) == 64  # SHA256 produces 64 hex characters

    def test_consistent_checksum(self, tmp_path):
        """Test that same file produces same checksum"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        checksum1 = compute_file_checksum(str(test_file))
        checksum2 = compute_file_checksum(str(test_file))

        assert checksum1 == checksum2

    def test_different_content_different_checksum(self, tmp_path):
        """Test that different content produces different checksum"""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        file1.write_text("Content 1")
        file2.write_text("Content 2")

        checksum1 = compute_file_checksum(str(file1))
        checksum2 = compute_file_checksum(str(file2))

        assert checksum1 != checksum2

    def test_verify_checksum_valid(self, tmp_path):
        """Test verification of valid checksum"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        checksum = compute_file_checksum(str(test_file))
        assert verify_file_checksum(str(test_file), checksum) is True

    def test_verify_checksum_invalid(self, tmp_path):
        """Test verification of invalid checksum"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        fake_checksum = "0" * 64
        assert verify_file_checksum(str(test_file), fake_checksum) is False

    def test_save_and_load_checksum(self, tmp_path):
        """Test saving and loading checksum to file"""
        test_file = tmp_path / "model.h5"
        test_file.write_text("Fake model data")

        checksum = compute_file_checksum(str(test_file))
        save_checksum(str(test_file), checksum)

        loaded_checksum = load_checksum(str(test_file))
        assert loaded_checksum == checksum

    def test_load_nonexistent_checksum(self, tmp_path):
        """Test loading checksum when file doesn't exist"""
        test_file = tmp_path / "nonexistent.h5"

        loaded_checksum = load_checksum(str(test_file))
        assert loaded_checksum is None


class TestTrainingDataValidation:
    """Test JSON training data validation"""

    def test_valid_training_data(self):
        """Test that valid training data passes validation"""
        valid_data = [
            {
                "target_speed": 50.0,
                "actual_speed": 48.5,
                "error_scale": 1.2,
                "delta_error_scale": 0.8,
                "output_scale": 1.0
            },
            {
                "target_speed": 75.0,
                "actual_speed": 74.2,
                "error_scale": 1.5,
                "delta_error_scale": 1.1,
                "output_scale": 0.9
            }
        ]

        # Should not raise exception
        validate(instance=valid_data, schema=TRAINING_DATA_SCHEMA)

    def test_invalid_missing_field(self):
        """Test that missing required field fails validation"""
        invalid_data = [
            {
                "target_speed": 50.0,
                "actual_speed": 48.5,
                # Missing error_scale
                "delta_error_scale": 0.8,
                "output_scale": 1.0
            }
        ]

        with pytest.raises(ValidationError):
            validate(instance=invalid_data, schema=TRAINING_DATA_SCHEMA)

    def test_invalid_out_of_range(self):
        """Test that out-of-range values fail validation"""
        invalid_data = [
            {
                "target_speed": 150.0,  # Out of range (max 100)
                "actual_speed": 48.5,
                "error_scale": 1.2,
                "delta_error_scale": 0.8,
                "output_scale": 1.0
            }
        ]

        with pytest.raises(ValidationError):
            validate(instance=invalid_data, schema=TRAINING_DATA_SCHEMA)

    def test_invalid_wrong_type(self):
        """Test that wrong data type fails validation"""
        invalid_data = [
            {
                "target_speed": "fifty",  # Should be number
                "actual_speed": 48.5,
                "error_scale": 1.2,
                "delta_error_scale": 0.8,
                "output_scale": 1.0
            }
        ]

        with pytest.raises(ValidationError):
            validate(instance=invalid_data, schema=TRAINING_DATA_SCHEMA)

    def test_invalid_extra_fields(self):
        """Test that extra fields fail validation"""
        invalid_data = [
            {
                "target_speed": 50.0,
                "actual_speed": 48.5,
                "error_scale": 1.2,
                "delta_error_scale": 0.8,
                "output_scale": 1.0,
                "extra_field": "not allowed"  # Extra field
            }
        ]

        with pytest.raises(ValidationError):
            validate(instance=invalid_data, schema=TRAINING_DATA_SCHEMA)


class TestNeuralNetworkTrainer:
    """Test neural network trainer"""

    def test_load_training_data_file_not_found(self):
        """Test loading training data when file doesn't exist"""
        trainer = NeuralNetworkTrainer()
        data = trainer.load_training_data("nonexistent.json")
        assert data is None

    def test_load_training_data_valid(self, tmp_path):
        """Test loading valid training data"""
        valid_data = [
            {
                "target_speed": 50.0,
                "actual_speed": 48.5,
                "error_scale": 1.2,
                "delta_error_scale": 0.8,
                "output_scale": 1.0
            }
        ]

        data_file = tmp_path / "training_data.json"
        with open(data_file, 'w') as f:
            json.dump(valid_data, f)

        trainer = NeuralNetworkTrainer()
        loaded_data = trainer.load_training_data(str(data_file))

        assert loaded_data == valid_data

    def test_load_training_data_invalid_json(self, tmp_path):
        """Test loading invalid JSON"""
        data_file = tmp_path / "bad.json"
        data_file.write_text("{invalid json")

        trainer = NeuralNetworkTrainer()
        data = trainer.load_training_data(str(data_file))
        assert data is None

    def test_load_training_data_fails_schema(self, tmp_path):
        """Test loading data that fails schema validation"""
        invalid_data = [
            {
                "target_speed": "not a number",  # Invalid type
                "actual_speed": 48.5,
                "error_scale": 1.2,
                "delta_error_scale": 0.8,
                "output_scale": 1.0
            }
        ]

        data_file = tmp_path / "invalid_schema.json"
        with open(data_file, 'w') as f:
            json.dump(invalid_data, f)

        trainer = NeuralNetworkTrainer()
        data = trainer.load_training_data(str(data_file))
        assert data is None

    def test_load_training_data_too_large(self, tmp_path):
        """Test that very large files are rejected"""
        from constants import MAX_JSON_FILE_SIZE_BYTES

        # Create a file larger than max size
        data_file = tmp_path / "huge.json"
        with open(data_file, 'wb') as f:
            f.write(b'0' * (MAX_JSON_FILE_SIZE_BYTES + 1))

        trainer = NeuralNetworkTrainer()
        data = trainer.load_training_data(str(data_file))
        assert data is None
