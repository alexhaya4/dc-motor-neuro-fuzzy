import math

import pytest

from base_controller import BaseController
from config import GPIOConfig, MotorConfig, PathConfig, ConfigurationError
from conventional_controllers import PIController, PIDController
from fuzzy_controller import FuzzyController
from auto_tuner import AutoTuner
from improved_data_collection import HeuristicDataCollector


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf')])
def test_nonfinite_controller_outputs_fail_to_zero(value):
    class InvalidController(BaseController):
        def _compute_control_output(self, target, current):
            return value
    assert InvalidController().compute_output(50, 20) == 0


@pytest.mark.parametrize('cls', [PIController, PIDController, FuzzyController])
def test_zero_setpoint_cannot_power_motor(cls):
    assert cls().compute_output(0, 0) == 0
    assert cls().compute_output(0, 40) == 0


@pytest.mark.parametrize('cls,kwargs', [(PIController, {'kp': float('nan')}),
    (PIDController, {'kd': float('inf')}), (PIController, {'integral_limit': -1})])
def test_invalid_controller_parameters_are_rejected(cls, kwargs):
    with pytest.raises(ValueError):
        cls(**kwargs)


def test_gpio_aliasing_is_rejected():
    with pytest.raises(ConfigurationError, match='distinct'):
        GPIOConfig(motor_in1=18)


@pytest.mark.parametrize('kwargs', [{'max_rpm': 0}, {'pulses_per_revolution': 0}, {'pwm_frequency': -1},
    {'pulses_per_revolution': 1.5}, {'min_pulse_width_ms': float('nan')}])
def test_invalid_motor_configuration_is_rejected(kwargs):
    with pytest.raises(ConfigurationError):
        MotorConfig(**kwargs)


def test_subdirectory_may_not_escape_to_sibling(tmp_path):
    base = tmp_path / 'repo'
    with pytest.raises(ConfigurationError, match='outside'):
        PathConfig(base_dir=base, models_dir=tmp_path / 'other', logs_dir=base / 'logs', data_dir=base / 'data')
    assert not (tmp_path / 'other').exists()


def test_relay_gain_formula_rejects_unusable_period_and_does_not_clamp_results():
    tuner = AutoTuner()
    assert tuner.calculate_ziegler_nichols(10, 2) == pytest.approx((6, 6, 1.5))
    assert tuner.validate_parameters(6, 6, 1.5) == (6, 6, 1.5)
    with pytest.raises(ValueError):
        tuner.calculate_ziegler_nichols(10, 0)


def test_tuner_and_collector_never_substitute_random_hardware_readings(monkeypatch):
    import motor_hardware
    monkeypatch.setattr(motor_hardware, 'is_raspberry_pi', lambda: False)
    with pytest.raises(RuntimeError):
        AutoTuner().measure_speed()
    with pytest.raises(RuntimeError):
        HeuristicDataCollector().collect_at_target(50, 1, 1)


def test_complete_fuzzy_rule_grid_has_an_inference_result():
    controller = FuzzyController()
    for error in (-100, -30, 0, 30, 100):
        for delta in (-100, -30, 0, 30, 100):
            controller.controller.input['error'] = error
            controller.controller.input['delta_error'] = delta
            controller.controller.compute()
            value = controller.controller.output['pwm_output']
            assert math.isfinite(value) and 0 <= value <= 100


def test_pi_pid_use_elapsed_monotonic_time(monkeypatch):
    import conventional_controllers
    clock = [0.0]
    monkeypatch.setattr(conventional_controllers.time, 'monotonic', lambda: clock[0])
    pi = PIController(kp=0.5, ki=0.1)
    clock[0] = 0.2
    assert pi.compute_output(50, 20) == pytest.approx(15.6)
    pid = PIDController(kp=0, ki=0, kd=1)
    clock[0] = 0.3
    assert pid.compute_output(50, 30) == pytest.approx(20)
    clock[0] = 0.4
    assert pid.compute_output(50, 40) == pytest.approx(8)


def test_invalid_numeric_environment_has_a_configuration_error(monkeypatch):
    monkeypatch.setenv('MOTOR_PULSES_PER_REV', 'not-a-number')
    with pytest.raises(ConfigurationError, match='MOTOR_PULSES_PER_REV'):
        MotorConfig.from_env()
