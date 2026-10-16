"""Train scaling models from a validated dataset supplied by the user."""

import argparse
from config import get_config
from nn_models import NeuralNetworkTrainer


def main():
    config = get_config()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', default=str(config.paths.data_dir / 'training_data.json'))
    parser.add_argument('--models', default=str(config.paths.models_dir))
    parser.add_argument('--epochs', type=int, default=config.controller.nn_epochs)
    parser.add_argument('--batch-size', type=int, default=config.controller.nn_batch_size)
    args = parser.parse_args()
    success = NeuralNetworkTrainer().train_networks(epochs=args.epochs, batch_size=args.batch_size,
                                                   filename=args.data, directory=args.models)
    return 0 if success else 1


if __name__ == '__main__':
    raise SystemExit(main())
