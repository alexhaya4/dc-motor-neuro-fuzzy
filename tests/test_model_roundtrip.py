"""Real TensorFlow training, serialization and controller-loading regressions."""
import json

import numpy as np
import pytest

from nn_models import ScalingFactorNetwork, NeuralNetworkTrainer, save_checksum, compute_file_checksum
from neural_tuned_fuzzy_controller import NeuralTunedFuzzyController


def test_real_training_and_keras_save_load_roundtrip(tmp_path):
    X = np.array([[x, x - 5] for x in range(10, 90, 10)], dtype=np.float32)
    y = np.linspace(0.2, 0.8, len(X), dtype=np.float32)
    network = ScalingFactorNetwork(name='error_scale')
    history = network.train(X, y, epochs=2, batch_size=4)
    assert len(history.history['loss']) == 2
    assert np.isfinite(history.history['loss']).all()
    before = network.predict(X)
    assert np.all((before >= 0.5) & (before <= 2))
    network.save(tmp_path)
    restored = ScalingFactorNetwork(name='error_scale')
    assert restored.load(tmp_path)
    np.testing.assert_allclose(restored.predict(X), before, rtol=1e-6)
    assert (tmp_path / 'error_scale.keras.sha256').exists()


def test_controller_uses_the_trainers_filenames_input_units_and_output_scaling(tmp_path):
    networks = {}
    for name in ('error_scale', 'delta_error_scale', 'output_scale'):
        network = ScalingFactorNetwork(name=name)
        network.save(tmp_path)
        networks[name] = network
    controller = NeuralTunedFuzzyController(tmp_path)
    assert controller.using_neural_networks
    controller._compute_scaling_factors(80, 35)
    for name, network in networks.items():
        expected = network.predict(np.array([[80, 35]], dtype=np.float32))[0, 0]
        assert getattr(controller, name) == pytest.approx(float(expected))
    assert 0 <= controller.compute_output(80, 35) <= 100
    assert controller.compute_output(0, 35) == 0


def test_missing_or_modified_checksum_does_not_load_model(tmp_path):
    original = ScalingFactorNetwork(name='error_scale')
    original.save(tmp_path)
    path = tmp_path / 'error_scale.keras.sha256'
    path.unlink()
    network = ScalingFactorNetwork(name='error_scale')
    assert not network.load(tmp_path)
    path.write_text('0' * 64)
    assert not network.load(tmp_path)


def test_legacy_hdf5_load_does_not_require_old_loss_deserialization(tmp_path):
    network = ScalingFactorNetwork(name='output_scale')
    filename = tmp_path / 'output_scale.h5'
    network.model.save(filename)
    save_checksum(str(filename), compute_file_checksum(filename))
    restored = ScalingFactorNetwork(name='output_scale')
    assert restored.load(tmp_path)
    X = np.array([[50, 40]], dtype=np.float32)
    np.testing.assert_allclose(restored.predict(X), network.predict(X), rtol=1e-6)


@pytest.mark.parametrize('features', [[[float('nan'), 5]], [[101, 1]], [[1]], []])
def test_invalid_inference_features_are_rejected(features):
    with pytest.raises(ValueError):
        ScalingFactorNetwork().predict(features)


@pytest.mark.parametrize('target', [float('nan'), -0.1, 1.1])
def test_training_rejects_unrepresentable_targets(target):
    with pytest.raises(ValueError):
        ScalingFactorNetwork().train([[10, 10], [20, 20]], [target, 0.5], epochs=1)


def test_training_data_envelope_and_nonfinite_json(tmp_path):
    trainer = NeuralNetworkTrainer()
    sample = dict(target_speed=50, actual_speed=45, error_scale=1, delta_error_scale=1, output_scale=1)
    filename = tmp_path / 'data.json'
    filename.write_text(json.dumps({'metadata': {'label_source': 'heuristic'}, 'samples': [sample]}))
    loaded = trainer.load_training_data(filename)
    assert loaded == [sample]
    X, *ys = trainer.prepare_data(loaded)
    np.testing.assert_equal(X, [[50, 45]])
    assert all(np.isfinite(y).all() for y in ys)
    filename.write_text(json.dumps([{**sample, 'actual_speed': float('nan')}]))
    assert trainer.load_training_data(filename) is None


def test_scaling_targets_outside_network_output_range_are_rejected(tmp_path):
    sample = dict(target_speed=50, actual_speed=45, error_scale=4, delta_error_scale=1, output_scale=1)
    filename = tmp_path / 'data.json'
    filename.write_text(json.dumps([sample]))
    assert NeuralNetworkTrainer().load_training_data(filename) is None
