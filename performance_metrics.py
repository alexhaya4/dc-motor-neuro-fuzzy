"""Metrics calculated from observed samples, with explicit unavailable results."""

import math
import time
from collections import deque

from constants import SETTLING_TIME_TOLERANCE_PERCENT, STEADY_STATE_SAMPLES, STEADY_STATE_START_TIME_SEC


class PerformanceMetrics:
    def __init__(self, clock=time.monotonic, settling_dwell=1.0):
        if not math.isfinite(settling_dwell) or settling_dwell <= 0:
            raise ValueError('settling_dwell must be positive and finite')
        self.clock = clock
        self.settling_dwell = settling_dwell
        self.reset()

    def reset(self):
        self.start_time = self.clock()
        self.target = None
        self.within_since = None
        self.last_sample_time = None
        self.max_value = 0.0
        self.steady_state_samples = deque(maxlen=STEADY_STATE_SAMPLES)

    def update(self, target, actual):
        if not all(math.isfinite(x) and 0 <= x <= 100 for x in (target, actual)):
            raise ValueError('Metric inputs must be finite speed percentages')
        if self.target is not None and target != self.target:
            self.reset()
        self.target = target
        now = self.clock()
        self.last_sample_time = now
        self.max_value = max(self.max_value, actual)
        tolerance = max(target * SETTLING_TIME_TOLERANCE_PERCENT / 100, 0.1)
        if abs(actual - target) <= tolerance:
            if self.within_since is None:
                self.within_since = now
        else:
            self.within_since = None
        if now - self.start_time >= STEADY_STATE_START_TIME_SEC:
            self.steady_state_samples.append(abs(actual - target))

    def calculate(self, target):
        if self.target is None or target != self.target:
            return dict(overshoot=None, settling_time=None, ss_error=None, score=None)
        settling = None
        if self.within_since is not None and self.last_sample_time - self.within_since >= self.settling_dwell:
            settling = self.within_since - self.start_time
        overshoot = max(0.0, (self.max_value - target) * 100 / target) if target > 0 else None
        error = sum(self.steady_state_samples) / len(self.steady_state_samples) if self.steady_state_samples else None
        # A composite score is not reported without a defined, validated scoring protocol.
        return dict(overshoot=overshoot, settling_time=settling, ss_error=error, score=None)
