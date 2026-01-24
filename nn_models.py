import tensorflow as tf
import numpy as np
import os
import json
import hashlib
import matplotlib.pyplot as plt
from pathlib import Path
from jsonschema import validate, ValidationError as JsonValidationError
from constants import (
    NN_ERROR_SCALE_MIN, NN_ERROR_SCALE_MAX,
    NN_DELTA_ERROR_SCALE_MIN, NN_DELTA_ERROR_SCALE_MAX,
    NN_OUTPUT_SCALE_MIN, NN_OUTPUT_SCALE_MAX,
    MODEL_CHECKSUM_ALGORITHM, MAX_JSON_FILE_SIZE_BYTES
)


# JSON Schema for training data validation
TRAINING_DATA_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "target_speed": {"type": "number", "minimum": 0, "maximum": 100},
            "actual_speed": {"type": "number", "minimum": 0, "maximum": 100},
            "error_scale": {"type": "number", "minimum": 0.1, "maximum": 5.0},
            "delta_error_scale": {"type": "number", "minimum": 0.1, "maximum": 5.0},
            "output_scale": {"type": "number", "minimum": 0.1, "maximum": 5.0}
        },
        "required": ["target_speed", "actual_speed", "error_scale", "delta_error_scale", "output_scale"],
        "additionalProperties": False
    },
    "minItems": 1,
    "maxItems": 100000
}


def compute_file_checksum(filepath: str, algorithm: str = MODEL_CHECKSUM_ALGORITHM) -> str:
    """
    Compute cryptographic checksum of a file

    Args:
        filepath: Path to file
        algorithm: Hash algorithm (sha256, sha512, etc.)

    Returns:
        Hexadecimal checksum string
    """
    hash_obj = hashlib.new(algorithm)
    with open(filepath, 'rb') as f:
        # Read file in chunks to handle large files
        for chunk in iter(lambda: f.read(8192), b''):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def verify_file_checksum(filepath: str, expected_checksum: str,
                         algorithm: str = MODEL_CHECKSUM_ALGORITHM) -> bool:
    """
    Verify file checksum matches expected value

    Args:
        filepath: Path to file
        expected_checksum: Expected checksum value
        algorithm: Hash algorithm

    Returns:
        True if checksum matches, False otherwise
    """
    actual_checksum = compute_file_checksum(filepath, algorithm)
    return actual_checksum == expected_checksum


def save_checksum(filepath: str, checksum: str) -> None:
    """Save checksum to .checksum file"""
    checksum_file = f"{filepath}.{MODEL_CHECKSUM_ALGORITHM}"
    with open(checksum_file, 'w') as f:
        f.write(checksum)


def load_checksum(filepath: str) -> str:
    """Load checksum from .checksum file"""
    checksum_file = f"{filepath}.{MODEL_CHECKSUM_ALGORITHM}"
    if os.path.exists(checksum_file):
        with open(checksum_file, 'r') as f:
            return f.read().strip()
    return None

