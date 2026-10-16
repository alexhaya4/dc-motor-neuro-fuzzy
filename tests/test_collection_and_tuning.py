"""Exercise collection/tuning logic with controlled input sequences, not physical performance claims."""
import json
import math
import pytest

from config import AppConfig, PathConfig
from auto_tuner import AutoTuner
from improved_data_collection import HeuristicDataCollector
from nn_models import NeuralNetworkTrainer


class InputSequence:
    def __init__(self, clock, values):
        self.clock = clock
        self.values = iter(values)
        self.writes = []
        self.arms = 0
    def arm(self):
        self.arms += 1
    def ChangeDutyCycle(self, value):
        self.writes.append(value)
    def read_speed(self, duration):
        self.clock[0] += duration
        return next(self.values)


@pytest.fixture
def clock(monkeypatch):
    import time
    value = [0.0]
    monkeypatch.setattr(time, 'monotonic', lambda: value[0])
    return value


def test_relay_uses_real_output_interface_and_measured_crossings(clock):
    hardware = InputSequence(clock, [40, 60] * 30)
    ku, tu = AutoTuner(hardware=hardware).relay_test(50, 10, 4)
    assert ku == pytest.approx(4 / math.pi)
    assert tu == pytest.approx(0.6)
    assert 40 in hardware.writes and 60 in hardware.writes
    assert hardware.writes[-1] == 0


def test_unexcited_plant_never_returns_successful_default_gains(clock):
    hardware = InputSequence(clock, [50] * 30)
    with pytest.raises(RuntimeError, match='No usable'):
        AutoTuner(hardware=hardware).tune_pid(test_duration=2)
    assert hardware.writes[-1] == 0


def test_tuning_exception_still_disables_output(clock):
    hardware = InputSequence(clock, [float('nan')])
    with pytest.raises(ValueError):
        AutoTuner(hardware=hardware).relay_test(50, 10, 2)
    assert hardware.writes[-1] == 0


def test_collector_and_trainer_share_dataset_schema(tmp_path, clock):
    config = AppConfig(load_from_env=False)
    config.paths = PathConfig(base_dir=tmp_path, models_dir=tmp_path/'models', logs_dir=tmp_path/'logs', data_dir=tmp_path/'data')
    hardware = InputSequence(clock, [40, 45, 48, 50, 50, 50])
    collector = HeuristicDataCollector(config, hardware)
    samples = collector.collect_at_target(50, 1, 2)
    assert len(samples) == len(collector.training_data) == 2
    assert hardware.writes[-1] == 0
    collector.save_training_data()
    filename = config.paths.data_dir/'training_data.json'
    payload = json.loads(filename.read_text())
    assert payload['metadata']['label_source'] == 'heuristic'
    trainer = NeuralNetworkTrainer()
    loaded = trainer.load_training_data(filename)
    X, *_ = trainer.prepare_data(loaded)
    assert X.shape == (2, 2)
    assert loaded == samples
