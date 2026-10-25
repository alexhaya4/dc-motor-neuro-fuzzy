import tensorflow as tf
import numpy as np
import os
import json
import hashlib
import tempfile
import math
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
            "error_scale": {"type": "number", "minimum": NN_ERROR_SCALE_MIN, "maximum": NN_ERROR_SCALE_MAX},
            "delta_error_scale": {"type": "number", "minimum": NN_DELTA_ERROR_SCALE_MIN, "maximum": NN_DELTA_ERROR_SCALE_MAX},
            "output_scale": {"type": "number", "minimum": NN_OUTPUT_SCALE_MIN, "maximum": NN_OUTPUT_SCALE_MAX}
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
    parent = Path(checksum_file).parent
    with tempfile.NamedTemporaryFile(mode='w', dir=parent, delete=False) as f:
        f.write(checksum)
        temporary = f.name
    os.replace(temporary, checksum_file)


def load_checksum(filepath: str) -> str:
    """Load checksum from .checksum file"""
    checksum_file = f"{filepath}.{MODEL_CHECKSUM_ALGORITHM}"
    if os.path.exists(checksum_file):
        with open(checksum_file, 'r') as f:
            return f.read().strip()
    return None

class ScalingFactorNetwork:
    """Neural network model for adaptive scaling factors."""
    
    def __init__(self, input_size=2, hidden_layers=None, output_size=1, name="scaling_network"):
        """Initialize the neural network model.
        
        Args:
            input_size: Number of input features (default: 2 for target_speed, actual_speed)
            hidden_layers: List of hidden layer sizes (default: [16, 8])
            output_size: Number of outputs (default: 1 for a single scaling factor)
            name: Name of the model for saving/loading
        """
        if not name or Path(name).name != name or '/' in name or '\\' in name:
            raise ValueError('Model name must be a filename without path components')
        hidden_layers = [16, 8] if hidden_layers is None else list(hidden_layers)
        if input_size != 2 or output_size != 1 or not hidden_layers or any(not isinstance(n, int) or n <= 0 for n in hidden_layers):
            raise ValueError('Scaling networks require two inputs, one output and positive hidden layers')
        self.name = name
        self.model = self._build_model(input_size, hidden_layers, output_size)
        self.history = None
        
    def _build_model(self, input_size, hidden_layers, output_size):
        """Build the neural network model."""
        model = tf.keras.Sequential(name=self.name)
        model.add(tf.keras.Input(shape=(input_size,)))
        model.add(tf.keras.layers.Rescaling(1.0 / 100.0))
        
        # Input layer
        model.add(tf.keras.layers.Dense(hidden_layers[0], activation='relu'))
        
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
        X = self._validate_features(X)
        y = np.asarray(y, dtype=np.float32).reshape(-1, 1)
        if len(y) != len(X) or not np.isfinite(y).all() or np.any((y < 0) | (y > 1)):
            raise ValueError('Training targets must be finite normalized scaling factors in [0, 1]')
        if not 0 <= validation_split < 1 or not isinstance(epochs, int) or epochs <= 0 or not isinstance(batch_size, int) or batch_size <= 0:
            raise ValueError('Invalid training settings')
        split = int(len(X) * (1 - validation_split))
        if split < 1 or (validation_split and split >= len(X)):
            raise ValueError('Insufficient samples for the requested validation split')

        def dataset(features, targets):
            data = tf.data.Dataset.from_tensor_slices((features, targets)).batch(batch_size)
            options = tf.data.Options()
            options.threading.private_threadpool_size = 1
            options.threading.max_intra_op_parallelism = 1
            return data.with_options(options)

        network_name = self.name
        class ProgressCallback(tf.keras.callbacks.Callback):
            def on_epoch_end(self, epoch, logs=None):
                if callback:
                    callback(network_name, epoch, epochs, logs, 'running')

        self.model.compile(optimizer='adam', loss='mse', metrics=['mae'])
        training = dataset(X[:split], y[:split])
        validation = dataset(X[split:], y[split:]) if validation_split else None
        self.history = self.model.fit(training, validation_data=validation, epochs=epochs,
                                      verbose=0, shuffle=False, callbacks=[ProgressCallback()])
        if callback:
            callback(self.name, epochs - 1, epochs, None, 'completed')
        return self.history

    @staticmethod
    def _validate_features(X):
        X = np.asarray(X, dtype=np.float32)
        if X.ndim == 1:
            X = X.reshape(1, -1)
        if X.ndim != 2 or X.shape[1] != 2 or not len(X) or not np.isfinite(X).all() or np.any((X < 0) | (X > 100)):
            raise ValueError('Expected finite [target_speed, actual_speed] percentages with shape (N, 2)')
        return X

    def predict(self, X):
        """Make predictions with the model.
        
        Args:
            X: Input features
            
        Returns:
            Predicted values
        """
        X = self._validate_features(X)
        predictions = self.model(tf.convert_to_tensor(X), training=False).numpy()
        if predictions.shape != (len(X), 1) or not np.isfinite(predictions).all() or np.any((predictions < 0) | (predictions > 1)):
            raise ValueError('Model produced invalid normalized scaling factors')

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
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        filepath = directory / f"{self.name}.keras"
        with tempfile.NamedTemporaryFile(suffix='.keras', dir=directory, delete=False) as f:
            temporary = Path(f.name)
        try:
            self.model.save(temporary)
            checksum = compute_file_checksum(temporary)
            os.replace(temporary, filepath)
            save_checksum(str(filepath), checksum)
        finally:
            temporary.unlink(missing_ok=True)

    def load(self, directory="models", verify_integrity=True):
        directory = Path(directory)
        filepath = directory / f"{self.name}.keras"
        if not filepath.exists():
            filepath = directory / f"{self.name}.h5"
        if not filepath.is_file():
            return False
        try:
            if verify_integrity:
                checksum = load_checksum(str(filepath))
                if not checksum or not verify_file_checksum(str(filepath), checksum):
                    return False
            model = tf.keras.models.load_model(filepath, compile=False, safe_mode=True)
            if model.input_shape != (None, 2) or model.output_shape != (None, 1):
                return False
            # Check the actual inference path before adopting a model.
            previous = self.model
            self.model = model
            try:
                self.predict(np.array([[0.0, 0.0], [100.0, 100.0]], dtype=np.float32))
            except Exception:
                self.model = previous
                return False
            return True
        except (OSError, ValueError, TypeError, UnicodeError):
            return False

    def plot_history(self):
        """Plot the training history to a file without showing it interactively."""
        if self.history is None:
            print("No training history available.")
            return
        
        # Use a non-interactive backend for plotting
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        
        figure = Figure(figsize=(12, 4))
        FigureCanvasAgg(figure)
        for axis, metric in zip(figure.subplots(1, 2), ('loss', 'mae')):
            axis.plot(self.history.history[metric], label='Training')
            if 'val_' + metric in self.history.history:
                axis.plot(self.history.history['val_' + metric], label='Validation')
            axis.set(title=f'{self.name} - {metric}', xlabel='Epochs', ylabel=metric)
            axis.legend()
        figure.tight_layout()
        figure.savefig(f'{self.name}_history.png')


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
        try:
            def invalid_constant(value):
                raise ValueError(f'Non-finite JSON number: {value}')

            # Bound the bytes actually read, not a size observed before opening.
            # A file may change between a separate stat and the JSON parser.
            with open(filename, 'rb') as stream:
                contents = stream.read(MAX_JSON_FILE_SIZE_BYTES + 1)
            if len(contents) > MAX_JSON_FILE_SIZE_BYTES:
                print(f"Training data file {filename} is too large "
                      f"({len(contents)} bytes read; limit {MAX_JSON_FILE_SIZE_BYTES} bytes).")
                return None
            data = json.loads(contents.decode('utf-8'), parse_constant=invalid_constant)
            if isinstance(data, dict):
                data = data.get('samples')

            # Validate JSON structure
            validate(instance=data, schema=TRAINING_DATA_SCHEMA)

            print(f"Loaded and validated {len(data)} training samples.")
            return data

        except FileNotFoundError:
            print(f"Training data file {filename} not found.")
            return None
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as e:
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
        validate(instance=data, schema=TRAINING_DATA_SCHEMA)
        if not all(math.isfinite(value) for row in data for value in row.values()):
            raise ValueError('Training data contains non-finite numbers')
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
    
    def train_networks(self, epochs=100, batch_size=32, callback=None, filename=None, directory=None):
        """Train all three networks.
        
        Args:
            epochs: Number of training epochs
            batch_size: Batch size for training
            callback: Optional callback function for progress updates
            
        Returns:
            True if training completed successfully, False otherwise
        """
        # Load training data
        from config import get_config
        config = get_config()
        filename = filename if filename is not None else config.paths.data_dir / 'training_data.json'
        directory = directory if directory is not None else config.paths.models_dir
        data = self.load_training_data(filename)
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
            self.error_network.save(directory)
            self.delta_error_network.save(directory)
            self.output_network.save(directory)
            
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
