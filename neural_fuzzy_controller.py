"""Compatibility adapter for the maintained, verified-model controller."""

from neural_tuned_fuzzy_controller import NeuralTunedFuzzyController


class NeuralFuzzyController(NeuralTunedFuzzyController):
    def __init__(self, models_to_use=None, models_dir=None):
        super().__init__(models_dir=models_dir, models_to_use=models_to_use)
