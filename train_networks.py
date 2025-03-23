import os
import sys
from nn_models import NeuralNetworkTrainer

def main():
    print("Starting neural network training for ANFIS controller...")
    
    # Check if training data exists
    if not os.path.exists("training_data.json"):
        print("Error: training_data.json not found. Please run data_collection.py first.")
        return
    
    # Create and train neural network models
    trainer = NeuralNetworkTrainer()
    
    print("Training neural networks...")
    print("This may take several minutes depending on your hardware.")
    print("The training progress will be displayed below.")
    
    trainer.train_networks(epochs=50, batch_size=32)
    
    print("\nTraining complete. The trained models have been saved to the 'models' directory.")
    print("You can now use the neural_fuzzy_controller.py with fully trained neural networks.")

if __name__ == "__main__":
    main()
