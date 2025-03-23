import tensorflow as tf
import numpy as np
import os
import json
import matplotlib.pyplot as plt

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
            return 0.5 + (predictions * 1.5)  # 0.5 to 2.0
        elif self.name == "delta_error_scale":
            return 0.5 + (predictions * 1.5)  # 0.5 to 2.0
        else:  # output_scale
            return 0.5 + (predictions * 1.0)  # 0.5 to 1.5
    
    def save(self, directory="models"):
        """Save the model to disk."""
        if not os.path.exists(directory):
            os.makedirs(directory)
        
        filepath = os.path.join(directory, f"{self.name}.h5")
        self.model.save(filepath)
        print(f"Model saved to {filepath}")
    
    def load(self, directory="models"):
        """Load the model from disk."""
        filepath = os.path.join(directory, f"{self.name}.h5")
        
        if os.path.exists(filepath):
            self.model = tf.keras.models.load_model(filepath)
            print(f"Model loaded from {filepath}")
            return True
        else:
            print(f"Model file {filepath} not found.")
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
        """Load training data from a file."""
        if not os.path.exists(filename):
            print(f"Training data file {filename} not found.")
            return None
        
        with open(filename, 'r') as f:
            data = json.load(f)
        
        print(f"Loaded {len(data)} training samples.")
        return data
    
    def prepare_data(self, data):
        """Prepare the data for training the neural networks."""
        # Extract features and targets
        X = np.array([[d['target_speed'], d['actual_speed']] for d in data])
        y_error = np.array([d['error_scale'] for d in data])
        y_delta = np.array([d['delta_error_scale'] for d in data])
        y_output = np.array([d['output_scale'] for d in data])
        
        # Normalize targets to [0, 1] range for sigmoid output
        y_error = (y_error - 0.5) / 1.5  # Map 0.5-2.0 to 0-1
        y_delta = (y_delta - 0.5) / 1.5  # Map 0.5-2.0 to 0-1
        y_output = (y_output - 0.5) / 1.0  # Map 0.5-1.5 to 0-1
        
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