class ScalingFactorNetwork:
    """Neural network model for adaptive scaling factors."""
    
    def __init__(self, input_size=2, hidden_layers=[16, 8], output_size=1, name="scaling_network"):
        """Initialize the neural network model.
        
        Args:
            input_size: Number of input features (default: 2 for target_speed, actual_speed)
            hidden_layers: List of hidden layer sizes (default: [16, 8])
            output_size: Number of outputs (default: 1 for a single scaling factor)
            name: Name of the model for saving/loading
        """
        self.name = name
        self.model = self._build_model(input_size, hidden_layers, output_size)
        self.history = None
        
    def _build_model(self, input_size, hidden_layers, output_size):
        """Build the neural network model."""
        model = tf.keras.Sequential()
        
        # Input layer
        model.add(tf.keras.layers.Dense(hidden_layers[0], input_shape=(input_size,), activation='relu'))
        
        # Hidden layers
        for units in hidden_layers[1:]:
            model.add(tf.keras.layers.Dense(units, activation='relu'))
            model.add(tf.keras.layers.Dropout(0.2))  # Add dropout for regularization
            
        # Output layer - using sigmoid to ensure output is between 0 and 1
        # We'll scale this to get the final scaling factor
        model.add(tf.keras.layers.Dense(output_size, activation='sigmoid'))
        
        # Compile model
        model.compile(optimizer='adam', loss='mse', metrics=['mae'])
        
        return model
    
    def train(self, X, y, validation_split=0.2, epochs=100, batch_size=32, callback=None):
        """Train the model on provided data.
        
        Args:
            X: Input features
            y: Target values
            validation_split: Portion of data to use for validation
            epochs: Number of training epochs
            batch_size: Batch size for training
            callback: Optional callback function that receives progress updates
            
        Returns:
            Training history
        """
        # Create a custom callback to report progress
        class ProgressCallback(tf.keras.callbacks.Callback):
            def on_epoch_begin(self, epoch, logs=None):
                if callback:
                    # Report start of epoch
                    callback(self.model.name, epoch, epochs, None, "running")
            
            def on_epoch_end(self, epoch, logs=None):
                if callback:
                    # Report end of epoch with metrics
                    callback(self.model.name, epoch, epochs, logs, "running")
        
        # Set model name to be used in callback
        self.model.name = self.name
        
        # Train the model with our custom callback
        self.history = self.model.fit(
            X, y,
            validation_split=validation_split,
            epochs=epochs,
            batch_size=batch_size,
            verbose=1,
            callbacks=[ProgressCallback()]
        )
        
        if callback:
            # Report completion
            callback(self.name, epochs-1, epochs, None, "completed")
        
        return self.history
    
    def predict(self, X):
        """Make predictions with the model.
        
        Args:
            X: Input features
            
        Returns:
            Predicted values
        """
        # Ensure X is in the right shape
        if len(X.shape) == 1:
            X = X.reshape(1, -1)
        
        predictions = self.model.predict(X)
        
        # Scale the predictions to get the final scaling factor
        # For error_scale: range 0.5 to 2.0
        # For delta_error_scale: range 0.5 to 2.0
        # For output_scale: range 0.5 to 1.5
        
        if self.name == "error_scale":
            range_span = NN_ERROR_SCALE_MAX - NN_ERROR_SCALE_MIN
            return NN_ERROR_SCALE_MIN + (predictions * range_span)
        elif self.name == "delta_error_scale":
            range_span = NN_DELTA_ERROR_SCALE_MAX - NN_DELTA_ERROR_SCALE_MIN
            return NN_DELTA_ERROR_SCALE_MIN + (predictions * range_span)
        else:  # output_scale
            range_span = NN_OUTPUT_SCALE_MAX - NN_OUTPUT_SCALE_MIN
            return NN_OUTPUT_SCALE_MIN + (predictions * range_span)
    
    def save(self, directory="models"):
        """Save the model to disk with integrity checksum."""
        if not os.path.exists(directory):
            os.makedirs(directory)

        filepath = os.path.join(directory, f"{self.name}.h5")
        self.model.save(filepath)

        # Compute and save checksum for integrity verification
        checksum = compute_file_checksum(filepath)
        save_checksum(filepath, checksum)

        print(f"Model saved to {filepath}")
        print(f"Checksum ({MODEL_CHECKSUM_ALGORITHM}): {checksum}")
    
    def load(self, directory="models", verify_integrity=True):
        """
        Load the model from disk with optional integrity verification.

        Args:
            directory: Directory containing model file
            verify_integrity: Whether to verify file checksum (recommended)

        Returns:
            True if loaded successfully, False otherwise
        """
        filepath = os.path.join(directory, f"{self.name}.h5")

        if not os.path.exists(filepath):
            print(f"Model file {filepath} not found.")
            return False

        # Verify integrity if checksum file exists
        if verify_integrity:
            expected_checksum = load_checksum(filepath)
            if expected_checksum:
                print(f"Verifying model integrity...")
                if not verify_file_checksum(filepath, expected_checksum):
                    print(f"WARNING: Model file {filepath} failed integrity check!")
                    print(f"File may have been corrupted or tampered with.")
                    return False
                print(f"Integrity verification passed.")
            else:
                print(f"No checksum file found for {filepath}, skipping verification.")

        try:
            self.model = tf.keras.models.load_model(filepath)
            print(f"Model loaded from {filepath}")
            return True
        except (OSError, IOError, ValueError) as e:
            print(f"Error loading model from {filepath}: {e}")
            return False
    
    def plot_history(self):
        """Plot the training history to a file without showing it interactively."""
        if self.history is None:
            print("No training history available.")
            return
        
        # Use a non-interactive backend for plotting
        import matplotlib
        matplotlib.use('Agg')  # Force non-interactive backend
        import matplotlib.pyplot as plt
        
        plt.figure(figsize=(12, 4))
        
        # Plot loss
        plt.subplot(1, 2, 1)
        plt.plot(self.history.history['loss'], label='Training Loss')
        plt.plot(self.history.history['val_loss'], label='Validation Loss')
        plt.title(f'{self.name} - Loss')
        plt.xlabel('Epochs')
        plt.ylabel('Loss')
        plt.legend()
        
        # Plot mean absolute error
        plt.subplot(1, 2, 2)
        plt.plot(self.history.history['mae'], label='Training MAE')
        plt.plot(self.history.history['val_mae'], label='Validation MAE')
        plt.title(f'{self.name} - Mean Absolute Error')
        plt.xlabel('Epochs')
        plt.ylabel('MAE')
        plt.legend()
        
        plt.tight_layout()
        
        # Save to file instead of showing interactively
        plt.savefig(f"{self.name}_history.png")
        plt.close()  # Important: close the figure to release resources


