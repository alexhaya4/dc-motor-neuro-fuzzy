import pytest
from performance_metrics import PerformanceMetrics


def test_missing_observations_are_not_perfect_metrics():
    metrics = PerformanceMetrics()
    assert all(x is None for x in metrics.calculate(50).values())


def test_settling_requires_sustained_observed_tolerance_and_resets_on_excursion():
    now = [0.0]
    metrics = PerformanceMetrics(clock=lambda: now[0])
    now[0] = 1
    metrics.update(50, 50)
    assert metrics.calculate(50)['settling_time'] is None
    now[0] = 1.5
    metrics.update(50, 20)
    now[0] = 2
    metrics.update(50, 50)
    now[0] = 3.1
    metrics.update(50, 51)
    assert metrics.calculate(50)['settling_time'] == 2
    assert metrics.calculate(50)['ss_error'] is None
    now[0] = 6
    metrics.update(50, 49)
    assert metrics.calculate(50)['ss_error'] == 1
    metrics.update(75, 50)
    assert metrics.calculate(75)['settling_time'] is None
    assert metrics.calculate(75)['ss_error'] is None
    assert metrics.calculate(75)['score'] is None