class NeuralNetworkTrainer:
    """Class for training and managing the neural network models."""
    
    def __init__(self):
        self.error_network = ScalingFactorNetwork(name="error_scale")
        self.delta_error_network = ScalingFactorNetwork(name="delta_error_scale")
        self.output_network = ScalingFactorNetwork(name="output_scale")
        
    def load_training_data(self, filename="training_data.json"):
        """
        Load training data from a file with validation.

        Args:
            filename: Path to JSON training data file

        Returns:
            Validated training data or None if validation fails
        """
        if not os.path.exists(filename):
            print(f"Training data file {filename} not found.")
            return None

        # Check file size to prevent memory exhaustion
        file_size = os.path.getsize(filename)
        if file_size > MAX_JSON_FILE_SIZE_BYTES:
            print(f"Training data file {filename} is too large "
                  f"({file_size} bytes > {MAX_JSON_FILE_SIZE_BYTES} bytes).")
            return None

        try:
            with open(filename, 'r') as f:
                data = json.load(f)

            # Validate JSON structure
            validate(instance=data, schema=TRAINING_DATA_SCHEMA)

            print(f"Loaded and validated {len(data)} training samples.")
            return data

        except json.JSONDecodeError as e:
            print(f"Invalid JSON in {filename}: {e}")
            return None
        except JsonValidationError as e:
            print(f"Training data validation failed: {e.message}")
            return None
        except (OSError, IOError) as e:
            print(f"Error reading {filename}: {e}")
            return None
    
    def prepare_data(self, data):
        """Prepare the data for training the neural networks."""
        # Extract features and targets
        X = np.array([[d['target_speed'], d['actual_speed']] for d in data])
        y_error = np.array([d['error_scale'] for d in data])
        y_delta = np.array([d['delta_error_scale'] for d in data])
        y_output = np.array([d['output_scale'] for d in data])
        
        # Normalize targets to [0, 1] range for sigmoid output
        y_error = (y_error - NN_ERROR_SCALE_MIN) / (NN_ERROR_SCALE_MAX - NN_ERROR_SCALE_MIN)
        y_delta = (y_delta - NN_DELTA_ERROR_SCALE_MIN) / (NN_DELTA_ERROR_SCALE_MAX - NN_DELTA_ERROR_SCALE_MIN)
        y_output = (y_output - NN_OUTPUT_SCALE_MIN) / (NN_OUTPUT_SCALE_MAX - NN_OUTPUT_SCALE_MIN)
        
        return X, y_error, y_delta, y_output
    
    def train_networks(self, epochs=100, batch_size=32, callback=None):
        """Train all three networks.
        
        Args:
            epochs: Number of training epochs
            batch_size: Batch size for training
            callback: Optional callback function for progress updates
            
        Returns:
            True if training completed successfully, False otherwise
        """
        # Load training data
        data = self.load_training_data()
        if data is None:
            if callback:
                callback(None, 0, 0, None, "error", "No training data found")
            return False
        
        # Prepare data
        X, y_error, y_delta, y_output = self.prepare_data(data)
        
        try:
            # Report start
            if callback:
                callback("all", 0, 3, None, "started")
            
            # Train networks
            print("\nTraining error_scale network...")
            if callback:
                callback("error_scale", 0, epochs, None, "started")
            self.error_network.train(X, y_error, epochs=epochs, batch_size=batch_size, callback=callback)
            
            print("\nTraining delta_error_scale network...")
            if callback:
                callback("delta_error_scale", 0, epochs, None, "started")
            self.delta_error_network.train(X, y_delta, epochs=epochs, batch_size=batch_size, callback=callback)
            
            print("\nTraining output_scale network...")
            if callback:
                callback("output_scale", 0, epochs, None, "started")
            self.output_network.train(X, y_output, epochs=epochs, batch_size=batch_size, callback=callback)
            
            # Save models
            self.error_network.save()
            self.delta_error_network.save()
            self.output_network.save()
            
            # Plot training history
            self.error_network.plot_history()
            self.delta_error_network.plot_history()
            self.output_network.plot_history()
            
            # Report completion
            if callback:
                callback("all", 3, 3, None, "completed")
            
            return True
        except Exception as e:
            print(f"Error during training: {str(e)}")
            if callback:
                callback("all", 0, 0, None, "error", str(e))
            return False
    
    def load_networks(self):
        """Load all three networks from disk."""
        success = True
        
        if not self.error_network.load():
            success = False
        
        if not self.delta_error_network.load():
            success = False
        
        if not self.output_network.load():
            success = False
        
        return success


if __name__ == "__main__":
    trainer = NeuralNetworkTrainer()
    trainer.train_networks(epochs=50)
